# 🛠️ E-ZZIO — CHARTE D'ORCHESTRATION MULTI-AGENT D'ATELIER

**Date d'entrée en vigueur :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Statut :** Politique d'atelier souveraine (n'altère aucun runtime de production).

---

## 1. RÈGLE D'OR DE L'ORCHESTRATION

> **Antigravity est le superviseur souverain d'architecture et de réconciliation.**  
> Le travail d'atelier quotidien est déporté sur les outils déterministes, les modèles locaux Ollama et les agents secondaires spécialisés.

---

## 2. AIGUILLAGE OPÉRATIONNEL PAR AGENT

| ACTEUR | OUTILS / COMMANDES | DOMAINE D'INTERVENTION EXCLUSIF |
|---|---|---|
| **Outils Déterministes** | PowerShell, Python, `git`, `pytest` | Fichiers, hashes, JSON/YAML, arborescence, tests unitaires. |
| **Ollama Local** | `phi4-mini`, `nemotron-3-nano`, `qwen3.5`, `hermes3` | Triage de prompt, classification rapide, filtrage de contexte, résumés concis. |
| **Claude Code** | `G:\npm-global\claude.CMD` | Refactoring lourd multi-fichiers, debugging complexe, refonte de modules. |
| **Codex CLI** | `G:\npm-global\codex.CMD` | Codage ciblé, génération de tests unitaires, documentation technique. |
| **OpenCode** | `G:\npm-global\opencode.CMD` | Routine de maintenance, petits scripts, exploration. |
| **AionUi** | App Desktop Workbench | Tableau de bord visuel, surveillance des flux, monitoring d'atelier. |
| **Antigravity** | Google DeepMind / Gemini 3.7 & 3.1 Pro | **Supervision souveraine, architecture core, preuves formelles, audits de sécurité, arbitrages finaux.** |

---

## 3. WORKFLOW CONTRACTUEL EN 5 ÉTAPES

1. **Classification :** Si la tâche est déterministe $ightarrow$ exécutée immédiatement en local via PowerShell/Python (0 token).
2. **Local AI Check :** Si un filtrage ou un triage léger suffit $ightarrow$ résolu par Ollama en local (0 token).
3. **Délégation Agent :** Si un codage ou refactoring important est requis $ightarrow$ délégué à Claude Code ou Codex CLI.
4. **Supervision Antigravity :** Réservé à l'arbitrage architectural, aux contre-expertises et à la validation des invariants.
5. **Checkpointing :** Persistance obligatoire du résultat sous `state/audit/current/<mission>/` pour interdire toute réinterrogation superflue.
