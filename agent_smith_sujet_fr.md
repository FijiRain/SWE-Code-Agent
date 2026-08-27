# Agent Smith
### Raisonnement autonome, génération et exécution de code

**Résumé :** Dans ce projet, vous allez construire un **framework agentique** capable de résoudre de manière autonome des défis de programmation.
Votre agent devra raisonner, écrire du code, l'exécuter dans un environnement sandboxé, et itérer jusqu'à trouver une solution.
Ce projet introduit les **Code Agents**, le **Model Context Protocol (MCP)**, et l'**exécution de code contrôlée**.
Réalisé en collaboration avec @ldevelle.

*Version : 1.1*

---

## Table des matières

- I. Avant-propos
- II. Instructions IA
- III. Vue d'ensemble
  - III.1 Qu'est-ce qu'un Code Agent ?
- IV. Instructions communes
  - IV.1 Règles générales
  - IV.2 Contraintes techniques
- V. Partie obligatoire
  - V.1 Framework agentique
    - V.1.1 Modèles de sortie communs
    - V.1.2 Approche de développement
  - V.2 Le Sandbox
  - V.3 Agent MBPP
  - V.4 Agent SWE-bench
  - V.5 Outils obligatoires
    - V.5.1 Outils système de fichiers
    - V.5.2 Outils de recherche de code
    - V.5.3 Outils d'exécution
  - V.6 Fournisseurs d'API LLM
    - V.6.1 Exemples de fournisseurs gratuits
  - V.7 Rapport de benchmark de modèles
- VI. Évaluation
  - VI.1 Exigences strictes et limites
    - VI.1.1 Limites MBPP
    - VI.1.2 Limites SWE-bench
  - VI.2 Critères de réussite
  - VI.3 Critères de notation
  - VI.4 Ce qui sera testé lors de la review
    - VI.4.1 Sécurité IA en évaluation
  - VI.5 Structure des logs d'évaluation
- VII. Exigences du README
- VIII. Rendu

---

## Chapitre I — Avant-propos

L'ingénierie logicielle ne consiste plus seulement à écrire du code correct, elle consiste à **comprendre des systèmes, naviguer dans de grandes bases de code, déboguer des échecs et itérer efficacement**. Les LLM modernes génèrent bien du code, mais corriger de vrais bugs nécessite aussi de l'exploration, des tests d'hypothèses, de l'exécution et de l'observation.

C'est là qu'intervient **Agent Smith**. Un Code Agent n'est pas simplement un modèle qui écrit du code : **il raisonne sur une tâche, interagit avec des outils, exécute du code en toute sécurité, observe les résultats et adapte sa stratégie**. Dans ce projet, vous allez concevoir et implémenter un tel système, en allant au-delà des prompts statiques et de l'appel d'outils basé sur du JSON, pour construire une **boucle agentique complète** pilotée par du code Python exécutable.

---

## Chapitre II — Instructions IA

### ● Contexte

L'IA est aujourd'hui un puissant partenaire de code — aux côtés de vos pairs — pour s'attaquer à des projets vastes et exigeants. Vous devrez la guider tant sur les aspects techniques que non techniques de votre travail.

Les outils IA peuvent améliorer votre efficacité et la qualité de votre travail, mais vous devez être capable d'approfondir n'importe quelle partie du projet sans en dépendre.

Votre partenaire IA vous soutient, mais vous restez pleinement responsable de vos décisions techniques informées, et de leur explication et défense.

### ● Message principal

- ☛ Visez un usage mature et responsable de l'IA.
- ☛ Ne laissez jamais l'IA prendre des décisions à votre place — surtout lorsqu'elle n'a pas conscience de vos objectifs, contraintes ou dynamiques d'équipe.
- ☛ Préservez la créativité, l'innovation et la supervision humaine grâce à une collaboration active avec vos pairs. L'IA est entraînée sur des données existantes et génère rarement de véritables idées nouvelles.
- ☛ Restez informé des tendances émergentes et prêt à vous adapter à de nouveaux concepts et technologies.

### ● Règles pour l'apprenant :

- Conservez le leadership intellectuel sur vos projets et prenez vos propres décisions informées.
- Priorisez l'intelligence collective de votre équipe et de vos pairs.
- Restez activement informé de l'évolution des technologies IA.

### ● Résultats de la phase :

- Compétences en ingénierie IA.
- Efficacité accrue.
- Meilleure fiabilité et qualité.
- Un esprit pionnier.

### ● Commentaires et exemples :

- Vos pairs peuvent identifier les compromis, questionner les hypothèses et vous aider à progresser. La première réponse d'une IA n'est peut-être pas la meilleure — elle peut manquer d'efficacité, de sécurité, ou de réelle valeur ajoutée. Plus que jamais, appuyez-vous sur vos pairs.
- L'IA peut vous rendre plus rapide, mais vos pairs vous rendent meilleur. La collaboration, la discussion et le challenge mutuel sont clés pour réussir.
- Soyez transparent sur la façon dont l'IA a été utilisée dans vos projets, et identifiez clairement ce qui a été généré par des outils IA.

**✓ Bonne pratique :**
> J'ai demandé à l'IA de m'aider à générer des tests unitaires pour mon API. Je les ai revus avec mon coéquipier, et nous les avons ajustés pour les cas limites. Cela nous a fait gagner du temps, et nous avons tous les deux appris quelque chose de nouveau.

**✗ Mauvaise pratique :**
> J'ai fait générer l'intégralité de l'architecture de mon projet par l'IA. Ça « fonctionne », mais quand on me demande d'expliquer les choix de conception lors de la peer review ou devant un client, je ne peux pas. Je perds en crédibilité et j'échoue.

---

## Chapitre III — Vue d'ensemble

Ce projet explore un nouveau paradigme de l'ingénierie logicielle pilotée par IA : la **génération de code agentique**.

Contrairement aux approches classiques où un LLM produit une réponse finale, votre système permettra au modèle de :

- Écrire du code Python exécutable
- Appeler des outils directement depuis le code
- Observer les résultats d'exécution
- Itérer jusqu'à ce que la tâche soit résolue

Votre agent fonctionnera selon une boucle structurée : **Thought → Code → Observation** (Réflexion → Code → Observation).

*(Schéma « AGENT LOOP » : THOUGHT (le LLM raisonne) → CODE (le LLM écrit) → OBSERVATION (le code s'exécute dans le sandbox) → (répéter jusqu'à trouver une solution) → FINAL ANSWER (soumettre la solution))*

Vous appliquerez ce framework à deux benchmarks différents :

- **MBPP** : problèmes algorithmiques Python
- **SWE-bench** : correction de bugs réels dans des dépôts de production

Le défi central de ce projet n'est pas seulement de rendre l'agent intelligent, mais aussi de le rendre **sûr, contrôlé, reproductible et mesurable**.
En particulier, vous devrez **évaluer et comparer plusieurs modèles de langage** afin d'analyser leurs performances et d'identifier les plus efficaces en fonction du taux de réussite et de l'efficacité d'itération.

### III.1 Qu'est-ce qu'un Code Agent ?

Un **Code Agent** est un système IA capable de :

- Raisonner sur une tâche de programmation
- Générer du code exécutable
- Exécuter ce code dans un environnement contrôlé
- Utiliser des outils pour interagir avec des fichiers, des tests et des dépôts
- Observer les résultats et affiner son approche

Dans ce projet, vous implémenterez une approche d'**appel d'outils basé sur le code**, où le LLM génère du code Python tel que :

```python
result = search_code("validate_email")
print(result)
content = read_file("models.py", 1, 50)
print(content)
```

Cette approche est plus expressive que l'appel d'outils en JSON, car elle permet :

- Des variables persistantes entre les étapes
- De la logique conditionnelle et des boucles
- Un raisonnement complexe en plusieurs étapes

*(Schéma d'exemple de conversation : le système envoie le framework, le manuel du sandbox et la consigne « Corrige le bug de `is_valid_email()` quand un email contient un signe '+' ». Le LLM raisonne, écrit du code appelant `search_code`, `read_file`, observe les résultats renvoyés par le sandbox (localisation de la fonction, contenu du fichier), et conclut : « J'ai trouvé le problème ! Le pattern regex est incomplet... »)*

*(Schéma d'architecture « Agent Code » :*
*1. **Agent/Orchestrator** est la boucle centrale. Il appelle le LLM, extrait le code, l'envoie au sandbox, lit les observations, et recommence.*
*2. **Extraction de code** est une étape de transformation entre la réponse du LLM et le sandbox.*
*3. **Sandbox** est la frontière d'exécution. Il applique des restrictions de sécurité au code généré par le LLM. Le sandbox contient un client MCP qui se connecte à un serveur MCP externe.*
*4. **`final_answer()`** est une construction intégrée au sandbox — ce n'est PAS un outil MCP.*
*5. **Le(s) serveur(s) MCP** s'exécutent en processus séparés (via stdio ou HTTP). Seuls vos propres serveurs MCP sont autorisés.)*

---

## Chapitre IV — Instructions communes

### IV.1 Règles générales

- Vous devez utiliser **Python 3.10**.
- Vous devez utiliser **uv** comme gestionnaire de paquets.
- Votre projet doit suivre les principes d'une architecture logicielle propre.
- Toutes les erreurs doivent être gérées proprement — un crash pendant l'évaluation entraînera un échec.
- Votre code doit être lisible, structuré et documenté.
- Toute exécution doit se faire dans un **environnement sandboxé**.

### IV.2 Contraintes techniques

- Vous devez supporter plusieurs fournisseurs et modèles LLM.
- Vous devez implémenter un suivi d'utilisation (tokens, retries, latence, requêtes).
- Vous devez implémenter un sandbox configurable (imports, accès au système de fichiers), comme précisé en section 5.2.
- Vos outils doivent fonctionner indépendamment de la boucle de l'agent.
- Vous ne devez utiliser aucune bibliothèque qui réimplémente une logique d'orchestration d'agent (par ex. llama-index, smolagents, langgraph, crewai, autogen).
- La boucle de l'agent doit être votre propre implémentation.
- Même si le projet peut être réalisé sans, les architectures multi-agents sont autorisées, mais l'orchestration doit être votre propre code.

---

## Chapitre V — Partie obligatoire

### V.1 Framework agentique

Dans ce projet, vous devez construire un **framework agentique** capable de résoudre de manière autonome des défis de programmation.
Pour le choix du fournisseur LLM, voir la section 5.6.1 pour des exemples d'API en accès gratuit.

Votre système doit :

1. Implémenter une boucle **Thought → Code → Observation**
2. Extraire le code Python généré par le LLM à partir des réponses du modèle

> **💡 Astuce :** Lors du benchmark entre plusieurs fournisseurs (section 5.7), votre couche d'extraction doit gérer différents formats de sortie produits par les LLM — en fonction de ce sur quoi les LLM utilisés ont été entraînés — pas seulement les blocs de code Python. Liste non exhaustive :
>
> (a) **Blocs de code Python** (principal) — ``` ```python ... ``` <end_code>```
>
> (b) **Appels d'outils XML** — style Anthropic `<invoke name="..."><parameter>...</parameter></invoke>`
>
> (c) **Appels d'outils JSON/Hermes** — `<tool_call>{"name": "...", "arguments": {...}}</tool_call>`
>
> (d) **Format ReAct** — `Action: nom_outil` / `Action Input: {...}`
>
> Les formats non-Python doivent être convertis en appels de fonctions Python équivalents (par ex. `result = read_file(filepath="/testbed/file.py")`) avant l'exécution dans le sandbox. Cela permet au sandbox de rester agnostique du format tout en supportant n'importe quel modèle.

3. Exécuter le code généré à l'intérieur d'un environnement sandboxé
4. Renvoyer les résultats d'exécution du sandbox au LLM
5. Résoudre les tâches de benchmark de manière autonome via la boucle de l'agent
6. Concevoir le **system prompt**, incluant :
   - une documentation claire des outils disponibles
   - des exemples de structure de réponse (par ex. Thought, Code, Observation)
   - des exemples de boucles de raisonnement d'agent efficaces

> **⚠️ Important :** Votre sandbox doit fournir un retour explicite au LLM dans toutes les situations suivantes :
> - Aucun bloc de code valide n'a été trouvé dans la réponse du modèle
> - Un bloc de code était malformé mais a quand même été interprété (expliquer comment)
> - L'exécution a atteint le timeout et la sortie est partielle
> - La sortie d'un outil a été tronquée à cause de limites de taille
> - Une édition a introduit une erreur de syntaxe ou une violation de lint
>
> Le LLM ne doit jamais être laissé dans l'incertitude sur ce qui s'est passé. Les échecs silencieux mènent à des observations hallucinées et des itérations gaspillées.

#### V.1.1 Modèles de sortie communs

Les agents MBPP et SWE-bench produisent tous deux la même structure `StepMetrics`/`SolutionOutput` ; seule la sémantique des champs `benchmark` et `solution` change (code Python pour MBPP, patch git pour SWE-bench).

```python
class StepMetrics(BaseModel):
    """Métriques pour une étape unique de l'agent.

    Chaque étape correspond à un cycle génération LLM -> exécution sandbox.
    Tous les champs sont requis pour l'évaluation, des chaînes vides sont
    acceptables pour les étapes où un champ ne s'applique pas (par ex.
    pas d'exécution sandbox).
    """
    step: int = Field(..., description="Numéro d'itération (indexé à partir de 1)")
    input_tokens: int = Field(..., description="Tokens envoyés au LLM pour cette étape")
    output_tokens: int = Field(..., description="Tokens générés par le LLM pour cette étape")
    request_time_ms: float = Field(..., description="Temps réel (wall-clock) de l'appel à l'API LLM, en millisecondes")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp ISO 8601 de l'enregistrement de cette étape")
    api_url: str = Field(default="", description="URL de base du endpoint de l'API LLM (par ex. 'https://openrouter.ai/api/v1')")
    model_name: str = Field(default="", description="Identifiant du modèle utilisé pour cette étape (par ex. 'qwen/qwen3-235b-a22b-2507')")
    llm_output: str = Field(default="", description="Texte brut généré par le LLM avant extraction du code")
    sandbox_input: str = Field(default="", description="Code Python envoyé au sandbox pour exécution")
    sandbox_output: str = Field(default="", description="Résultat d'exécution du sandbox (stdout/stderr/message d'erreur)")
    retries: int = Field(default=0, description="Nombre de retries d'appel API LLM avant d'obtenir une réponse réussie (0 = succès au premier essai)")


class SolutionOutput(BaseModel):
    """Sortie de la solution de l'étudiant, format requis pour l'évaluation.

    C'est la structure JSON que votre agent doit produire et écrire dans
    solution.json. La moulinette valide ceci par rapport à la correction
    de la tâche et aux limites de métriques.
    """
    task_id: str = Field(..., description="Identifiant de tâche (task_id MBPP en chaîne, ou instance_id SWE-bench)")
    benchmark: str = Field(..., description="Type de benchmark : 'mbpp' ou 'swebench'")
    success: bool = Field(..., description="Si l'agent pense avoir résolu la tâche")
    solution: str = Field(..., description="Pour MBPP : le code Python de la fonction. Pour SWE-bench : le patch git (diff)")
    iterations: int = Field(..., description="Nombre d'itérations de la boucle de l'agent utilisées")
    total_requests: int = Field(..., description="Nombre total de requêtes API LLM effectuées (retries inclus)")
    total_input_tokens: int = Field(..., description="Somme des input_tokens sur toutes les étapes")
    total_output_tokens: int = Field(..., description="Somme des output_tokens sur toutes les étapes")
    total_time_seconds: float = Field(..., description="Temps réel (wall-clock) du début à la fin de l'agent")
    steps: List[StepMetrics] = Field(default_factory=list, description="Métriques par étape, une entrée par itération de l'agent")
    system_prompt: str = Field(default="", description="System prompt complet envoyé au LLM (pour vérification de provenance)")
    error: Optional[str] = Field(default=None, description="Message d'erreur si l'agent a échoué (None si succès)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp ISO 8601 de la production de la solution")
```

> **ℹ️ Info :** Chaque étape du tableau `steps` de `SolutionOutput` doit inclure `api_url`, `model_name` (champs identifiant le endpoint LLM utilisé pour cette étape), ainsi que `llm_output` (réponse brute du LLM), `sandbox_input` (code envoyé au sandbox), `sandbox_output` (résultat d'exécution), et `retries` (nombre de retries API).

#### V.1.2 Approche de développement

Construire un agent autonome est une tâche complexe. Voici des questions pour guider votre développement :

**Pour commencer :** Quel benchmark est le plus simple et devrait être abordé en premier ? Est-ce que je teste avec le modèle le plus performant disponible, ou est-ce que je me handicape avec des contraintes trop tôt ? Mon système peut-il résoudre la tâche la plus simple si les limites de tokens et d'itérations sont temporairement retirées ? Si non, ajouter des contraintes ne fera qu'empirer les choses.

**Déboguer votre agent :** Que se passe-t-il pendant les 3 à 5 premières itérations : difficultés d'appel d'outils, observations hallucinées, ou chemin inattendu ? Ai-je essayé de résoudre la tâche cible moi-même, manuellement, et mon prompt reflète-t-il cette méthodologie ? Pour SWE-bench, décomposez le script d'évaluation en objectifs plus petits et suivez si les tests individuels passent plutôt que d'attendre le succès du script complet.

**Passer à l'échelle :** Une solution qui fonctionne sur une tâche se généralise-t-elle, ou ai-je surajusté (overfit) ? Est-ce que j'optimise trop tôt (tokens, choix de modèle), ou ai-je d'abord prouvé que l'approche fonctionne ? Différents modèles préfèrent différents styles d'appel d'outils : est-ce que je lutte contre les tendances naturelles du modèle, ou est-ce que je travaille avec elles ?

### V.2 Le Sandbox

Cette partie porte sur la conception et l'implémentation d'un sandbox d'exécution sécurisé et configurable pour l'agent.

**1. Implémenter une utilisation en CLI du sandbox**

```bash
# Lancer le sandbox interactif
uv run sandbox

# Avec une configuration personnalisée
uv run sandbox sandbox_template.json

# Avec les outils MBPP (stdio)
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json

# Avec les outils MBPP (HTTP)
uv run sandbox --mcp-server <URL>

# Avec les outils SWE-bench
uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json
```

Le **sandbox interactif** (`uv run sandbox` sans argument de tâche) est un mode ligne de commande de type REPL. Il doit ouvrir un prompt, lire du code saisi par l'utilisateur en boucle, et exécuter chaque entrée dans l'espace de noms du sandbox, soumis aux mêmes restrictions d'import, de système de fichiers, de timeout et de mémoire définies en section 5.2, avec les wrappers d'outils MCP connectés et `final_answer` disponibles. Après chaque entrée, il affiche le résultat ou toute erreur levée et retourne au prompt. Il se termine proprement sur la commande `exit` ou sur EOF (Ctrl+D).

**2. Implémenter un outil `final_answer`**

**Ce qu'est `final_answer` :**
`final_answer` est une fonction appelable que le sandbox injecte dans l'espace de noms d'exécution. Quand le code de l'agent appelle `final_answer(answer_string)`, le sandbox capture l'argument et signale à la boucle de l'agent que la tâche est terminée. La boucle de l'agent se termine alors et produit le `SolutionOutput`.

**Ce que `final_answer` n'est PAS :** `final_answer` n'est **pas** un outil MCP — il n'est fourni par aucun serveur MCP. Il est toujours disponible dans l'espace de noms du sandbox, quel que soit le serveur MCP connecté. Les outils MCP opèrent en dehors du sandbox (par ex. lire des fichiers dans Docker, exécuter des tests), tandis que `final_answer` opère à l'intérieur du sandbox pour contrôler la boucle de l'agent.

**Comment utiliser `final_answer` :**

- **MBPP** : appeler `final_answer(votre_code_solution)` : passez votre code Python en argument
- **SWE-bench** : appeler `final_answer(get_patch())` : passez le patch git récupéré via `get_patch()` en argument

**Frontière architecturale :**
Le sandbox fournit deux types de fonctions appelables dans l'espace de noms d'exécution :

(a) **Wrappers d'outils MCP** : découverts dynamiquement depuis le serveur MCP connecté
(b) **`final_answer`** : toujours présent, fourni par le sandbox lui-même

Quand vous connectez un serveur MCP différent, les wrappers d'outils MCP changent mais `final_answer` reste.

**Propagation des exceptions :** Votre sandbox doit propager correctement les exceptions qui contrôlent le flux du programme. En particulier, `KeyboardInterrupt` et `SystemExit` ne doivent pas être capturées silencieusement — elles doivent atteindre la boucle de l'agent pour un arrêt propre.

**3. Appliquer les contraintes de sécurité du sandbox :** Exécuter du code généré par un LLM est intrinsèquement risqué. Votre sandbox n'est pas juste un composant technique ; c'est une **frontière de sécurité** entre un système autonome et le monde réel.

- **Restrictions d'import** : Seuls les modules de la liste blanche configurée peuvent être importés
- **Restrictions de système de fichiers** : l'accès aux fichiers par le code sandboxé est limité à une liste blanche de répertoires (le champ `allowed_directories` de `SandboxConfig`). Ce sont des chemins que le processus du sandbox lui-même voit, évalués à l'intérieur du sandbox, pas des chemins uniquement côté hôte : tout répertoire que le code doit atteindre doit figurer dans la liste blanche. Plusieurs entrées sont autorisées afin de séparer l'espace de travail de la tâche (par ex. `/testbed`) d'une zone de scratch/runtime accessible en écriture (par ex. `/tmp/agent`) ; tout ce qui est en dehors de la liste blanche est refusé.
- **Pas d'accès réseau** : Empêcher toute connexion réseau sortante ou entrante
- **Timeout d'exécution** : Terminer le code dépassant le timeout configuré (s'applique uniquement au code sandboxé)
- **Limites mémoire** : Terminer le code dépassant l'utilisation RAM autorisée
- **Builtins restreints** : Retirer ou surcharger les builtins dangereux pour empêcher toute escalade de privilèges

**4. Intégrer un serveur MCP**

- Les outils obligatoires doivent être intégrés à l'agent
- Les outils, ressources et prompts MCP doivent être exposés
- Les outils MCP doivent être appelables comme des fonctions Python depuis le sandbox
- Le système sera testé avec un **serveur MCP inconnu**
- Les fichiers d'outils MCP (`mcp_tools_mbpp.py`, `mcp_tools_swebench.py`) doivent se trouver à la racine de votre dépôt
- Les transports stdio et HTTP streamable doivent tous deux être supportés pour les connexions au serveur MCP

**5. Générer un manuel du sandbox** à fournir dans le prompt du LLM, qui doit inclure la documentation des outils MCP, ou la façon d'y accéder.

> **ℹ️ Info :** Le manuel du sandbox doit être généré dynamiquement à partir des schémas d'outils du serveur MCP connecté — noms des outils, descriptions, types de paramètres. Quand un serveur MCP différent est connecté, le manuel doit automatiquement refléter les outils de ce serveur.
> Le manuel est ce que le LLM lit pour comprendre quels outils sont disponibles et comment les appeler.

Les limites et le comportement du sandbox doivent être configurables via des **modèles Pydantic et des fichiers de configuration JSON**.

```python
class SandboxConfig(BaseModel):
    """Configuration du sandbox pour les solutions étudiantes.

    Utilise une approche de liste blanche : seuls les imports dans
    authorized_imports sont autorisés. Tout le reste est bloqué par défaut.
    """
    authorized_imports: List[str] = Field(default_factory=lambda: [
        "math", "math.*",
        "collections", "collections.*",
        "itertools", "re", "json",
        "typing", "typing.*",
        "functools", "operator",
        "heapq", "bisect", "copy",
        "string", "random",
        "datetime", "datetime.*",
        "array", "cmath",
    ])
    allowed_directories: List[str] = Field(default_factory=lambda: [
        "/testbed", "/tmp/agent"
    ])
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512
```

Une entrée finissant par `.*` permet aussi d'importer les sous-modules de ce module (par ex. `collections.*` autorise `collections.abc`).
Quand un serveur MCP différent est connecté, le sandbox doit découvrir et exposer dynamiquement les outils de ce serveur. Vos outils obligatoires ne sont présents que lorsque votre propre serveur MCP est connecté.

> **ℹ️ Info :** Le sandbox est la couche d'exécution centrale. Il se connecte à un serveur MCP et expose ses outils comme des fonctions Python appelables dans l'espace de noms du sandbox. Le sandbox englobe le client MCP, et non l'inverse. Le sandbox et les outils MCP sont des domaines de sécurité indépendants : le sandbox restreint ce que le code Python généré par le LLM peut faire (imports, chemins, timeout, mémoire), tandis que les actions des outils MCP se déroulent en dehors du sandbox et ne sont pas soumises au timeout du sandbox (par ex. un outil qui lance un processus externe).

> **⚠️ Important :** Vous devez implémenter les mécanismes de sécurité en utilisant uniquement les bibliothèques et builtins Python standards. Aucun package externe comme RestrictedPython n'est autorisé.

**Approches d'isolation du sandbox**

> **💭 À réfléchir :** code non fiable à l'intérieur de votre propre processus, ou dans un processus séparé ? Chaque choix implique des compromis en termes de frontières de sécurité, de gestion du timeout (comment tuer du code qui tourne indéfiniment ?), et de communication (comment récupérer les résultats ?). Plusieurs approches valides existent, choisissez celle qui convient à votre architecture.

### V.3 Agent MBPP

Dans cette partie, vous implémenterez un agent autonome dédié à résoudre des tâches **MBPP (Mostly Basic Python Problems)**.

**1. Implémenter une interface CLI de l'agent**

```bash
# 1. Extraire une tâche
cd moulinette
uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json

# 2. Lancer votre agent
cd ../student
uv run python -m agent_mbpp --task-file ../cache/mbpp_task.json \
  --output ../cache/mbpp_solution.json \
  --model-name "model/name" --provider-url "https://provider.api/v1"

# 3. Valider la solution
cd ../moulinette
uv run moulinette_eval validate mbpp ../cache/mbpp_task.json \
  ../cache/mbpp_solution.json
```

- Chargement de la tâche
- Exécution de l'agent

**2. Implémenter les outils MCP MBPP**

- `run_tests(code, test_list)`
  Exécute une solution candidate face aux assertions de test données. Renvoie une chaîne JSON avec un booléen `success` (si toutes les assertions ont passé) et un champ `output`.
- Vous pouvez implémenter tout autre outil que vous jugez utile

**3. Définir des modèles Pydantic pour :**

- L'entrée de tâche

```python
class MBPPTaskInput(BaseModel):
    """Entrée pour l'évaluation d'une tâche MBPP."""
    task_id: int
    task_definition: str
    function_definition: str
    test_imports: List[str] = Field(default_factory=list)
    test_list: List[str] = Field(default_factory=list)
```

- Sortie de l'agent : mêmes modèles `StepMetrics`/`SolutionOutput` qu'en section 5.1 (`benchmark="mbpp"`, `solution` = votre code de fonction)

**4.** Concevez votre agent pour opérer dans les limites définies en section 6.1 (itérations, tokens, temps). L'évaluation valide que la sortie de votre agent reste dans ces limites. `max_iterations` doit être un paramètre configurable de votre boucle d'agent.

Les fournisseurs LLM externes sont autorisés, à condition que l'interface reste conforme aux contraintes du projet.

### V.4 Agent SWE-bench

Cette partie porte sur l'implémentation d'un agent autonome capable de résoudre des tâches **SWE-bench** à l'intérieur d'environnements Dockerisés.

Pour SWE-bench, les deux approches sont valides :
(a) déployer le sandbox à l'intérieur du conteneur Docker, ou
(b) exécuter le sandbox sur l'hôte avec des outils MCP qui font le pont vers Docker.

Quel que soit le choix, les contraintes de sécurité du sandbox doivent être appliquées.

- Corriger de vrais bugs ou implémenter des fonctionnalités dans de vrais dépôts
- Explorer des bases de code à l'intérieur de conteneurs Docker, vous êtes responsable de leur nettoyage après l'exécution de votre programme
- Générer et soumettre des patchs valides en utilisant `git -c core.fileMode=false diff`

> **⚠️ Important :** Lors du test de vos outils SWE-bench en isolation, la moulinette définit la variable d'environnement `TESTBED_PATH` pointant vers la racine du dépôt avant de démarrer votre serveur MCP. Vos outils doivent lire exactement cette variable pour localiser le dépôt.

Vous pouvez installer des dépendances supplémentaires à l'intérieur du conteneur Docker (par ex. ruff, jedi, tree) pour améliorer vos outils.

> **❓ Pour vos premiers tests**, essayez d'abord la tâche la plus simple :
> `sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`. Que se passe-t-il si vous retirez les outils inutilisés de votre configuration ?

**1. Implémenter une interface CLI de l'agent**

```bash
# 1. Extraire une tâche
cd moulinette
uv run moulinette_eval dump swebench --output ../cache/swebench_task.json

# 2. Lancer votre agent
cd ../student
uv run python -m agent_swebench --task-file ../cache/swebench_task.json \
  --output ../cache/swebench_solution.json \
  --model-name "model/name" --provider-url "https://provider.api/v1"

# 3. Valider la solution
cd ../moulinette
uv run moulinette_eval validate swebench ../cache/swebench_task.json \
  ../cache/swebench_solution.json
```

**2. Implémenter les outils MCP SWE-bench**

- Les outils doivent suivre la spécification définie dans « Outils obligatoires »
- Vous pouvez implémenter tout autre outil que vous jugez utile

**3. Définir des modèles Pydantic pour :**

- L'entrée de tâche

```python
class SWEBenchTaskInput(BaseModel):
    """Entrée pour une tâche SWE-bench, fournie par la moulinette.

    Votre agent reçoit ceci et doit produire un patch git qui corrige
    le problème.
    """
    instance_id: str = Field(..., description="Identifiant d'instance SWE-bench (par ex. 'sympy__sympy-23534')")
    problem_statement: str = Field(..., description="Description de l'issue GitHub, ce qui doit être corrigé")
    docker_image: str = Field(..., description="Nom complet de l'image Docker à télécharger (par ex. 'swebench/sweb.eval.x86_64.sympy_1776_sympy-23534:latest')")
    eval_script: str = Field(..., description="Script bash à exécuter dans le conteneur pour évaluer le patch")
    hints_text: str = Field(default="", description="Indices optionnels sur le problème (peut être vide)")
    repo: str = Field(default="", description="Nom du dépôt (par ex. 'sympy/sympy')")
```

- Sortie de l'agent (patch) : mêmes modèles `StepMetrics`/`SolutionOutput` qu'en section 5.1 (`benchmark="swebench"`, `solution` = votre patch git)

**4.** Appliquer les **limites strictes** définies en section 6.1

Les fournisseurs LLM externes sont autorisés, à condition que l'agent reste pleinement compatible avec l'infrastructure d'évaluation.
`SolutionOutput` doit inclure un champ `system_prompt` contenant le system prompt complet envoyé au LLM. Chaque étape de `steps` doit inclure les champs `llm_output`, `sandbox_input`, et `sandbox_output`, journalisant la réponse brute du LLM, le code Python envoyé au sandbox, et le résultat d'exécution. Un champ `retries` suit le nombre de retries d'appel API LLM nécessaires pour l'étape.

```json
{
  "steps": [
    {
      "step": 1,
      "llm_output": "I'll read the file to understand the module.\n```python\nresult = read_file(filepath=\"/testbed/src/module.py\")\n```",
      "sandbox_input": "result = read_file(filepath=\"/testbed/src/module.py\")",
      "sandbox_output": "def solve(x):\n    return x + 1\n...",
      "retries": 0,
      "input_tokens": 1234,
      "output_tokens": 567,
      "..."
    }
  ]
}
```

Ces métadonnées sont examinées pendant l'évaluation pour vérifier que l'agent a résolu les tâches par une exploration et un raisonnement de code légitimes, et non en cherchant des solutions dans des pull requests, des issues, ou des sources externes.

### V.5 Outils obligatoires

Vous devez implémenter tous les outils suivants. Chaque outil est exposé par le serveur MCP (Model Context Protocol) et sera testé indépendamment dans le contexte du benchmark SWE-bench.

#### V.5.1 Outils système de fichiers

- **`read_file(filepath, start_line, end_line)`**
  Lit le contenu d'un fichier avec les numéros de ligne. Le format de sortie doit être similaire à `cat -n` :
  ```
  <numéro_ligne>: <contenu_ligne>
  <numéro_ligne>: <contenu_ligne>
  ...
  ```

- **`edit_file(filepath, old_str, new_str)`**
  Remplace une chaîne exacte dans un fichier par une nouvelle chaîne.

- **`list_files(directory, pattern)`**
  Liste les fichiers d'un répertoire correspondant à un motif donné.

#### V.5.2 Outils de recherche de code

- **`search_code(pattern, file_pattern)`**
  Effectue une recherche de type grep dans la base de code. La sortie doit suivre ce format :
  ```
  /chemin/absolu/vers/fichier.py:<numéro_ligne> <contenu_ligne>
  /chemin/absolu/vers/autre_fichier.py:<numéro_ligne> <contenu_ligne>
  ...
  ```

- **`search_function_or_class_definition_in_code(name)`**
  Trouve la définition d'une fonction ou d'une classe. Le format de sortie doit être similaire à celui de `search_code`.

- **`find_references(name, filepath, line)`**
  Trouve tous les usages d'un symbole (fonction ou classe). Le format de sortie doit être similaire à celui de `search_code`.

#### V.5.3 Outils d'exécution

- **`run_tests()`**
  Exécute le script d'évaluation.

- **`get_patch()`**
  Récupère le diff git unifié de toutes les modifications apportées au dépôt, selon l'implémentation.

- **`run_command(command, workdir)`**
  Exécute une commande shell dans le répertoire de travail spécifié. Renvoie le stdout, le stderr et le code de sortie de la commande.

### V.6 Fournisseurs d'API LLM

Pour implémenter votre agent, vous aurez besoin d'effectuer des appels à des **API de Large Language Model (LLM)**. Plusieurs fournisseurs offrent des niveaux gratuits ou des quotas d'usage suffisants pour le développement et l'expérimentation.

La liste ci-dessous est fournie **à titre illustratif uniquement**. Elle est basée sur des ressources publiquement disponibles et peut évoluer avec le temps.
**Vous êtes libre d'utiliser d'autres fournisseurs** tant que votre système respecte les exigences du projet (niveau gratuit, plusieurs tokens API par fournisseur).

Le dataset sur lequel votre agent est évalué s'appelle SWE-bench Verified. En le sachant, vous pouvez trouver :

- **Classements de modèles (leaderboards)** : quels LLM performent le mieux sur des tâches de code réelles ?
- **Descriptions de systèmes d'agent** : comment les systèmes les plus performants conçoivent-ils leur boucle d'agent, leurs outils et leurs prompts ?
- **Traces et évaluations par tâche** — comment un modèle spécifique performe-t-il sur la tâche exacte sur laquelle vous itérez ? Cela peut aider à choisir le bon modèle pour vos premiers cycles de débogage.

> **❓** Que se passe-t-il si le modèle continue à générer après un appel d'outil au lieu d'attendre la vraie sortie d'exécution ? Utilisez un paramètre d'API `stop_sequences` (ou `stop`) (par ex. `<end_code>`, `</tool_call>`) pour arrêter la génération au token qui termine un bloc de code, sinon le modèle risque d'halluciner une fausse sortie d'outil au lieu d'attendre la vraie.

#### V.6.1 Exemples de fournisseurs gratuits

Exemples : OpenRouter, Together AI, Groq, Google AI Studio (Gemini), Mistral AI, Cohere, Fireworks AI, Perplexity AI, et Anyscale (liste non exhaustive).
Assurez-vous que votre implémentation supporte **plusieurs clés API par fournisseur** et envisagez d'implémenter un fallback entre fournisseurs. Les limites de débit et les quotas peuvent varier, en particulier sous charge pendant l'évaluation.

**Important :**

- Cette liste n'est **pas exhaustive et non contractuelle**.
- Les conditions d'accès, quotas et modèles disponibles peuvent évoluer avec le temps.
- Les apprenants sont encouragés à explorer d'autres fournisseurs ou à utiliser des modèles auto-hébergés si nécessaire.
- **L'intégralité de la solution doit reposer exclusivement sur des niveaux gratuits.**
  - Aucun plan payant, crédit acheté, ou compte avec facturation activée n'est autorisé.
  - Le projet doit être entièrement exécutable en n'utilisant que des quotas gratuits au moment de l'évaluation.
- **La gestion multi-tokens est obligatoire.**
  - Votre système doit supporter **plusieurs clés API par fournisseur**.
  - La rotation de tokens doit être implémentée pour gérer les limites de débit et l'épuisement des quotas.
- Votre implémentation doit être suffisamment **abstraite** pour permettre de changer de fournisseur sans refactorisation majeure.

> **ℹ️ Info :** Le choix du fournisseur n'est pas noté. C'est la qualité de votre abstraction, de la gestion d'erreurs, et de l'architecture globale qui compte.

### V.7 Rapport de benchmark de modèles

Le taux de réussite brut ne raconte qu'une partie de l'histoire de quel modèle est le meilleur pour votre agent — l'efficacité d'exploration, le coût en tokens, la fiabilité du fournisseur et la discipline d'itération comptent aussi. Vous devez produire un rapport de benchmark (`BENCHMARK_REPORT.md` à la racine de votre dépôt) comparant **au moins 5 modèles** sur **au moins 2 fournisseurs**, sur le même ensemble d'**au moins 3 tâches SWE-bench**.

> **💡 Astuce :** Les fournisseurs en niveau gratuit imposent des quotas quotidiens de tokens/requêtes, et exécuter 5 modèles peut épuiser un fournisseur avant d'avoir terminé. Puisque plus de fournisseurs signifie plus de quotas indépendants dans lesquels puiser, nous recommandons de garder plus de 2 fournisseurs prêts plutôt que le strict minimum, afin qu'un seul mur de quota ne bloque pas votre run de benchmark.

Votre rapport doit inclure :

1. **Setup** : Quels modèles/fournisseurs ont été comparés, quelles tâches ont été utilisées, et pourquoi ces tâches ont été choisies
2. **Tableau de résultats** : Pour chaque combinaison modèle × tâche :
   - Réussite/Échec
   - Itérations utilisées
   - Total de tokens d'entrée
   - Total de tokens de sortie
   - Temps réel (wall-clock)
3. **Fiabilité du fournisseur** : Pour chaque modèle/fournisseur :
   - Temps de réponse moyen par requête
   - Nombre de retries nécessaires (limites de débit, timeouts, erreurs)
   - Disponibilité globale pendant les runs de benchmark
4. **Métriques intermédiaires** (au moins 2 des suivantes) :
   - Étape à laquelle l'agent lit/édite pour la première fois le fichier qui apparaît dans le patch final (efficacité d'exploration)
   - Étape à laquelle les échecs de tests diminuent pour la première fois par rapport à la baseline (progrès partiel)
   - Itérations entre le « premier passage des tests » et `final_answer` (discipline de soumission — zéro est idéal)

   Ces métriques peuvent être mesurées manuellement en inspectant vos fichiers `solution.json` — l'automatisation n'est pas requise. Ce qui compte, c'est l'analyse, pas l'outillage.
5. **Étude d'ablation** : Au moins une comparaison avant/après d'un changement apporté à votre agent (prompt, outils, paramètres) sur les mêmes tâches avec le même modèle
6. **Conclusions** : Quel(s) modèle(s) vous avez sélectionné(s) pour votre pipeline final et pourquoi. Quels modèles peuvent être écartés et pourquoi. Basé sur vos données.

Les fichiers `solution.json` correspondants doivent être présents dans votre dépôt.

---

## Chapitre VI — Évaluation

Pendant l'évaluation, les clés API et la configuration sont fournies via un fichier `.env` passé en argument obligatoire aux scripts d'évaluation :

```bash
./exam_TYPE.sh --student-path ./student --moulinette-path ./moulinette --env-file /path/to/.env
```

Votre CLI doit supporter le chargement des clés API depuis des variables d'environnement. Les étudiants doivent utiliser des variables d'environnement standards (par ex. `OPENROUTER_API_KEY`).

| `exam_mbpp.sh` | `exam_swebench.sh` | `exam_sandbox.sh` |
|---|---|---|
| 5 tâches aléatoires | 3 tâches aléatoires | Tests de sécurité |
| Réussite : 4/5 | Réussite : 2/3 | Réussite : TOUS |
| Pour chaque tâche : 1. extraire tâche, 2. lancer agent, 3. valider | Pour chaque tâche : 1. extraire tâche, 2. lancer agent, 3. valider, 4. nettoyage du conteneur | Tests : blocage d'import, blocage de builtin, blocage réseau, restriction de chemin, timeout, limite mémoire, protocole MCP |

*Tableau VI.1 : Résumé des scripts d'examen et des tâches. Les limites d'itération/tokens/timeout sont détaillées en section 6.1.*

*(Schéma DUMP → RUN → VALIDATE : `moulinette dump TYPE --output task.json` → `student_agent --task-file task.json --output solution.json` → `moulinette validate TYPE task.json solution.json` ; produit un task.json (entrée) → l'agent résout dans les limites → vérification de la solution contre les tests et vérification des métriques dans les limites → PASS ou FAIL)*

### VI.1 Exigences strictes et limites

Votre implémentation doit respecter strictement les limites d'exécution suivantes. Dépasser l'une de ces limites entraînera l'échec de la tâche correspondante.

#### VI.1.1 Limites MBPP

| Métrique | Limite |
|---|---|
| Itérations maximum | 10 |
| Tokens d'entrée maximum | 6 000 |
| Tokens de sortie maximum | 1 500 |
| Timeout | 120 secondes |

#### VI.1.2 Limites SWE-bench

| Métrique | Limite |
|---|---|
| Itérations maximum | 30 |
| Tokens d'entrée maximum | 300 000 |
| Tokens de sortie maximum | 10 000 |
| Timeout | 900 secondes |

- Les limites de tokens sont **cumulatives** sur toutes les itérations d'une seule tâche (tous les cycles Thought → Code → Observation combinés).
- Les tokens de réflexion/raisonnement (utilisés par les modèles de raisonnement) comptent dans la limite comme tous les autres tokens.
- Si les tokens de raisonnement de votre modèle rendent les limites trop serrées, envisagez d'utiliser un modèle non raisonneur.
- Le timeout est appliqué en tuant de force le processus de votre agent (et tout processus qu'il a engendré) avec `SIGTERM` puis `SIGKILL` s'il n'a pas répondu à temps, pas juste vérifié après coup. Pour SWE-bench, assurez-vous que le nettoyage de votre conteneur Docker puisse quand même s'exécuter dans ce cas (par ex. un gestionnaire de signal), ou se termine assez rapidement pour que ce cas ne soit généralement pas atteint.

### VI.2 Critères de réussite

| Benchmark | Tâches | Seuil de réussite |
|---|---|---|
| MBPP | 5 tâches aléatoires | 4 sur 5 |
| SWE-bench | 3 tâches aléatoires | 2 sur 3 |

**Aucun retry n'est autorisé pendant l'examen** : une tâche échouée n'est pas relancée. Cela ne restreint pas la propre logique de retry interne aux appels LLM de votre agent, suivie par `StepMetrics.retries`.

### VI.3 Critères de notation

Pour valider le projet, vous devez satisfaire **toutes** les conditions suivantes :

- Atteindre les critères de réussite pour MBPP et SWE-bench
- Respecter toutes les limites d'itération, de tokens et de timeout
- Tous les outils obligatoires passent des tests indépendants
- Le sandbox passe les tests d'isolation et de sécurité

> **⚠️ Important :** Des clés API codées en dur dans votre code constituent un échec de sécurité. Toutes les clés API doivent être chargées depuis des variables d'environnement ou des fichiers de configuration (`.env`). Toute clé API trouvée dans votre code source sera signalée pendant l'évaluation.

### VI.4 Ce qui sera testé lors de la review

- Correction des outils obligatoires
- Implémentation correcte de la boucle de raisonnement de l'agent
- Garanties de sécurité et d'isolation du sandbox
- Résultats de benchmark de modèles et statistiques de tokens
- Qualité du code, robustesse et architecture globale

> **ℹ️ Info :** Pendant l'évaluation, il vous sera demandé d'effectuer de petites modifications en direct sur votre agent et de le relancer sur une tâche MBPP. Cela teste que vous comprenez votre propre base de code et que les données dans `solution.json` proviennent d'une véritable exécution, et non de valeurs fabriquées. Chaque modification devrait prendre 2 à 5 minutes. Si vous ne trouvez pas où apporter un changement, cela indique que vous ne comprenez pas votre propre base de code. Il vous sera demandé d'annuler tous les changements après l'exercice (par ex. `git checkout`).

#### VI.4.1 Sécurité IA en évaluation

Construire un agent de code autonome soulève d'importantes considérations de sécurité au-delà de la simple sécurité du sandbox. Pendant l'évaluation, nous vérifions que votre agent résout les tâches par un raisonnement et une exploration de code légitimes — et non en exploitant des raccourcis.

Votre agent ne doit **pas** :

- Récupérer des solutions depuis des pull requests, des issues, ou des sources externes
- Utiliser des patchs mémorisés issus de ses données d'entraînement sans exploration réelle
- Contourner les contraintes de sécurité du sandbox
- Accéder à des ressources en dehors du contexte de tâche fourni

`SolutionOutput` inclut les champs `system_prompt`, `llm_output`, `sandbox_input`, et `sandbox_output` précisément afin que les évaluateurs puissent retracer le processus de raisonnement de l'agent. Cette transparence est un élément central du développement responsable de l'IA.

**Toute violation entraînera une note de 0.**

### VI.5 Structure des logs d'évaluation

Les résultats d'évaluation sont stockés dans :

```
./evaluations/EVAL_TYPE/YYYY-MM-DD_HH-MM-SS/task_id/task.json, solution.json, stdout.log, stderr.log
```

---

## Chapitre VII — Exigences du README

Un fichier `README.md` doit être fourni à la racine de votre dépôt Git. Son but est de permettre à toute personne non familière avec le projet (pairs, staff, recruteurs, etc.) de comprendre rapidement de quoi parle le projet, comment l'exécuter, et où trouver plus d'informations sur le sujet.

Le `README.md` doit inclure au minimum :

- La toute première ligne doit être en italique et lire : *This project has been created as part of the 42 curriculum by <login1>[, <login2>[, <login3>[...]]].*
- Une section « **Description** » présentant clairement le projet, y compris son objectif et un bref aperçu.
- Une section « **Instructions** » contenant toute information pertinente sur la compilation, l'installation et/ou l'exécution.
- Une section « **Resources** » listant les références classiques liées au sujet (documentation, articles, tutoriels, etc.), ainsi qu'une description de la façon dont l'IA a été utilisée — en précisant pour quelles tâches et quelles parties du projet.

➠ **Des sections supplémentaires peuvent être requises selon le projet** (par ex. exemples d'utilisation, liste de fonctionnalités, choix techniques, etc.).

*Tout ajout requis sera explicitement listé ci-dessous.*

Votre `README.md` doit inclure :

- L'architecture du système
- L'explication de la boucle de l'agent
- La conception du sandbox
- Les détails d'implémentation des outils
- Les résultats et l'analyse du benchmark

> **ℹ️ Info :** Votre README doit être rédigé en anglais.

---

## Chapitre VIII — Rendu

Soumettez votre projet dans votre dépôt Git. Votre dépôt doit contenir :

- L'architecture interne et la structure des répertoires de votre rendu sont laissées libres.
- Les fichiers de configuration pour le sandbox et les modèles
- `README.md`

> **⚠️ Important :** N'incluez pas d'images Docker, de poids de modèles volumineux, ou de sorties générées.
