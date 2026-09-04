# E-ZZIO V9.0 — DEPENDENCY WEIGHT TRUTH

**Date de Mesure Réelle sur Disque** : 29 août 2026  
**Environnement** : Python 3.12.10 x64 (Windows 11)

---

## 1. POIDS PHYSIQUE RÉEL DANS `site-packages`

| Package Installé | Poids Disque Réel | Catégorie | Rôle Exact |
| :--- | :---: | :--- | :--- |
| **`torch`** | **446.46 MB** | Transitive ML | Dépendance transitive de bibliothèques d'analyse |
| **`_polars_runtime_32`** | **175.87 MB** | Dataframe Rust | Moteur de manipulation de données haute performance |
| **`lancedb`** | **141.92 MB** | Vector Engine | Moteur vectoriel optionnel |
| **`cv2` (OpenCV)** | **112.38 MB** | Vision Engine | Traitement matriciel d'images |
| **`googleapiclient`** | **97.86 MB** | Direct SaaS | Connecteur Google Workspace & Drive |
| **`scipy`** | **85.67 MB** | Scientific | Algorithmes numériques |
| **`pyarrow`** | **80.63 MB** | Columnar Data | Format tabulaire en mémoire |
| **`av.libs`** | **62.55 MB** | Multimédia C | Bindings FFmpeg pour manipulation audio/vidéo |
| **`chromadb_rust_bindings`**| **60.46 MB** | Vector Store | Bindings Rust natifs |
| **`ctranslate2`** | **59.35 MB** | Inference STT | Moteur d'inférence C++ de `faster-whisper` |
| **`litellm`** | **53.29 MB** | Bridge / Type | Schémas de modèles et adaptateur de repli |
| **`pymupdf`** | **44.63 MB** | PDF Engine | Extraction et lecture PDF dans `UniversalReader` |
| **`transformers`** | **42.45 MB** | NLP Models | Tokenizers et modèles de transformation |
| **`pydantic`** | **~15.00 MB** | Core Runtime | Validation des schémas de données |
| **`httpx`** | **~3.50 MB** | Core Runtime | Transport HTTP asynchrone universel |
| **`fastapi` / `uvicorn`** | **~5.00 MB** | Core Runtime | Serveur HTTP ASGI |

---

## 2. SYNTHÈSE DES PLUS GROS COMPOSANTS
- **Plus gros package direct du Core Runtime** : `pydantic` (~15 MB) et `httpx` (~3.5 MB).
- **Plus gros package direct de Capacités SaaS** : `googleapiclient` (97.86 MB) et `litellm` (53.29 MB).
- **Plus grosse pile transitive globale** : `torch` (446.46 MB) et `_polars_runtime_32` (175.87 MB).
