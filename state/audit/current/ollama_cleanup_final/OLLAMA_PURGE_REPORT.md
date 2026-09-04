# 🧹 RAPPORT DE PURGE FINALE OLLAMA `ez-*`

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date d'exécution :** 31 Août 2026  
**Environnement :** AMD Ryzen 9 5900X / 32 Go DDR4-3200 / GTX 1650 4 Go (Inférence CPU pure)  
**Mode :** Opération de nettoyage autorisée avec vérification physique avant / après.

---

## 1. 🛑 PREFLIGHT & VÉRIFICATION DES CIBLES

Avant toute action de suppression, l'audit a vérifié :
* **Routes de production (`core/cognition/model_router.py`) :** 0 dépendance envers les 5 tags `ez-*`.
* **Providers actifs :** 0 dépendance (tous les flux conversationnels et cognitifs utilisent Gemini Cloud en primaire et Qwen2.5-Coder:7b / BGE-M3 en local).
* **Mode LOCAL_ONLY :** Route canonique vers `phi4-mini:latest` ou `qwen2.5-coder:7b`.
* **Tests de non-régression :** 100% indépendants des tags `ez-*`.

```text
DELETE_TARGETS_VERIFIED   : ez-router:latest, ez-core-safe:latest, ez-agent-hermes:latest, ez-core-free:latest, ez-rag-expert:latest
ACTIVE_RUNTIME_REFERENCES : 0
PARENT_DEPENDENCIES       : 0
UNIQUE_BLOBS              : ez-core-free (5.34 GB), ez-rag-expert (6.10 GB)
SHARED_BLOBS              : ez-router (2.32 GB), ez-core-safe (6.14 GB), ez-agent-hermes (4.34 GB)
```

---

## 2. 🗑️ JOURNAL D'EXÉCUTION DES SUPPRESSIONS

Les 5 commandes `ollama rm` ont été exécutées séparément avec vérification physique du code retour :

| Modèle Cible | Commande Exécutée | Code Retour | Statut |
| :--- | :--- | :---: | :---: |
| **`ez-router:latest`** | `ollama rm ez-router:latest` | `0` | **SUPPRIMÉ** |
| **`ez-core-safe:latest`** | `ollama rm ez-core-safe:latest` | `0` | **SUPPRIMÉ** |
| **`ez-agent-hermes:latest`** | `ollama rm ez-agent-hermes:latest` | `0` | **SUPPRIMÉ** |
| **`ez-core-free:latest`** | `ollama rm ez-core-free:latest` | `0` | **SUPPRIMÉ** |
| **`ez-rag-expert:latest`** | `ollama rm ez-rag-expert:latest` | `0` | **SUPPRIMÉ** |

---

## 3. 🔍 POST-CLEANUP & INVENTAIRE OLLAMA

Vérification physique immédiate via `ollama list` :
* **Modèles `ez-*` présents :** **0** (Disparition totale des 5 modèles).
* **Modèles canoniques de production intacts (5/5) :**
  1. `phi4-mini:latest` (2.5 GB)
  2. `qwen3.5:9b` (6.6 GB)
  3. `hermes3:8b` (4.7 GB)
  4. `bge-m3:latest` (1.2 GB)
  5. `nomic-embed-text:latest` (274 MB)

---

## 4. 💾 MESURE PHYSIQUE DU GAIN DE STOCKAGE (`G:\Ollama\Models`)

* **Stockage physique avant purge :** **25.5773 GB** (27 463 379 142 octets).
* **Stockage physique après purge :** **14.1371 GB** (15 179 557 331 octets).
* **Espace physique réellement récupéré :** **11.4402 GB** (12 283 821 811 octets).
* **Espace logique supprimé :** **24.24 GB** (26 032 888 664 octets).

*Explication de la divergence physique vs logique :*
* Les modèles `ez-router`, `ez-core-safe` et `ez-agent-hermes` partageaient 100% de leurs poids GGUF avec `phi4-mini`, `qwen3.5:9b` et `hermes3:8b` (0 B de blob libéré).
* Les modèles `ez-core-free` et `ez-rag-expert` possédaient des blobs orphelins exclusifs totalisant exactement **11.4402 GB**, entièrement libérés du disque dur physique.

---

## 5. 🧪 VALIDATION EN CONDITIONS RÉELLES DE PRODUCTION

Campagne de sondes réelles exécutées après la purge :

| Profil / Route | Moteur Résolu | Fournisseur | Statut | Latence E2E (ms) | Extrait Réponse |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **FAST** | `gemini-3.5-flash-lite` | `gemini_pool` | **SUCCESS** | 846.25 ms | "Salut BidiNani. J'y suis. Qu'est-ce qu'on lance ?" |
| **GENERAL** | `gemini-3.5-flash` | `gemini_pool` | **SUCCESS** | 9 378.60 ms | "La photosynthèse est le processus par lequel les végétaux..." |
| **CODING** | `gemini-3.7-flash` | `gemini_pool` | **SUCCESS** | 11 676.23 ms | "Voici la fonction factorielle en Python : def factorielle..." |
| **LOCAL_ONLY** | `phi4-mini:latest` | `ollama` | **SUCCESS** | 3 515.14 ms | "1 + 1 = 2" |
| **EMBEDDINGS** | `bge-m3:latest` | `ollama` | **SUCCESS** | 1 882.63 ms | Dim: 1024, Embedding vecteur généré |

---

## 6. 🔎 AUDIT DES RÉFÉRENCES RÉSIDUELLES HORS STATE/AUDIT

* **Références actives au runtime :** **0**
* **Documentation :** 4
* **Outils / Benchmarks de test :** 22
* **Prototypes LangGraph (`src/ezzio/config.py`) :** 7
* **Références mortes :** 84
* **Total résiduel répertorié :** 117 (toutes inactives).
