# `core/coding/` — Couche de codage interne

**Créé** : 2026-09-22
**Origine** : capture du protocole `core/cognition/antigravity/capabilities.py`
           avant décommissionnement du bridge externe.

## Objectif

Fournir à `coder_worker` un **protocole de codage interne**, inspiré
d'Antigravity mais **sans aucune dépendance externe**.

## Structure

| Fichier | Rôle | Statut |
|---|---|---|
| `__init__.py` | Point d'entrée | ✅ Créé |
| `protocol.py` | Types (`CodingRequest`, `CodingResponse`, enums) | ✅ Créé |
| `policy.py` | Gouvernance (validation) | ✅ Créé |
| `bridge.py` | InternalToolBridge (édition, git, shell) | ⏳ À créer |
| `coder_worker.py` | Boucle `plan → build → verify` | ⏳ À créer |

## Correspondance Antigravity → coding

| Antigravity | coding | Statut |
|---|---|---|
| `AntigravityAgentRequest` | `CodingRequest` | ✅ |
| `AntigravityAgentResponse` | `CodingResponse` | ✅ |
| `AntigravityExecutionMode` | `ExecutionMode` | ✅ |
| `AntigravityEffortLevel` | `EffortLevel` | ✅ |
| `AntigravityOutputFormat` | `OutputFormat` | ✅ |
| `AntigravityPolicyGovernor` | `CodingPolicy` | ✅ |
| `AntigravityDesktopBridge` | `InternalToolBridge` | ⏳ |
| `AntigravityClient` | `CoderWorker` | ⏳ |

## Ce qui est préservé

- ✅ **Modes** : READ_ONLY_SANDBOX, ACCEPT_EDITS, DRY_RUN
- ✅ **Efforts** : LOW, NORMAL, HIGH
- ✅ **Formats** : TEXT, JSON, PATCH
- ✅ **Gouvernance** : whitelist + modes autorisés
- ✅ **Structure de requête/réponse**

## Ce qui est supprimé

- ❌ Dépendance `antigravity-client`
- ❌ Bridge Node.js
- ❌ Appels réseau vers Google Antigravity
- ❌ Service externe

## Prochaines étapes

1. Implémenter `bridge.py` (InternalToolBridge)
2. Implémenter `coder_worker.py` (boucle interne)
3. Brancher `model_router` (fédération de modèles)
4. Brancher `audit_ledger` (traçabilité)
5. Tester sur une tâche réelle
6. Décommissionner Antigravity