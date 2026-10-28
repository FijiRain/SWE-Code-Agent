# Bucket List d'Intégration Orchestrator <-> Sandbox

Ce document récapitule les points clés à valider entre **l'Orchestrateur** et la **Sandbox** avant et pendant le merge de nos deux branches.

---

## 1. Cycle de vie de la Sandbox (Instanciation & Nettoyage)

- [x] **Point d'instanciation (`complete_task`) :**
  - Instancier la Sandbox au début de `complete_task(task)` dans `src/orchestration/orchestrator.py` plutôt que dans `__init__()`.
  - *Raison :* Chaque tâche doit démarrer dans un état vierge et isolé (particulièrement critique pour SWE-bench où l'image Docker / le repo changent par tâche).
- [x] **Signature du constructeur :**
  - Valider le nom de la classe et les arguments requis pour l'instanciation :
    - Est-ce `Sandbox(task)` ou une classe par benchmark (`MBPPSandbox()`, `SWESandbox(task)`) ?
- [x] **Nettoyage automatique des conteneurs (`close` / `cleanup`) :**
  - Vérifier la méthode de fermeture (`sandbox.close()`, `sandbox.cleanup()` ou support du context manager `with Sandbox(...) as sandbox:`).
  - L'intégrer dans un bloc `finally:` à la fin de `complete_task()` pour éviter les conteneurs Docker zombies saturant la mémoire.

---

## 2. Gestion des erreurs et résilience (`try / except`)

- [x] **Erreurs dans le code du LLM (gérées par la Sandbox) :**
  - Si le code candidat Python crash (`SyntaxError`, `NameError`, `AssertionError`, division par zéro), la méthode `execute()` **ne doit pas** lever d'exception Python.
  - La Sandbox doit intercepter le traceback et renvoyer un objet `ExecutionResult` avec le champ `error="<traceback>"` afin que le LLM puisse analyser l'erreur et s'auto-corriger au tour suivant.
- [ ] **Erreurs système Docker (gérées par l'Orchestrateur) :**
  - Si le moteur Docker crashe ou est inaccessible, l'appel `self.sandbox.execute()` doit être protégé par un `try ... except Exception as e:` dans `complete_task()`.
  - En cas de crash Docker, l'orchestrateur consigne `error = f"Sandbox system failure: {e}"` et stoppe la boucle proprement afin d'écrire un `SolutionOutput` valide avec `success=False`.

---

## 3. Contrat des outils injectés & `sandbox_manual`

- [x] **Injection du manuel (`sandbox_manual`) :**
  - Définir comment l'Orchestrateur récupère la documentation des fonctions injectées :
    - Méthode `sandbox.get_manual() -> str` ou constante partagée ?
    - Cette chaîne sera injectée dans le prompt système via `build_mbpp_sys_prompt(sandbox_manual)`.
- [x] **Alignement strict des signatures d'outils (MBPP) :**
  - Le prompt de l'Orchestrateur instruit le LLM d'appeler :
    1. `run_tests(code: str, test_list: list[str])`
    2. `final_answer(code_string: str)`
  - Confirmer que les fonctions injectées dans l'espace global de la Sandbox portent **exactement ces noms et ces signatures**.
- [ ] **Prise en charge de `test_imports` :** !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  - Pour les tâches MBPP requérant des imports spécifiques (`task.test_imports`), confirmer si `run_tests` les importe en amont ou si le LLM doit inclure les `import` directement dans sa chaîne `code`.

---

## 4. Comportement de `final_answer()` (MBPP & SWE-bench)

- [] **Comportement MBPP :**
  - Lorsque le LLM exécute `final_answer('''def solution(...): ...''')`, confirmer que l'argument capturé dans `ExecutionResult.final_answer` correspond strictement au code Python pur (sans le wrapper `final_answer(...)`).
- [ ] **Anticipation SWE-bench (Génération du patch git) :**
  - Pour SWE-bench, `SolutionOutput.solution` doit contenir le diff Git (`git diff`).
  - Définir si la Sandbox génère automatiquement le patch git lors de l'appel à `final_answer()` pour l'assigner à `ExecutionResult.final_answer`.
  - *Bénéfice :* Si oui, la logique de l'Orchestrateur (`solution = execution_res.final_answer`) reste 100% universelle pour MBPP et SWE-bench.

---

## 5. Emplacement des modèles de données partagés

- [ ] **Déplacement de `ExecutionResult` :**
  - Actuellement dans `tests/test_ExecutionResult.py` pour les mocks temporaires.
  - Déplacer sa définition dans `src/models/output_data_models.py` (ou `src/models/sandbox_models.py`).
  - Permettra à `src/orchestration/` et `src/sandbox/` d'importer directement :
    ```python
    from src.models.output_data_models import ExecutionResult
    ```
