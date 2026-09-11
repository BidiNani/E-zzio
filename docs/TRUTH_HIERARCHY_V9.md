# E-ZZIO V9.0 — TRUTH HIERARCHY & FORENSIC METHODOLOGY

**Date d'Adoption** : 29 août 2026

---

## 1. PRINCIPE DE SUPRÉMATIE DES FAITS SUR LES AFFIRMATIONS
Dans tout audit ou validation du système E-ZzIO, la vérité technique obéit à la hiérarchie d'autorité stricte suivante :

$$\mathbf{\text{RUNTIME OBSERVATION}} > \mathbf{\text{STATIC IMPORT / AST}} > \mathbf{\text{TEST RESULTS}} > \mathbf{\text{CONFIGURATION}} > \mathbf{\text{DOCUMENTATION}}$$

1. **`RUNTIME OBSERVATION` (Niveau 1 — Preuve Suprême)** : Comportement réel des processus en mémoire, ports réseau ouverts, requêtes HTTP observées, transactions SQLite réelles.
2. **`STATIC IMPORT / AST` (Niveau 2 — Preuve Structurelle)** : Arbre syntaxique abstrait, présence physique de modules, graphe effectif des dépendances.
3. **`TEST RESULTS` (Niveau 3 — Preuve Contractuelle)** : Résultat d'exécution des suites automatisées (`pytest`).
4. **`CONFIGURATION` (Niveau 4 — Intention Déclarative)** : Fichiers `.env`, `pyproject.toml`, `settings.json`.
5. **`DOCUMENTATION` (Niveau 5 — Récit Informatif)** : Fichiers Markdown, commentaires de code, synthèses d'agents.

---

## 2. VOCABULAIRE CONTRACTUEL INTERDISANT LES FAUSSES CERTITUDES
Sont formellement proscrits dans les rapports techniques sans preuve mathématique formelle :
- *« 100% sûr »*, *« Zéro risque »*, *« Absolu »*, *« Prouvé universellement »*.

Sont adoptés les termes qualifiés :
- **`RUNTIME VERIFIED`** : Vérifié par exécution réelle et benchmark live.
- **`STATICALLY VERIFIED`** : Vérifié par parcours AST et analyse statique de code.
- **`TEST VERIFIED`** : Validé par assertion dans une suite pytest.
- **`SANDBOXED`** : Confiné et isolé hors du Core.
