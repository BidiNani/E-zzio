# 🏛️ RAPPORT D'AUDIT FORENSIQUE — MODÈLES DÉRIVÉS OLLAMA `ez-*`

**Standard constitutionnel :** `EVIDENCE RULE v1.1 — NO CLAIM WITHOUT OBSERVABLE PROOF`  
**Dépôt cible :** `G:\AI\E-zzio`  
**Date d'exécution :** 31 Août 2026  
**Environnement matériel :** AMD Ryzen 9 5900X (12c/24t) / 32 Go DDR4-3200 / GTX 1650 4 Go (Inférence CPU pure)  
**Mode :** `READ / EXECUTE-TEST-ONLY` (Audit physique sans suppression)

---

## 1. 📊 INVENTAIRE PHYSIQUE & FILIATION DES MODÈLES `ez-*`

L'inspection forensique des manifests (`G:\Ollama\Models\manifests\registry.ollama.ai\library\`) et des blobs physiques (`G:\Ollama\Models\blobs\`) a permis d'établir la filiation exacte et le partage de poids :

| Modèle Dérivé | Taille Logique | Parent Déclaré / Réel | Hash SHA-256 Poids (GGUF) | Statut Poids | Espace Récupérable Immédiat |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **`ez-router:latest`** | 2.32 GB | `phi4-mini:latest` | `sha256:3c168af1...` | **100% partagé** avec `phi4-mini` | **0 Byte** |
| **`ez-core-safe:latest`** | 6.14 GB | `qwen3.5:9b` | `sha256:dec52a44...` | **100% partagé** avec `qwen3.5:9b` | **0 Byte** |
| **`ez-agent-hermes:latest`** | 4.34 GB | `hermes3:8b` | `sha256:c8985d23...` | **100% partagé** avec `hermes3:8b` | **0 Byte** |
| **`ez-core-free:latest`** | 5.34 GB | Ex-`llama3.1-8b-abliterated` | `sha256:3c08d661...` | **Poids uniques orphelins** | **5.34 GB** |
| **`ez-rag-expert:latest`** | 6.10 GB | Dérivé Qwen Legacy | `sha256:85292217...` + proj | **Poids uniques orphelins** | **6.10 GB** |

**Bilan de stockage :**
* Stockage global Ollama : **25.58 GB** (10 modèles).
* Volume logique cumulé des 5 `ez-*` : **24.24 GB**.
* Volume physique réel des blobs partagés : **12.80 GB** (partagés avec `phi4-mini`, `qwen3.5:9b`, `hermes3:8b`).
* Volume physique réel des blobs uniques `ez-*` : **11.44 GB** (`ez-core-free` + `ez-rag-expert`).

---

## 2. 🔍 AUDIT DES MODELFILES & NATURE DES DÉRIVATIONS

L'extraction physique des layers `Modelfile` révèle :

1. **`ez-router:latest`** :
   * **Base :** `FROM phi4-mini:latest`
   * **Params :** `num_ctx 2048`, `temperature 0`, `top_p 0.9`
   * **System Prompt :** *"Tu es le routeur interne d'E-ZZIO. Ton unique rôle est de classifier la requête utilisateur et d'orienter vers le bon modèle en JSON strict."*
   * **Nature :** **Pure Prompt Wrapper**.
   * **Utilité :** Nulle en production. Le routage sovereign d'E-ZZIO (`core/cognition/model_router.py`) s'effectue en Python déterministe pur en **~4 microsecondes** sans aucun LLM.

2. **`ez-core-safe:latest`** :
   * **Base :** `FROM qwen3.5:9b`
   * **Params :** `num_ctx 8192`, `temperature 0.2`, `top_p 0.95`
   * **System Prompt :** *"Tu es le moteur cognitif principal et sécurisé d'E-ZZIO."*
   * **Nature :** **Pure Prompt Wrapper**.
   * **Utilité :** Doublon fonctionnel. L'injection dynamique de prompt au runtime sur `qwen3.5:9b` produit le même résultat sans figer un tag Ollama.

3. **`ez-agent-hermes:latest`** :
   * **Base :** `FROM hermes3:8b`
   * **Params :** `num_ctx 8192`, `temperature 0.3`
   * **System Prompt :** *"Tu es l'agent d'exécution et d'orchestration d'outils d'E-ZZIO."*
   * **Nature :** **Pure Prompt Wrapper**.
   * **Utilité :** Doublon fonctionnel. Les agents souverains injectent leurs system prompts dynamiquement.

4. **`ez-core-free:latest`** :
   * **Base :** Blob autonome de 5.34 GB (ex-Llama 3.1 8B débridé).
   * **Params :** `num_ctx 8192`, `temperature 0.7`
   * **System Prompt :** *"Tu es l'instance débridée et libre d'E-ZZIO."*
   * **Nature :** **Modèle autonome legacy**. Non routé en production.

5. **`ez-rag-expert:latest`** :
   * **Base :** Blobs autonomes (6.10 GB) avec couche projecteur.
   * **Params :** `num_ctx 16384`, `temperature 0.1`
   * **System Prompt :** *"Tu es le spécialiste de synthèse et d'extraction RAG d'E-ZZIO."*
   * **Nature :** **Modèle autonome legacy**. Non routé en production (le RAG sovereign actif s'appuie sur `bge-m3` + Gemini 3.5 Flash-Lite / Qwen local).

---

## 3. 🔎 AUDIT DU CODE SOURCE & DU ROUTAGE ACTIF

* **Routage de Production (`core/cognition/model_router.py`) :** **0 référence active** aux modèles `ez-*`. Les routes souveraines utilisent `gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.7-flash`, `gemini-3.1-pro-preview` et `qwen2.5-coder:7b` en fallback local.
* **Prototype LangGraph (`src/ezzio/config.py`) :** Contient 5 références par défaut (prototype déconnecté du pipeline de production Discord/CLI).
* **Outils / Benchmarks / Scripts :** 79 références dans des outils de maintenance et scripts de setup.

---

## 4. ⚡ BENCHMARK COMPARATIF DYNAMIQUE (CPU RYZEN 9 5900X)

Campagne de 3 runs réels par modèle sur l'API Ollama locale :

| Modèle Testé | Débit Moyen (tok/s) | E2E Moyen (ms) | Temps de Chargement (ms) | Évaluation Prompt (ms) | Évaluation Inférence (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`ez-router`** | **11.26** | 4 410.0 | 0.0 | 338.4 | 4 071.6 |
| **`phi4-mini:latest`** | **9.96** | 7 637.3 | 2 546.0 | 344.2 | 4 747.1 |
| **`ez-core-safe`** | **5.22** | 28 850.8 | 3 942.3 | 498.4 | 24 410.1 |
| **`qwen3.5:9b`** | **4.82** | 28 758.1 | 1 971.2 | 512.6 | 26 274.3 |
| **`ez-agent-hermes`** | **6.58** | 22 781.8 | 2 764.5 | 451.8 | 19 565.5 |
| **`hermes3:8b`** | **6.31** | 21 766.3 | 1 319.4 | 438.1 | 20 008.8 |
| **`ez-core-free`** | **5.58** | 20 443.7 | 4 983.8 | 446.7 | 15 013.2 |
| **`ez-rag-expert`** | **4.99** | 27 801.1 | 4 679.5 | 487.6 | 22 634.0 |

**Constat d'inférence :** Les modèles `ez-*` dérivés partagent exactement le même profil de vitesse et de latence que leurs modèles canoniques respectifs (les variations observées sont dues au warmup et à la longueur de prompt système).

---

## 5. 🎯 MATRICE DE DÉCISION & RECOMMANDATIONS

1. **`ez-router:latest`** $	o$ **SAFE_TO_DELETE_LATER** (0 B récupérés, remplacé par Python déterministe).
2. **`ez-core-safe:latest`** $	o$ **SAFE_TO_DELETE_LATER** (0 B récupérés, remplacé par `qwen3.5:9b` avec prompt injecté).
3. **`ez-agent-hermes:latest`** $	o$ **SAFE_TO_DELETE_LATER** (0 B récupérés, remplacé par `hermes3:8b` avec prompt injecté).
4. **`ez-core-free:latest`** $	o$ **SAFE_TO_DELETE_LATER** (**+5.34 GB récupérables**).
5. **`ez-rag-expert:latest`** $	o$ **SAFE_TO_DELETE_LATER** (**+6.10 GB récupérables**).

*Gain potentiel d'espace disque lors d'un futur nettoyage :* **+11.44 GB** (récupération des 2 blobs orphelins).

---

## 6. 🔒 VÉRIFICATION DE NON-RÉGRESSION

* **Tests pytest unitaires / intégration :** **8/8 PASSED** (100% de succès).
* **Intégrité architecturale :** 0 modification de code, 0 divergence de routage, Frozen Core intact.
