# Correctif : dépassement de la limite TPM de Groq sur SWE-bench

Date : 2026-11-03. Branche : `dev`. Rien n'est commité.

Fichiers modifiés :

| Fichier | Lignes ajoutées | Lignes retirées |
|---|---|---|
| `src/orchestration/exception.py` | 6 | 0 |
| `src/orchestration/orchestrator.py` | 39 | 4 |
| `src/orchestration/py_extractor.py` | 10 | 0 |
| `src/tools/execution.py` | 12 | 4 |

Aucun autre fichier n'est modifié. La logique du 429 (attente, puis rotation de clé), `key_manager.py` et `parse_header.py` sont inchangés.

---

## 1. Le problème

Tâche `django__django-11066`, modèle `openai/gpt-oss-120b` sur Groq.

**Premier run.** L'agent s'arrête à l'étape 6 avec l'erreur :

```
All provider API keys have been exhausted.
```

**Deuxième run.** Avec un premier patch, qui a ensuite été annulé, l'erreur exacte de Groq apparaît :

```
Error code: 413 - Request too large for model `openai/gpt-oss-120b` ...
on tokens per minute (TPM): Limit 8000, Requested 9363,
please reduce your message size and try again.
```

### Pourquoi

- **La limite est de 8000 TPM par clé** pour `gpt-oss-120b`. Le script `tests/check_quotas.py` l'a vérifié sur les 6 clés : `7927 / 8000` TPM et `999 / 1000` requêtes/jour. Aucune clé n'était épuisée.
- **Le contexte grossit à chaque étape.** Le prompt système et la tâche font environ 4000 tokens au départ, et chaque observation en ajoute jusqu'à environ 1000. Vers l'étape 6, une requête seule dépasse les 8000 tokens.
- **Groq répond alors 413 « Request too large »**, qui veut dire que la requête est plus grosse que la limite par minute elle-même. Attendre ou changer de clé ne sert à rien : seule la réduction du contexte règle le problème.
- **L'ancien code traitait le 413 comme un 429** : il attendait, passait à la clé suivante, puis recommençait. Après 6 échecs, il affichait « All provider API keys have been exhausted », ce qui était trompeur.

### Deux sources de gaspillage de tokens

1. **gpt-oss ignore les stop sequences** (`` ```Thought ``, `Observation:`) et invente plusieurs étapes à la suite dans une seule réponse. Seul le premier bloc de code est exécuté, mais toute la réponse était ajoutée au contexte.
2. **`run_tests()` renvoyait jusqu'à 15 000 caractères** (les derniers), puis la sandbox n'en affichait que les 4000 premiers. Le modèle voyait le milieu de la sortie : migrations Django et trace bash `+ source /opt/miniconda3...`. Il ne voyait jamais le résumé des tests (`Ran N tests ... OK/FAILED`), et ce bruit coûtait environ 1000 tokens par appel.

---

## 2. Modifications

### 2.1 `src/orchestration/exception.py`

Nouvelle exception, ajoutée entre `KeyQuotaError` et `ServerError` (ligne 13) :

```python
class RequestTooLargeError(ProviderRequestError):
    """Raised when a single request exceeds the provider tokens limit."""

    pass
```

Elle hérite de `ProviderRequestError`. Le `except ProviderRequestError` de `complete_task` l'attrape donc déjà : si elle remonte jusque-là, la boucle s'arrête proprement et `force_swe_patch` sauve le patch.

### 2.2 `src/orchestration/orchestrator.py`

**a) Imports (lignes 10-11 et 18)**

```python
from .exception import (KeyQuotaError, ServerError, FatalError,
                        ProviderRequestError, RequestTooLargeError)
...
from .py_extractor import extract_code, keep_first_block
```

**b) Constantes (lignes 34-36), sous `SWE_LIMITS`**

```python
# Characters kept from an old observation when the context is trimmed
KEPT_OBSERVATION_CHARS = 300
TRIM_NOTICE = "\n[... output truncated to fit the provider token limit ...]"
```

**c) `call_api()` : le 413 est séparé du 429 (lignes 106-111)**

Avant, les deux codes étaient traités ensemble :

```python
if status in (413, 429):
    ... time.sleep(wait_time)
    raise KeyQuotaError(...)
```

Après, le 413 a son propre cas, sans attente et sans rotation :

```python
if status == 413:
    # The prompt alone is above the tokens/minute limit:
    # waiting cannot make it pass, the context must shrink
    raise RequestTooLargeError(
        f"Request too large ({status}): {e}") from e
elif status == 429:
    # (code d'origine inchangé : attente selon les headers, puis KeyQuotaError)
```

**d) `query_llm()` : nouveau cas `except` (lignes 173-177)**

```python
except RequestTooLargeError:
    self.step_retries += 1
    # Shrink the history, give up once nothing is left to trim
    if not self.trim_context():
        raise
```

À chaque 413, une observation est raccourcie, puis la requête repart immédiatement avec la même clé. La tentative est comptée dans `retries`. Quand il ne reste plus rien à raccourcir, l'erreur remonte.

**e) Nouvelle méthode `trim_context()` (lignes 189-202)**

```python
def trim_context(self) -> bool:
    """Shorten the oldest long observation, False if none is left."""
    trimmed_size = KEPT_OBSERVATION_CHARS + len(TRIM_NOTICE)
    # Keep the system prompt, the task and the latest observation
    for i in range(2, len(self.context) - 1):
        content = self.context[i].get("content")
        if (self.context[i]["role"] == "user"
                and isinstance(content, str)
                and len(content) > trimmed_size):
            self.context[i] = {
                "role": "user",
                "content": content[:KEPT_OBSERVATION_CHARS] + TRIM_NOTICE,
            }
            return True
    return False
```

Règles de la méthode :
- **Messages jamais touchés :** l'index 0 (prompt système), l'index 1 (tâche) et le dernier message, qui est l'observation la plus récente dont le modèle a besoin.
- **Messages concernés :** uniquement ceux du rôle `user` (les observations). Les réponses de l'assistant ne sont jamais raccourcies.
- **Un seul message par appel :** le plus ancien dont la taille dépasse `300 + len(TRIM_NOTICE)` caractères. Il est réduit à ses 300 premiers caractères suivis de `TRIM_NOTICE`.
- **Pas de double coupe :** un message déjà raccourci fait exactement `trimmed_size` caractères, donc il n'est plus sélectionné.
- **Valeur de retour :** `True` si un message a été raccourci, `False` s'il n'y avait plus rien à raccourcir.
- **Pas besoin de connaître la limite :** comme on raccourcit une observation par 413, ça s'adapte à n'importe quel provider.

**f) `complete_task()` : seule la partie exécutée de la réponse va dans le contexte (lignes 243-245)**

Avant :

```python
self.context.append({"role": "assistant", "content": answer})
```

Après :

```python
# Raw answer stays in StepMetrics, the context only keeps
# the part that is actually executed
self.context.append({"role": "assistant",
                     "content": keep_first_block(answer)})
```

`extract_code(answer)` et `StepMetrics.llm_output` utilisent toujours la réponse brute. Le code exécuté et les métriques ne changent donc pas.

### 2.3 `src/orchestration/py_extractor.py`

Nouvelle fonction `keep_first_block()` (ligne 95), placée juste avant `extract_code()` :

```python
def keep_first_block(answer: str) -> str:
    """Cut an LLM answer right after its first fenced code block."""
    # Only the first block is executed: any hallucinated follow-up steps
    # would bloat the context and mislead the model on the next turn
    match = re.search(r"```[^\n]*\n.*?```", answer, re.DOTALL)
    if not match:
        return answer
    return answer[:match.end()]
```

- **Ce que repère la regex :** un bloc qui s'ouvre avec ```` ``` ```` suivi éventuellement d'un langage (`python`, `py` ou rien), puis le premier ```` ``` ```` qui le ferme.
- **Ce qui est gardé :** tout ce qui précède le bloc (`Thought: ...`) et le bloc lui-même. Tout ce qui suit est coupé.
- **Sans bloc ```` ``` ````** (formats XML `<code>`, ReAct `Action:`, etc.), la réponse est gardée telle quelle.

### 2.4 `src/tools/execution.py` (fonction `run_swebench_tests`, l'outil `run_tests`)

**a) Import de `re` (ligne 5).**

**b) Taille maximale (lignes 94-97) :** on passe de `max_size = 15000` à `max_size = 2000`.

```python
# The sandbox prints only the first 4000 characters of stdout:
# stay well below it so the test summary at the end stays visible
# without filling the provider tokens/minute budget
max_size = 2000
```

La troncature existante, qui garde la **fin** de la sortie, est inchangée. Avec 2000 caractères, toute la sortie passe sous la limite d'affichage de la sandbox (4000), et le résumé des tests, situé à la fin, reste visible.

**c) Filtrage de la trace bash (lignes 134-138)**

```python
# Nested bash xtrace lines ("++ ...", conda activation) are pure noise
stderr = "\n".join(line for line in process.stderr.splitlines()
                   if not re.match(r"\+{2,} ", line))
result = (f"Exit code: {process.returncode}\n"
          f"STDOUT:\n{process.stdout}\n"
          f"STDERR:\n{stderr}")
```

- **Lignes supprimées :** celles qui commencent par au moins deux `+` suivis d'un espace (`++ `, `+++ `, ...). Ce sont les lignes internes de l'activation conda.
- **Lignes conservées :** celles qui commencent par un seul `+ ` (par exemple `+ cd /testbed`), parce qu'unittest utilise aussi `+ ` dans ses diffs d'assertion (`- [1]` / `+ [2]`).

**d) Docstring mise à jour :** elle indique maintenant « only the last 2000 characters, where the test summary is ». Cette docstring apparaît dans le manuel des outils envoyé au modèle.

---

## 3. Ce qui a été essayé puis annulé

Un premier patch faisait plus de choses :
- `max_retries=0` sur le client OpenAI, pour couper les retries cachés du SDK ;
- un nouveau `ThrottleError` sur le 429, avec attente sur la même clé ;
- une deadline liée au timeout de la tâche.

Il a été entièrement retiré avec `git checkout` sur `exception.py` et `orchestrator.py`. Seule la gestion du 413 (`trim_context`) a été remise. Conséquences à garder en tête :
- **Retries cachés du SDK :** le SDK OpenAI refait encore jusqu'à 2 tentatives sur un 429, en attendant `retry-after` (jusqu'à 120 s). Ces tentatives n'apparaissent pas dans `retries`, mais gonflent `request_time_ms`. C'est ce qui explique les étapes à environ 48 s avec `retries: 0`.
- **429 inchangé :** un 429 déclenche toujours une attente, puis une rotation de clé comptée comme un échec.

---

## 4. Vérifications effectuées

- `flake8 src/orchestration src/tools` : aucune erreur.
- `mypy src/orchestration src/tools` avec les options du Makefile : aucune erreur.
- **Test 413 avec réponses d'API simulées, sans appel réseau :**
  - 413 puis succès : l'ancienne observation est raccourcie, la dernière est intacte, la clé ne change pas, il n'y a pas de `sleep`, et `step_retries = 1`.
  - 413 alors qu'il ne reste rien à raccourcir : `RequestTooLargeError` remonte.
- **`keep_first_block()` sur les 7 réponses du dernier run :** le code exécuté est identique dans tous les cas. L'étape 4 passe de 658 à 171 caractères, et l'étape 5 de 1890 à 139.
- **Filtre de `run_tests()` sur un exemple :** les lignes `++`/`+++` sont supprimées, et `+ cd`, `+ [2]` et `Ran 4 tests ... OK` sont conservées.
- `make lint` échoue toujours, mais à cause d'erreurs qui existaient déjà dans des fichiers non modifiés : `src/__main__.py`, `src/sandbox/protocol.py`, `src/sandbox/test/sandbox_full_test.py` et `tests/test_py_extractor.py`.

**Non vérifié :** aucun run réel SWE-bench avec Groq n'a été relancé après ces modifications.

---

## 5. Limites connues

- **Groq compte plus de tokens que le prompt réel.** Au deuxième run, il annonçait `Requested 9363` alors que les anciennes observations étaient déjà raccourcies. Il faut donc que le prompt reste nettement sous 8000 tokens.
- **Le contexte peut encore saturer.** Les réponses de l'assistant, le prompt système et la tâche ne sont jamais raccourcis. Sur une très longue trajectoire avec 8000 TPM, l'agent peut donc encore s'arrêter sur `Request too large (413)`. Dans ce cas, `force_swe_patch` sauve quand même le patch.
- **Solution plus durable :** un modèle ou une offre Groq (Dev Tier) avec une limite TPM plus haute.
