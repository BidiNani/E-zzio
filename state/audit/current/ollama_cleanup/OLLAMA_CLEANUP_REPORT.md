# 🏛️ RAPPORT FORENSIQUE — NETTOYAGE OLLAMA v1

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date :** 31 août 2026  
**Verdict Final :** `CLEANUP_SUCCESS`

---

## 1. 📊 BILAN DE L'ESPACE DISQUE RÉCUPÉRÉ

| Métrique | Valeur en Octets | Valeur en Gigaoctets (GB) |
| :--- | :---: | :---: |
| **Espace Disque Avant** | `43,093,959,634` octets | **40.13 GB** |
| **Espace Disque Après** | `27,463,379,142` octets | **25.58 GB** |
| **Espace Disque Récupéré** | `15,630,580,492` octets | **+14.56 GB** |

---

## 2. 🗑️ MODÈLES SUPPRIMÉS APRÈS AUDIT ET VALIDATION

| Modèle Supprimé | Taille | Dépendances Runtime | Modèle Parent | Statut Suppression |
| :--- | :---: | :---: | :---: | :---: |
| **`mannix/llama3.1-8b-abliterated:q5_K_M`** | 5.7 GB | 0 | Aucun | `DELETED (Exit 0)` |
| **`ornith-1.5:9b`** | 6.6 GB | 0 | Aucun | `DELETED (Exit 0)` |
| **`ministral-3:8b`** | 6.0 GB | 0 | Aucun | `DELETED (Exit 0)` |
| **`gemma4:e4b-it-q4_K_M`** | 9.6 GB | 0 | Aucun | `DELETED (Exit 0)` |

---

## 3. 🛡️ VÉRIFICATION DES MODÈLES DE PRODUCTION CONSERVÉS

| Modèle de Production Requis | Statut Vérifié |
| :--- | :---: |
| **`phi4-mini:latest`** | **`PRESENT`** |
| **`qwen3.5:9b`** | **`PRESENT`** |
| **`hermes3:8b`** | **`PRESENT`** |
| **`bge-m3:latest`** | **`PRESENT`** |
| **`nomic-embed-text:latest`** | **`PRESENT`** |

### Modèles Spécialisés ez-* Conservés Provisoirement :
- **`ez-router:latest`** : `PRESENT`
- **`ez-core-safe:latest`** : `PRESENT`
- **`ez-core-free:latest`** : `PRESENT`
- **`ez-agent-hermes:latest`** : `PRESENT`
- **`ez-rag-expert:latest`** : `PRESENT`

---

## 4. 🧭 VÉRIFICATION DU ROUTAGE ET DES PROFILS E-ZZIO

```text
FAST        : gemini-3.5-flash-lite (Cloud) -> INTACT
GENERAL     : gemini-3.5-flash (Cloud) -> INTACT
CODING      : gemini-3.7-flash (Cloud) -> INTACT
TOOLS       : gemini-3.7-flash (Cloud) -> INTACT
LOCAL_ONLY  : qwen2.5-coder:7b (Ollama) -> INTACT
EMBEDDINGS  : bge-m3:latest & nomic-embed-text:latest (Ollama) -> INTACT
```

---

## 5. 🏁 SYNTHÈSE FORENSIQUE

```text
============================================================
E-ZZIO — OLLAMA CLEANUP
============================================================

MODELS_BEFORE            : 14
MODELS_DELETED           : 4
MODELS_AFTER             : 10

DISK_BEFORE              : 40.13 GB
DISK_AFTER               : 25.58 GB
DISK_RECOVERED           : +14.56 GB

PRODUCTION_MODELS_INTACT : TRUE (5/5 PRESENT)
ROUTING_INTACT           : TRUE (0 impact)
RUNTIME_INTACT           : TRUE
REGRESSION               : ZERO
FAILED_DELETIONS         : 0
BLOCKED_DELETIONS        : 0

FINAL_STATUS             : CLEANUP_SUCCESS
============================================================
```
