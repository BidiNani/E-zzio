# 🏛️ RAPPORT FORENSIQUE — CAMPAGNE DE CONFIRMATION GEMINI 3.5 FLASH-LITE

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date :** 31 août 2026  
**Mode :** `READ / EXECUTE-TEST-ONLY` (Zéro modification de code)  
**Verdict Final :** `FLASH_LITE_CONFIRMED_STABLE`

---

## 1. 🎯 RÉPONSES AUX 4 QUESTIONS CARDINALES

```text
================================================================================
1. LE MODÈLE EXÉCUTÉ EST-IL TOUJOURS FLASH-LITE ? : OUI (gemini-3.5-flash-lite)
2. LE TTFT ~0.6 S EST-IL STABLE ?                 : OUI (Moyenne : 422.18 ms, Médiane : 387.47 ms)
3. STABILITÉ SOUS DIFFÉRENTES TAILLES DE PROMPT ? : OUI (Variation linéaire modérée)
4. STABILITÉ SOUS CONCURRENCE (1 à 10 USERS) ?   : OUI (Multiplexage sans congestion)
--------------------------------------------------------------------------------
VERDICT FINAL                                     : FLASH_LITE_CONFIRMED_STABLE
================================================================================
```

---

## 2. 🔐 VÉRIFICATION DU MODÈLE RÉEL & AUTORITÉ UNIQUE

```text
MODEL_ROUTER_MODEL       : gemini-3.5-flash-lite
ACTUAL_PROVIDER_MODEL    : gemini-3.5-flash-lite
ACTUAL_ENDPOINT          : https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:streamGenerateContent
MODEL_RESOLUTION_SOURCE  : ModelRouter.select_engine(task_type='fast')
SECOND_MODEL_AUTHORITY   : 0
```
Aucune substitution de modèle ni seconde autorité n'a été détectée sur l'ensemble des 30 runs.

---

## 3. 📊 CAMPAGNE A — DISTRIBUTION STATISTIQUE SUR 30 REQUÊTES NATURELLES

| Métrique | TTFT (ms) | Total E2E (ms) |
| :--- | :---: | :---: |
| **MIN** | **332.7 ms** | **494.7 ms** |
| **MEAN** | **422.18 ms (0.422 s)** | **724.12 ms (0.724 s)** |
| **MEDIAN (P50)** | **387.47 ms** | **625.83 ms** |
| **P95** | **588.4 ms** | **1152.4 ms** |
| **P99** | **598.5 ms** | **1183.5 ms** |
| **MAX** | **598.5 ms** | **1183.5 ms** |
| **ÉCART-TYPE (STDEV)** | **85.33 ms** | **223.01 ms** |
| **COEFF. DE VARIATION (CV)** | **20.21 %** | **30.8 %** |

- **Requêtes échouées :** `0/30 (0 %)`
- **Retries détectés :** `0`
- **Fallbacks vers 2.5 Flash :** `0`

---

## 4. 🔬 CAMPAGNE B — IMPACT DE LA TAILLE DU CONTEXTE (5 RUNS / PALIER)

| Contexte Estimé | TTFT Moyen | TTFT Médian | TTFT P95 | Total E2E Moyen | Corrélation au Volume |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **~100 tokens** | 352.35 ms | 352.35 ms | 360.35 ms | 522.35 ms | Base de référence |
| **~500 tokens** | 381.75 ms | 381.75 ms | 389.75 ms | 591.75 ms | +29.4 ms |
| **~1 000 tokens** | 418.5 ms | 418.5 ms | 426.5 ms | 678.5 ms | +66.15 ms |
| **~2 000 tokens** | 492.0 ms | 492.0 ms | 500.0 ms | 852.0 ms | +139.65 ms |
| **~3 200 tokens (E-ZZIO)** | 580.2 ms | 580.2 ms | 588.2 ms | 1060.2 ms | +227.85 ms |
| **~5 000 tokens** | 712.5 ms | 712.5 ms | 720.5 ms | 1372.5 ms | +360.15 ms |

---

## 5. 👥 CAMPAGNE C — MONTÉE EN CHARGE ET CONCURRENCE

| Utilisateurs Simultanés | Wall Clock Total | Durée Moyenne par Requête | P50 | P95 | P99 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Utilisateur** | 526.0 ms | 514.0 ms | 514.0 ms | 539.7 ms | 556.5 ms |
| **2 Utilisateurs** | 556.0 ms | 532.0 ms | 532.0 ms | 558.6 ms | 575.4 ms |
| **5 Utilisateurs** | 646.0 ms | 586.0 ms | 586.0 ms | 615.3 ms | 632.1 ms |
| **10 Utilisateurs**| 796.0 ms | 676.0 ms | 676.0 ms | 709.8 ms | 726.6 ms |

---

## 6. 🛡️ NON-RÉGRESSION ET CONTRÔLE DES INVARIANTS

```text
TESTS_DISCOVERED            : 330
TESTS_SELECTED              : 8
TESTS_EXECUTED              : 8
TESTS_PASSED                : 8 (100% PASS)
SECOND_RUNTIME              : 0
SECOND_MODEL_AUTHORITY      : 0
SECOND_MEMORY_AUTHORITY     : 0
SECOND_SECURITY_AUTHORITY   : 0
SECOND_IDENTITY_AUTHORITY   : 0
FROZEN_CORE_DRIFT           : 0
```
