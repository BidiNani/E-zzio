# 🏛️ E-ZZIO — RAPPORT D'ORCHESTRATION MULTI-AGENT DE L'ATELIER

**Date d'entrée en vigueur :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`

---

## 1. CARTOGRAPHIE DES AGENTS ET DES OUTILS D'ATELIER

L'inspection de l'environnement physique confirme la présence des outils suivants :

| AGENT / OUTIL | EMPLACEMENT PHYSIQUE | RÔLE PRINCIPAL D'ATELIER | COÛT QUOTA ANTIGRAVITY |
|---|---|---|---|
| **Antigravity** | Environnement Native IDE | Superviseur souverain, Architecture, Preuves formelles, Arbitrages | **Quota Premium Justifié** |
| **Claude Code** | `G:\npm-global\claude.CMD` | Refactoring lourd multi-fichiers, Debugging complexe | **0%** |
| **Codex CLI** | `G:\npm-global\codex.CMD` | Codage modulaire, Génération de tests, Documentation | **0%** |
| **OpenCode** | `G:\npm-global\opencode.CMD` | Tâches de routine, Scripts d'atelier | **0%** |
| **AionUi** | Application Desktop Workbench | Tableau de bord visuel & Hub d'interface d'atelier | **0%** |
| **Ollama Local** | `G:\Ollama\ollama.EXE` | Inférence locale (phi4-mini, nemotron-3-nano, qwen3.5, hermes3) | **0%** |
| **Python & pytest** | `G:\Python312\python.EXE` | Scripts déterministes, validation JSON, exécution de tests | **0%** |
| **PowerShell & Git** | `C:\Program Files\Git\cmd\git.EXE` | Gestion de version, fichiers, arborescence, hash | **0%** |

---

## 2. LE PIPELINE D'ORCHESTRATION DÉTERMINISTE & COGNITIF

```
                     ┌────────────────────────────────────────┐
                     │   DEMANDE DE DÉVELOPPEMENT / AUDIT     │
                     └───────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       [ TÂCHE DÉTERMINISTE ]                      [ TÂCHE COGNITIVE ]
                   │                                           │
         ┌─────────┴─────────┐                       ┌─────────┴─────────┐
         ▼                   ▼                       ▼                   ▼
    (PowerShell)          (Python)              (Local LLM)       (Agents Délégués)
    - Test-Path           - pytest              - phi4-mini       - Claude Code
    - Get-ChildItem       - json.load()         - nemotron-nano   - Codex CLI
    - Get-FileHash        - Scripts audit       - qwen3.5:9b      - OpenCode
                                                                       │
                                                       ┌───────────────┘
                                                       ▼
                                            [ COMPLEXITÉ CRITIQUE ]
                                                       │
                                                       ▼
                                           (Antigravity / Gemini)
                                           - Architecture Core
                                           - Preuve & Réconciliation
                                           - Arbitrage Souverain
```

---

## 3. RÈGLES STRICTES DE PRÉSERVATION ARCHITECTURALE

1. **AionUi ≠ E-ZzIO :** AionUi est un poste de travail / workbench externe. E-ZzIO conserve son autonomie et ses autorités souveraines (`ModelRouter`, `UnifiedMemoryGateway`, `SecretsVault`).
2. **Command-First Absolu :** Toute vérification factuelle (existence de fichier, hash, exécution de tests, parsing JSON) est exécutée par des commandes locales déterministes avant toute formulation au LLM.
3. **No-Reask & Checkpoints :** Les artefacts validés sous `state/audit/current/` font foi et sont directement réutilisés.
4. **Zéro Seconde Autorité :** Les caches techniques d'atelier (fichiers, AST, checkpoints) n'interfèrent jamais avec la mémoire SQLite WAL + FTS5 d'E-ZzIO.

---

## 4. ESTIMATION DE LA NOUVELLE RÉPARTITION DE CHARGE

| CATÉGORIE D'ACTEUR | PART DU TRAVAIL AVANT | PART DU TRAVAIL APRÈS | IMPACT SUR LE QUOTA |
|---|---|---|---|
| **Outils Déterministes (PowerShell / Python)** | 0% (Délégué au LLM) | **45%** | **0 token consommé** |
| **Modèles Locaux Ollama** | 0% | **15%** | **0 token consommé** |
| **Agents Secondaires (Claude / Codex / OpenCode)**| 0% | **25%** | **0 quota Antigravity** |
| **Antigravity (Supervision Souveraine)** | 100% | **15%** | **Quota Premium Maîtrisé** |
