# 🏛️ E-ZZIO — RAPPORT DE CORRECTIONS CIBLÉES & VÉRIFICATIONS PHYSIQUES

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`

---

## 1. CORRECTION DU FALLBACK LOCAL (`core/cognition/model_router.py`)

L'ancienne référence stale `qwen2.5-coder:7b` a été formellement remplacée par `phi4-mini:latest` :
- **Modèle de Repli :** `LOCAL_FALLBACK_MODEL = "phi4-mini:latest"`
- **Routage Local Faible Complexité :** Bascule immédiate sur `phi4-mini:latest`
- **Profils Cloud Invariants :** Gemini Pool (`gemini-3.7-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`) strictement préservés.
- **Validation Live :** Test unitaire d'aiguillage exécuté avec succès (Gemini online, Local only, Outage fallback, Fail-closed).

---

## 2. RÉCONCILIATION DE `runtime/model_router/config.json`

La configuration d'atelier a été synchronisée avec les modèles physiques réels d'Ollama :
- **Routes réconciliées :**
  - `chat`, `presence`, `fast_reply`, `code` $ightarrow$ `phi4-mini:latest`
  - `general` $ightarrow$ `hermes3:8b`
  - `reasoning`, `analysis`, `planning`, `engineering`, `refactoring` $ightarrow$ `qwen3.5:9b`
  - `embeddings` $ightarrow$ `bge-m3:latest`
- **Catalogue :** Élimination des 3 références absentes (`granite4.1:8b`, `qwen3-coder:30b`, `mrasif/gpt-oss-20b-GGUF`) et enregistrement des 6 modèles installés.

---

## 3. VÉRIFICATION PHYSIQUE DES CAPACITÉS DOCUMENTAIRES

L'ingestion autonome de `core/perception/universal_reader.py` a été soumise à des tests physiques d'extraction sur des flux binaires réels :
- **PDF :** `PROVEN` (Détection de signature magique `%PDF` et extraction textuelle avec garde OCR).
- **DOCX :** `PROVEN` (Extraction XML directe via le conteneur ZIP natif sans Microsoft Office).
- **XLSX :** `PROVEN` (Parsing direct des feuilles de calcul XML sans Microsoft Excel).
- **CSV & HTML :** `PROVEN` (Dialect sniffer et détection d'encodage résiliente).
- **Archives ZIP :** `PROVEN` (Contrôle anti-Zip-Slip et anti-Zip-Bomb 60 Mo actif).

---

## 4. VÉRIFICATION PHYSIQUE DES CAPACITÉS VOCALES

- **TTS (Text-to-Speech) :** `RUNTIME_PROVEN`
  - Modèle ONNX : `G:/AI/external/capabilities/kokoro-tts/models/kokoro-v0_19.onnx` (325,5 Mo présent sur disque).
  - Voix : `voices.bin` (5,7 Mo présent sur disque).
  - Synthèse en temps réel : 175 148 octets WAV générés avec succès via `KokoroTTSAdapter`.
- **STT (Speech-to-Text) :** `PROVEN`
  - Double moteur streaming Nemotron + Faster-Whisper validé par `tests/test_audio_engine.py` (3/3 tests passés).

---

## 5. BILAN DES TESTS DE NON-RÉGRESSION

| SUITE DE TESTS CIBLÉS | TESTS EXÉCUTÉS | RÉSULTAT | TEMPS |
|---|:---:|:---:|:---:|
| `tests/test_universal_reader.py` | 8 | **PASS** | 5.2s |
| `tests/test_universal_ingestion_v10.py` | 7 | **PASS** | 4.8s |
| `tests/test_kokoro_tts_adapter.py` | 4 | **PASS** | 3.1s |
| `tests/test_voice_gateway.py` | 4 | **PASS** | 2.9s |
| `tests/test_audio_engine.py` | 3 | **PASS** | 11.1s |
| `tests/test_model_router_failure_matrix.py` | 4 | **PASS** | 3.4s |
| **TOTAL** | **30** | **100% SUCCÈS** | **30.5s** |
