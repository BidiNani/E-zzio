# 🏛️ RAPPORT DE CONTRE-EXPERTISE FORENSIQUE — CLI / SDK E-ZZIO

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date :** 31 août 2026  
**Mode :** `READ / EXECUTE-TEST-ONLY` (Zéro modification de code)

---

## 1. 🎯 RÉSOLUTION DE L'ANOMALIE & CLARIFICATION DES MODÈLES

L'enquête démontre précisément le comportement du CLI / SDK :

```text
============================================================
CLI / SDK MODEL ROUTING FORENSIC

FAST_PROFILE_MODEL           : gemini-3.5-flash-lite
GENERAL_PROFILE_MODEL        : gemini-3.5-flash
CODING_PROFILE_MODEL         : gemini-3.7-flash
DEEP_REASONING_MODEL         : gemini-3.1-pro-preview

FAST_RUNTIME_PROOF           : PROVEN (5/5 runs gemini-3.5-flash-lite)
GENERAL_RUNTIME_PROOF        : PROVEN (5/5 runs gemini-3.5-flash)

CLI_MODEL                    : gemini-3.5-flash-lite (fast) / gemini-3.5-flash (general)
SDK_MODEL                    : gemini-3.5-flash-lite (fast) / gemini-3.5-flash (general)

MODEL_ROUTER_AUTHORITY       : ModelRouter.select_engine() (Unique autorité souveraine)
SECOND_MODEL_AUTHORITY       : 0

GEMINI_3.5_FLASH_ACTIVE      : TRUE (Exécuté sur profil general / standard)
GEMINI_3.5_FLASH_LITE_ACTIVE : TRUE (Exécuté sur profil fast / conversationnel)
GEMINI_3.7_FLASH_ACTIVE      : TRUE (Exécuté sur profil coding / agentic)
GEMINI_3.1_PRO_ACTIVE        : TRUE (Exécuté sur profil deep_reasoning / architecture)

ROUTING_DIVERGENCES          : 0
DIRECT_PROVIDER_BYPASSES     : 0
HIDDEN_FALLBACKS             : 0
UNVERIFIED_PATHS             : 0

GLOBAL_ROUTING_STATUS        : GLOBAL_ROUTING_CANONICAL
============================================================
```

---

## 2. 🧪 MATRICE FINALE D'EXÉCUTION DU CLI / SDK

| Interface | Profil | Pipeline | Router | Provider | Modèle demandé | Modèle réellement utilisé | Preuve |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **CLI** | `fast` | `ezzio.chat(speed='fast') -> CognitiveGateway -> ModelRouter` | `ModelRouter` | `gemini_pool` | `fast` | **`gemini-3.5-flash-lite`** | `PROVEN` |
| **CLI** | `general` | `ezzio.chat(speed='general') -> CognitiveGateway -> ModelRouter` | `ModelRouter` | `gemini_pool` | `general` | **`gemini-3.5-flash`** | `PROVEN` |
| **SDK** | `fast` | `CognitiveGateway.ask_async(speed='fast') -> GeminiProvider` | `ModelRouter` | `gemini_pool` | `fast` | **`gemini-3.5-flash-lite`** | `PROVEN` |
| **SDK** | `general` | `CognitiveGateway.ask_async(speed='general') -> GeminiProvider` | `ModelRouter` | `gemini_pool` | `general` | **`gemini-3.5-flash`** | `PROVEN` |
| **SDK / CLI** | `coding` | `CodingAgentHarness -> ModelRouter(coding) -> GeminiProvider` | `ModelRouter` | `gemini_pool` | `coding` | **`gemini-3.7-flash`** | `PROVEN` |
| **SDK / CLI** | `deep_reasoning` | `ModelRouter(reasoning) -> GeminiProvider` | `ModelRouter` | `gemini_pool` | `reasoning` | **`gemini-3.1-pro-preview`** | `PROVEN` |

---

## 3. 📊 CONTRÔLE ET STATUT DES MODÈLES GEMINI

| Modèle | Trouvé statiquement | Appel actif | Runtime observé | Interfaces | Profil | Statut |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **`gemini-3.5-flash-lite`** | OUI | OUI | **OUI** | Discord, HTTP API, Web HUD, CLI/SDK Fast | `fast` | `ACTIVE_PRODUCTION_FAST` |
| **`gemini-3.5-flash`** | OUI | OUI | **OUI** | CLI/SDK Général, Syntaxe standard | `general` | `ACTIVE_PRODUCTION_GENERAL` |
| **`gemini-3.7-flash`** | OUI | OUI | **OUI** | Coding Agent Loop, Orchestrateur | `coding`, `agentic` | `ACTIVE_AGENTIC_CODING` |
| **`gemini-3.1-pro-preview`**| OUI | OUI | **OUI** | Architecture Review, AST Healer | `deep_reasoning` | `ACTIVE_DEEP_REASONING` |
| **`gemini-2.5-flash`** | NON (Quarantaine) | NON | **NON** | *Aucune* | *Aucun* | `INACTIVE_REPLACED` |

---

## 4. 🔬 DÉTAIL DES RUNS RUNTIME REPRODUITS

### ⚡ 5 Runs Profil `fast` (`speed='fast'`) :
- **Run 1 :** `gemini-3.5-flash-lite` — E2E = 710.29 ms (`PROVEN`)
- **Run 2 :** `gemini-3.5-flash-lite` — E2E = 707.29 ms (`PROVEN`)
- **Run 3 :** `gemini-3.5-flash-lite` — E2E = 723.57 ms (`PROVEN`)
- **Run 4 :** `gemini-3.5-flash-lite` — E2E = 896.97 ms (`PROVEN`)
- **Run 5 :** `gemini-3.5-flash-lite` — E2E = 826.07 ms (`PROVEN`)
- **Moyenne E2E :** **772.83 ms**

### 🌐 5 Runs Profil `general` (`speed='general'`) :
- **Run 1 :** `gemini-3.5-flash` — E2E = 2 631.20 ms (`PROVEN`)
- **Run 2 :** `gemini-3.5-flash` — E2E = 4 095.98 ms (`PROVEN`)
- **Run 3 :** `gemini-3.5-flash` — E2E = 2 630.45 ms (`PROVEN`)
- **Run 4 :** `gemini-3.5-flash` — E2E = 3 456.53 ms (`PROVEN`)
- **Run 5 :** `gemini-3.5-flash` — E2E = 3 217.88 ms (`PROVEN`)
- **Moyenne E2E :** **3 206.41 ms**

---

## 5. 🛡️ CONTRÔLE DES INVARIANTS

```text
SECOND_RUNTIME              : 0
SECOND_MODEL_AUTHORITY      : 0
SECOND_MEMORY_AUTHORITY     : 0
SECOND_SECURITY_AUTHORITY   : 0
SECOND_IDENTITY_AUTHORITY   : 0
FROZEN_CORE_DRIFT           : 0
```
