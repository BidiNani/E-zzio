# E-ZZIO 10/10 FORENSIC BASELINE
## ÉTAT INITIAL COMPLET, DIAGNOSTIC FORENSIQUE ET PLAN D'ACTION VERS L'EXCELLENCE
### STANDARD : FAIL-CLOSED / ZERO REGRESSION V9.4 / PRESERVATION ABSOLUE DU CORE

---

## 1. ARCHITECTURE RÉELLE ET STRATIGRAPHIE DU SYSTÈME

E-ZzIO est un système d'exploitation cognitif souverain et gouverné, structuré en strates historiques successives :

* **Strate Canonique Active (V9.4 Living AI Office)** :
  * Point d'entrée serveur : `web_server.py` (FastAPI / Uvicorn sur port 8001).
  * Moteur de visualisation 2.5D : `runtime/web/ezzio-office-canvas.js` & `ezzio-office-motion.js` (A* pathfinding, walk cycles, orientation 4 directions, multi-agent crowding avoidance).
  * Coeur de gouvernance et sécurité : `core/capabilities/capability_policy.py`, `core/capabilities/registry.py`, `core/security/audit_ledger.py` (*Frozen Core scellé*).
  * Arbitrage humain (HITL) : `core/governance/approval/` & dialogue d'interception modale sans fuite de secret.
* **Strate Moteur d'Exécution & Outils (Tools & CLI)** :
  * `tools/` contient 145 scripts d'audit, de benchmark et de qualification.
  * Graphe sémantique structural : `tools/semantic_model/structural_graph/` (415 MB de modèles d'arborescence JSON).
* **Strate Cognitive & Mémoire (RAG / Vector Store)** :
  * ChromaDB persistant : `data/chroma_db/` (259 MB).
  * SQLite WAL & FTS5 : `runtime/evidence/evidence.db` et base unifiée de contexte.
* **Strates Historiques & Archivées (V1 à V7 / V17 à V21)** :
  * Présence de `legacy_archive/`, de snapshots zip (`state/baselines/`), de 302 fichiers de tests (dont 18 dans `_quarantine_dead_imports`).
  * Le système a conservé ses artefacts de transition sans dégradation fonctionnelle.

---

## 2. TOP 100 FICHIERS DU SYSTÈME DE FICHIERS PAR TAILLE (HORS .GIT)

| Rang | Chemin Relatif | Taille (MB) | Statut Proposé | Criticité | Usage Réel / Rôle |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | `dist\releases\E-ZZIO-V9.4-GOLDEN-SOURCE.zip` | 291.51 MB | `CERTIFIED` | CRITICAL | Golden Source V9.4 inviolable (Règle 1) |
| 2 | `tools\semantic_model\structural_graph\PHASE2_STRUCTURAL_STATE.json` | 211.84 MB | `REBUILDABLE` | LOW | Graphe sémantique structural généré lors des audits |
| 3 | `tools\semantic_model\structural_graph\PHASE2_STRUCTURAL_MODEL.json` | 203.73 MB | `REBUILDABLE` | LOW | Graphe sémantique structural généré lors des audits |
| 4 | `.venv\Lib\site-packages\_polars_runtime_32\_polars_runtime.pyd` | 178.78 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 5 | `data\chroma_db\chroma.sqlite3` | 133.79 MB | `ACTIVE` | HIGH | Index vectoriel persistant ChromaDB |
| 6 | `data\chroma_db\3e042f8d-2f5e-4472-a495-fe028c2ae7a4\data_level0.bin` | 125.25 MB | `ACTIVE` | HIGH | Index vectoriel persistant ChromaDB |
| 7 | `.venv\Lib\site-packages\cv2\cv2.pyd` | 81.87 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 8 | `runtime\models\whisper\models--Systran--faster-whisper-tiny\snapshots\d90ca5fe260221311c53c58e660288d3deb8d356\model.bin` | 72.04 MB | `ACTIVE` | HIGH | Poids de modèles audio/locaux embarqués |
| 9 | `.venv\Lib\site-packages\cv2\opencv_videoio_ffmpeg500_64.dll` | 29.45 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 10 | `.venv\Lib\site-packages\numpy.libs\libscipy_openblas64_-327b2e0bcffce2882e0dc04cdeb4eaa6.dll` | 19.55 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 11 | `dist\android\E-ZzIO-Android-Source-v9.0.1.zip` | 18.92 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 12 | `dist\android\E-ZzIO-Android-Source-v9.1.zip` | 18.92 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 13 | `state\baselines\v4_0_0_20260810_204914\ezzio_v4.0.0_snapshot.zip` | 12.81 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 14 | `.venv\Lib\site-packages\litellm\rust_bridge\_native.pyd` | 10.69 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 15 | `.venv\Lib\site-packages\granian\_granian.cp312-win_amd64.pyd` | 10.51 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 16 | `.venv\Lib\site-packages\cryptography\hazmat\bindings\_rust.pyd` | 9.48 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 17 | `.venv\Lib\site-packages\hf_xet\hf_xet.pyd` | 9.06 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 18 | `data\codebase_catalog.json` | 8.15 MB | `REFERENCE` | MEDIUM | Index sémantique de contexte et catalogue codebase |
| 19 | `.venv\Lib\site-packages\PIL\_avif.cp312-win_amd64.pyd` | 7.53 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 20 | `.venv\Lib\site-packages\tokenizers\tokenizers.pyd` | 7.21 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 21 | `EZZIO_CONTEXT.md` | 7.12 MB | `REFERENCE` | MEDIUM | Index sémantique de contexte et catalogue codebase |
| 22 | `.venv\Lib\site-packages\pydantic_core\_pydantic_core.cp312-win_amd64.pyd` | 5.01 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 23 | `runtime\evidence\evidence.db` | 4.33 MB | `ACTIVE` | HIGH | Base SQLite d'audit ledger et evidence |
| 24 | `dist\android\E-ZzIO-v9.0.1.apk` | 4.20 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 25 | `dist\android\E-ZzIO-v9.1-release.apk` | 4.20 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 26 | `dist\android\E-ZZIO-v9.4-release.apk` | 4.20 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 27 | `.venv\Lib\site-packages\lxml\etree.cp312-win_amd64.pyd` | 3.85 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 28 | `.venv\Lib\site-packages\numpy\_core\_multiarray_umath.cp312-win_amd64.pyd` | 3.67 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 29 | `android\.gradle\8.5\executionHistory\executionHistory.bin` | 3.66 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 30 | `.venv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\fb374d419588a4632f3f557e76b4b70aebbca790` | 3.64 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 31 | `state\audit\current\mapping\physical_inventory.json` | 3.36 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 32 | `runtime\cognitive\index\memory_index.sqlite` | 3.02 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 33 | `runtime\cognitive\snapshots\V7.58\memory_index.sqlite` | 3.02 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 34 | `state\cleanup\preflight\filesystem_inventory.json` | 2.96 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 35 | `runtime\web\tailwind.min.css` | 2.80 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 36 | `data\chroma_db\3e042f8d-2f5e-4472-a495-fe028c2ae7a4\index_metadata.pickle` | 2.72 MB | `ACTIVE` | HIGH | Index vectoriel persistant ChromaDB |
| 37 | `.venv\Lib\site-packages\PyWin32.chm` | 2.52 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 38 | `.venv\Lib\site-packages\PIL\_imaging.cp312-win_amd64.pyd` | 2.51 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 39 | `state\audit\visual\v9.4\baseline\E-ZZIO-V9.4-AI-OFFICE-DEMO.mp4` | 2.39 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 40 | `state\audit\visual\v9.4\final\E-ZZIO-V9.4-AI-OFFICE-DEMO.mp4` | 2.39 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 41 | `.venv\Lib\site-packages\tiktoken\_tiktoken.cp312-win_amd64.pyd` | 2.34 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 42 | `.venv\Lib\site-packages\_soundfile_data\libsndfile_x64.dll` | 2.25 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 43 | `runtime\models\whisper\models--Systran--faster-whisper-tiny\snapshots\d90ca5fe260221311c53c58e660288d3deb8d356\tokenizer.json` | 2.10 MB | `ACTIVE` | HIGH | Poids de modèles audio/locaux embarqués |
| 44 | `.venv\Lib\site-packages\PIL\_imagingft.cp312-win_amd64.pyd` | 2.07 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 45 | `.venv\Lib\site-packages\litellm\model_prices_and_context_window_backup.json` | 1.71 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 46 | `.venv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\anthropic_tokenizer.json` | 1.69 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 47 | `.venv\Lib\site-packages\lxml\objectify.cp312-win_amd64.pyd` | 1.66 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 48 | `runtime\cognition\budget\unified_decision_ledger.jsonl` | 1.63 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 49 | `.venv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\9b5ad71b2ce5302211f9c61530b329a4922fc6a4` | 1.60 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 50 | `.venv\Lib\site-packages\pythonwin\scintilla.dll` | 1.43 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 51 | `.venv\Lib\site-packages\litellm\proxy\swagger\swagger-ui-bundle.js` | 1.42 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 52 | `state\quarantine\quarantine_20260829_222000\runtime\memory\sqlite\cognitive_store.db` | 1.38 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 53 | `state\quarantine\quarantine_20260829_222000\data\action_registry.db` | 1.34 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 54 | `.venv\Lib\site-packages\litellm\llms\huggingface\huggingface_llms_metadata\hf_text_generation_models.txt` | 1.26 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 55 | `.venv\Lib\site-packages\botocore\data\endpoints.json` | 1.19 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 56 | `state\audit\optimization\performance_v21\raw_results.jsonl` | 1.15 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 57 | `.venv\Lib\site-packages\pythonwin\win32ui.pyd` | 0.98 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 58 | `state\audit\golden\v9.1\golden_file_manifest.json` | 0.96 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 59 | `.venv\Lib\site-packages\litellm\proxy\_lazy_openapi_snapshot.json` | 0.95 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 60 | `forge\outputs\image_hd\EZZIO_HD_1920x1080_20260610_011554.png` | 0.95 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 61 | `forge\outputs\image_hd\EZZIO_HD_1920x1080_20260610_011625.png` | 0.95 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 62 | `runtime\cognition\budget\cognitive_budget_ledger.jsonl` | 0.92 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 63 | `runtime\ecol\evolution_ledger\evolution_audit_2026-08-23.jsonl` | 0.90 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 64 | `.venv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\ec7223a39ce59f226a68acc30dc1af2788490e15` | 0.85 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 65 | `.venv\Lib\site-packages\google\genai\types.py` | 0.84 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 66 | `.venv\Lib\site-packages\numpy\_core\_simd.cp312-win_amd64.pyd` | 0.79 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 67 | `state\audit\visual\v9.4-counter-certification\E-ZZIO-V9.4-VISUAL-COUNTER-CERTIFICATION.mp4` | 0.79 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 68 | `projects\arpg_mobile_prototype\.godot\shader_cache\SceneShaderGLES3\536fe8d8085998f3b68daa8343b573088cd1a8b5be6d78321c33a6f56a584769\6bb7c9a2fd1c4a8fa77cb96555b9b4a720209981.cache` | 0.76 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 69 | `dist\releases\E-ZZIO-V9.4-GOLDEN-MANIFEST.json` | 0.74 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 70 | `state\audit\optimization\performance_v19\performance_matrix.csv` | 0.73 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 71 | `dist\releases\E-ZZIO-V9.3-GOLDEN-MANIFEST.json` | 0.72 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 72 | `.venv\Lib\site-packages\litellm\proxy\proxy_server.py` | 0.71 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 73 | `projects\arpg_mobile_prototype\.godot\shader_cache\SceneShaderGLES3\536fe8d8085998f3b68daa8343b573088cd1a8b5be6d78321c33a6f56a584769\a38af2d0725c8e99d8492f4c72736f24d6a54cc5.cache` | 0.70 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 74 | `projects\arpg_mobile_prototype\.godot\shader_cache\SceneShaderGLES3\536fe8d8085998f3b68daa8343b573088cd1a8b5be6d78321c33a6f56a584769\cafb1506f2db0c3681435e264aa18e216d1a7a40.cache` | 0.70 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 75 | `.venv\Lib\site-packages\regex\_regex.cp312-win_amd64.pyd` | 0.69 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 76 | `.venv\Lib\site-packages\pywin32_system32\pythoncom312.dll` | 0.66 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 77 | `.venv\Lib\site-packages\litellm\proxy\_experimental\out\_next\static\chunks\1dg0y22lcfxz2.js` | 0.65 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 78 | `.venv\Lib\site-packages\huggingface_hub\hf_api.py` | 0.65 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 79 | `.venv\Lib\site-packages\litellm-1.98.0.dist-info\RECORD` | 0.64 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 80 | `.venv\Lib\site-packages\litellm\proxy\_experimental\out\_next\static\chunks\1y596evc77z8d.js` | 0.60 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 81 | `data\models\registry.json.tmp_20260825_205622` | 0.59 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 82 | `.venv\Lib\site-packages\numpy\random\_generator.cp312-win_amd64.pyd` | 0.56 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 83 | `.venv\Lib\site-packages\numpy.libs\msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll` | 0.55 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 84 | `.venv\Lib\site-packages\litellm\router.py` | 0.54 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 85 | `.venv\Lib\site-packages\rpds\rpds.cp312-win_amd64.pyd` | 0.53 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 86 | `.venv\Lib\site-packages\win32comext\shell\shell.pyd` | 0.52 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 87 | `state\audit\optimization\performance_v19\quality_matrix.csv` | 0.51 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 88 | `runtime\dependency_graph.json` | 0.50 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 89 | `.venv\Lib\site-packages\reportlab\fonts\DarkGarden.sfd` | 0.50 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 90 | `.venv\Lib\site-packages\botocore\data\ec2\2016-11-15\service-2.json.gz` | 0.49 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 91 | `.venv\Lib\site-packages\polars\dataframe\frame.py` | 0.49 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 92 | `state\audit\current\mapping\content_summary.json` | 0.49 MB | `UNKNOWN` | MEDIUM | À investiguer avant toute décision |
| 93 | `.venv\Lib\site-packages\litellm\llms\custom_httpx\llm_http_handler.py` | 0.48 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 94 | `.venv\Lib\site-packages\litellm\proxy\_experimental\out\_next\static\chunks\0cefehsj9nby1.css` | 0.48 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 95 | `.venv\Lib\site-packages\numpy\random\mtrand.cp312-win_amd64.pyd` | 0.47 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 96 | `.venv\Lib\site-packages\polars\expr\expr.py` | 0.45 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 97 | `runtime\models\whisper\models--Systran--faster-whisper-tiny\snapshots\d90ca5fe260221311c53c58e660288d3deb8d356\vocabulary.txt` | 0.44 MB | `ACTIVE` | HIGH | Poids de modèles audio/locaux embarqués |
| 98 | `.venv\Lib\site-packages\numpy\_core\tests\test_multiarray.py` | 0.43 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 99 | `.venv\Lib\site-packages\jiter\jiter.cp312-win_amd64.pyd` | 0.43 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |
| 100 | `.venv\Lib\site-packages\discord\bin\libopus-0.x64.dll` | 0.42 MB | `ACTIVE` | HIGH | Binaire C/Rust/DLL de l'environnement virtuel Python |

---

## 3. TOP 100 OBJETS GIT PAR TAILLE (ANALYSE FORENSIQUE DE L'HISTORIQUE)

| Rang | Hash OID (10 hex) | Taille (MB) | Chemin Détecté dans Git | Caractère | Action Proposée |
| :--- | :--- | :---: | :--- | :---: | :--- |
| 1 | `310f168315` | 992.13 MB | `models/gemma-4-E4B-it-Q4_K_M.gguf` | Modèle binaire lourd dans l'historique | CONSERVER (Gel Git - Aucune réécriture non validée) |
| 2 | `389f60bbb8` | 310.45 MB | `runtime/realtime/models/kokoro/current/kokoro-v0_19.onnx` | Modèle binaire lourd dans l'historique | CONSERVER (Gel Git - Aucune réécriture non validée) |
| 3 | `e276a62fb2` | 291.51 MB | `dist/releases/E-ZZIO-V9.4-GOLDEN-SOURCE.zip` | Release zip scellée | CONSERVER (Archives officielles de release) |
| 4 | `58f9118d4c` | 290.98 MB | `dist/releases/E-ZZIO-V9.3-GOLDEN-SOURCE.zip` | Release zip scellée | CONSERVER (Archives officielles de release) |
| 5 | `dc4854c1ce` | 287.34 MB | `dist/releases/E-ZZIO-V9.2-GOLDEN-SOURCE.zip` | Release zip scellée | CONSERVER (Archives officielles de release) |
| 6 | `8ca8e034df` | 287.34 MB | `dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip` | Release zip scellée | CONSERVER (Archives officielles de release) |
| 7 | `0dfd4b33c0` | 207.45 MB | `tools/semantic_model/structural_graph/PHASE2_STRUCTURAL_STATE.json` | Dump sémantique JSON | CONSERVER (Historique immuable) |
| 8 | `d567a65c86` | 199.34 MB | `tools/semantic_model/structural_graph/PHASE2_STRUCTURAL_MODEL.json` | Dump sémantique JSON | CONSERVER (Historique immuable) |
| 9 | `e384aee6a0` | 154.34 MB | `runtime/audit/storage_migration/active_code_paths/ACTIVE_CODE_PATHS_20260814_155219.json` | Objet d'historique Git | CONSERVER |
| 10 | `69196b469b` | 146.28 MB | `runtime/audit/full_reuse/EZZIO_FULL_REUSE_v13_20260809_164021.json` | Objet d'historique Git | CONSERVER |
| 11 | `0f904841e0` | 128.53 MB | `runtime/audit/full_reuse/EZZIO_FULL_REUSE_FILES_v13_20260809_164021.csv` | Objet d'historique Git | CONSERVER |
| 12 | `55c4a81b55` | 116.38 MB | `runtime/audit/storage_migration/active_code_paths/ACTIVE_CODE_PATHS_20260814_155219.csv` | Objet d'historique Git | CONSERVER |
| 13 | `9010b9de5b` | 85.04 MB | `runtime/audit/storage_migration/hard_path_reference/HARD_PATH_REFERENCE_20260814_154921.json` | Objet d'historique Git | CONSERVER |
| 14 | `5f49575ab8` | 62.73 MB | `runtime/audit/storage_migration/hard_path_reference/HARD_PATH_REFERENCE_20260814_154921.csv` | Objet d'historique Git | CONSERVER |
| 15 | `55c9ba57ce` | 60.27 MB | `runtime/realtime/audio/voices/fr_FR-siwis-medium.onnx` | Modèle binaire lourd dans l'historique | CONSERVER (Gel Git - Aucune réécriture non validée) |
| 16 | `20d7480206` | 51.26 MB | `runtime/audit/storage_migration/active_python_dependency/ACTIVE_PYTHON_DEPENDENCY_20260814_154837.json` | Objet d'historique Git | CONSERVER |
| 17 | `90f3beb973` | 32.10 MB | `runtime/audit/storage_migration/active_python_dependency/ACTIVE_PYTHON_DEPENDENCY_20260814_154837.csv` | Objet d'historique Git | CONSERVER |
| 18 | `0789f4ed1d` | 28.54 MB | `runtime/audit/reliability/dependency_graph.json` | Objet d'historique Git | CONSERVER |
| 19 | `e7aacd3902` | 18.92 MB | `dist/android/E-ZzIO-Android-Source-v9.0.1.zip` | Objet d'historique Git | CONSERVER |
| 20 | `d27fe7c991` | 18.05 MB | `runtime/audit/full_reuse/EZZIO_FULL_REUSE_v13_20260809_164021.txt` | Objet d'historique Git | CONSERVER |
| 21 | `cacb944e13` | 12.81 MB | `state/baselines/v4_0_0_20260810_204914/ezzio_v4.0.0_snapshot.zip` | Objet d'historique Git | CONSERVER |
| 22 | `919fbe73ae` | 11.09 MB | `runtime/audit/storage_migration/consumer_certification/MODEL_REGISTRY_AUTHORITY_FLOW_V4_20260814_160754.json` | Objet d'historique Git | CONSERVER |
| 23 | `fd9273de0a` | 10.34 MB | `runtime/audit/storage_migration/parallel_forensic/FORENSIC_MAPPING_20260814_154221.json` | Objet d'historique Git | CONSERVER |
| 24 | `7bd74ebd8d` | 9.79 MB | `runtime/realtime/audio/piper/libtashkeel_model.ort` | Objet d'historique Git | CONSERVER |
| 25 | `2807f68e38` | 8.84 MB | `runtime/realtime/audio/piper/onnxruntime.dll` | Modèle binaire lourd dans l'historique | CONSERVER (Gel Git - Aucune réécriture non validée) |
| 26 | `ac39ad91b9` | 8.14 MB | `runtime/realtime/audio/piper/espeak-ng-data/ru_dict` | Objet d'historique Git | CONSERVER |
| 27 | `c1be645c32` | 7.82 MB | `runtime/audit/storage_migration/hard_path_reference/high_triage/HIGH_TRIAGE_20260814_155100.json` | Objet d'historique Git | CONSERVER |
| 28 | `7823f04be1` | 6.70 MB | `runtime/audit/storage_migration/contract_boundary/MODEL_REGISTRY_METHOD_USAGE_RESOLUTION_V47_2_20260814_175000.json` | Objet d'historique Git | CONSERVER |
| 29 | `59dec79cf6` | 5.75 MB | `runtime/audit/storage_migration/hard_path_reference/high_triage/HIGH_TRIAGE_20260814_155100.csv` | Objet d'historique Git | CONSERVER |
| 30 | `e813f220d7` | 5.49 MB | `runtime/realtime/models/kokoro/current/voices.bin` | Objet d'historique Git | CONSERVER |
| 31 | `4f5de600f8` | 4.69 MB | `reports/g_drive_cleaner_20260610_172550/safe_delete_candidates.json` | Objet d'historique Git | CONSERVER |
| 32 | `42deac5ada` | 4.20 MB | `runtime/audit/storage_migration/consumer_certification/MODEL_REGISTRY_ACTIVE_CONSUMERS_V13_20260814_161555.json` | Objet d'historique Git | CONSERVER |
| 33 | `676823afcc` | 4.20 MB | `dist/android/E-ZZIO-v9.4-release.apk` | Objet d'historique Git | CONSERVER |
| 34 | `40e6a6374b` | 4.14 MB | `runtime/audit/intelligence_scan/dependency_graph_forensic.json` | Objet d'historique Git | CONSERVER |
| 35 | `9b18f999ec` | 4.14 MB | `runtime/temp/EZZIO_GUARDIAN/Report_Large_20260805_121740.txt` | Objet d'historique Git | CONSERVER |
| 36 | `05197db78c` | 4.10 MB | `runtime/temp/EZZIO_GUARDIAN/CleanLarge_20260805_121740.log` | Objet d'historique Git | CONSERVER |
| 37 | `9d7d63b8c4` | 4.08 MB | `runtime/audit/storage_migration/c_reference_classifier/C_REFERENCE_CLASSIFICATION_20260814_154621.json` | Objet d'historique Git | CONSERVER |
| 38 | `94b7620cb1` | 3.96 MB | `runtime/temp/EZZIO_GUARDIAN/Candidates_Large_20260805_121740.txt` | Objet d'historique Git | CONSERVER |
| 39 | `f55e8968b7` | 3.74 MB | `reports/g_drive_cleaner_20260610_172550/actions.jsonl` | Objet d'historique Git | CONSERVER |
| 40 | `ef4f4d107f` | 3.67 MB | `runtime/audit/core_module_boundary/V48_1/EXCLUDED_FORENSIC_INVENTORY_20260814_192703.json` | Objet d'historique Git | CONSERVER |
| 41 | `cb93c92a1f` | 3.63 MB | `runtime/audit/reliability/broken_references.json` | Objet d'historique Git | CONSERVER |
| 42 | `17b8e4c393` | 3.25 MB | `state/audit/current/mapping/physical_inventory.json` | Objet d'historique Git | CONSERVER |
| 43 | `576b6bdb7c` | 2.94 MB | `runtime/audit/storage_migration/c_reference_classifier/C_REFERENCE_CLASSIFICATION_20260814_154621.csv` | Objet d'historique Git | CONSERVER |
| 44 | `cb8a0cf3dd` | 2.93 MB | `quarantine/g_drive_cleaner_20260610_174857/AI/E-zzio/ezzio-ui/node_modules/.vite/deps_ssr/svelte_compiler.js.map` | Objet d'historique Git | CONSERVER |
| 45 | `61019e1722` | 2.72 MB | `runtime/audit/storage_migration/c_reference_classifier/C_REFERENCE_CLASSIFICATION_20260814_154621.txt` | Objet d'historique Git | CONSERVER |
| 46 | `82dbded1a2` | 2.71 MB | `runtime/audit/storage_migration/parallel_forensic/FORENSIC_MAPPING_20260814_154221.txt` | Objet d'historique Git | CONSERVER |
| 47 | `ba74a2c97a` | 2.62 MB | `runtime/test_isolation/v453/sandbox_integration_c/events_endurance.pending` | Objet d'historique Git | CONSERVER |
| 48 | `d0a730e1ef` | 2.53 MB | `runtime/audit/system/mutation_event_graph.json` | Objet d'historique Git | CONSERVER |
| 49 | `b2a7fe218c` | 2.39 MB | `state/audit/visual/v9.4/baseline/E-ZZIO-V9.4-AI-OFFICE-DEMO.mp4` | Objet d'historique Git | CONSERVER |
| 50 | `80c5592ef1` | 2.22 MB | `runtime/realtime/models/silero_vad.onnx` | Modèle binaire lourd dans l'historique | CONSERVER (Gel Git - Aucune réécriture non validée) |
| 51 | `466534d93a` | 2.21 MB | `dump_complet.txt` | Objet d'historique Git | CONSERVER |
| 52 | `272030a9fb` | 1.80 MB | `runtime/audit/core_module_boundary/MODULE_CANDIDATES_20260814_191914.json` | Objet d'historique Git | CONSERVER |
| 53 | `c045277c7f` | 1.78 MB | `runtime/audit/storage_migration/consumer_certification/MODEL_REGISTRY_WRITE_AUTHORITY_TRACE_V22_20260814_165430.json` | Objet d'historique Git | CONSERVER |
| 54 | `bcad20e8f3` | 1.57 MB | `quarantine/g_drive_cleaner_20260610_174857/AI/E-zzio/ezzio-ui/node_modules/.vite/deps_ssr/svelte_compiler.js` | Objet d'historique Git | CONSERVER |
| 55 | `f284cabe1d` | 1.49 MB | `runtime/realtime/audio/piper/espeak-ng-data/cmn_dict` | Objet d'historique Git | CONSERVER |
| 56 | `da39d8c35a` | 1.42 MB | `runtime/audit/storage_migration/baseline/ACTIVE_FILES_BASELINE_20260814_160013.json` | Objet d'historique Git | CONSERVER |
| 57 | `f0738da864` | 1.32 MB | `runtime/audit/storage_migration/consumer_certification/MODEL_REGISTRY_WRITE_AUTHORITY_V18_20260814_162207.json` | Objet d'historique Git | CONSERVER |
| 58 | `e1a79f2b31` | 1.23 MB | `runtime/test_isolation/v453/sandbox_integration_c_async/events_endurance_async.pending` | Objet d'historique Git | CONSERVER |
| 59 | `6a0c99384a` | 1.20 MB | `runtime/audit/intelligence_scan/inventory_forensic.json` | Objet d'historique Git | CONSERVER |
| 60 | `0055664798` | 1.17 MB | `audit/filesystem.json` | Objet d'historique Git | CONSERVER |
| 61 | `154ac50a92` | 1.16 MB | `runtime/memory/sqlite/cognitive_store.db` | Objet d'historique Git | CONSERVER |
| 62 | `fe0512cc4f` | 1.16 MB | `runtime/audit/system/full_cognitive_inventory.json` | Objet d'historique Git | CONSERVER |
| 63 | `82402234dd` | 1.04 MB | `runtime/audit/storage_migration/consumer_certification/MODEL_REGISTRY_RUNTIME_CALLGRAPH_FORENSIC_V45_20260814_173849.json` | Objet d'historique Git | CONSERVER |
| 64 | `a97f40a4c1` | 1.02 MB | `runtime/audit/intelligence_scan/V7_REGISTRY/live_transaction_append.logl` | Objet d'historique Git | CONSERVER |
| 65 | `b25f5621c9` | 1.00 MB | `runtime/memory/sqlite/cognitive_store.db` | Objet d'historique Git | CONSERVER |
| 66 | `bb8c2e0ef3` | 0.98 MB | `runtime/test_isolation/v453/sandbox_ryzen_drill/events_ryzen_drill.pending` | Objet d'historique Git | CONSERVER |
| 67 | `ca5d70b6ba` | 0.95 MB | `forge/outputs/image_hd/EZZIO_HD_1920x1080_20260610_011554.png` | Objet d'historique Git | CONSERVER |
| 68 | `ba4aa3befb` | 0.93 MB | `state/audit/golden/v9.1/golden_file_manifest.json` | Objet d'historique Git | CONSERVER |
| 69 | `602203e275` | 0.91 MB | `runtime/audit/core_module_boundary/DEPENDENCY_GRAPH_20260814_191914.json` | Objet d'historique Git | CONSERVER |
| 70 | `96fdbadd91` | 0.82 MB | `runtime/audit/core_module_boundary/V48_3_1/IMPORT_GRAPH_20260814_201705.json` | Objet d'historique Git | CONSERVER |
| 71 | `4e571890ab` | 0.72 MB | `dist/releases/E-ZZIO-V9.4-GOLDEN-MANIFEST.json` | Objet d'historique Git | CONSERVER |
| 72 | `146db1403b` | 0.72 MB | `dist/releases/E-ZZIO-V9.3-GOLDEN-MANIFEST.json` | Objet d'historique Git | CONSERVER |
| 73 | `619077ee5d` | 0.72 MB | `reports/g_drive_cleaner_20260610_174857/actions.jsonl` | Objet d'historique Git | CONSERVER |
| 74 | `aff1577a99` | 0.70 MB | `runtime/audit/core_module_boundary/V48_3_2/IMPORT_GRAPH_20260814_202658.json` | Objet d'historique Git | CONSERVER |
| 75 | `c5ba28955f` | 0.69 MB | `runtime/audit/intelligence_scan/V7_REGISTRY/cleanup_transaction_log.json` | Objet d'historique Git | CONSERVER |
| 76 | `4c881f7123` | 0.69 MB | `runtime/audit/intelligence_scan/V7_REGISTRY/cleanup_approval_manifest.json` | Objet d'historique Git | CONSERVER |
| 77 | `d0aee674c0` | 0.66 MB | `runtime/realtime/audio/piper/espeak-ng-data/lb_dict` | Objet d'historique Git | CONSERVER |
| 78 | `8df0a31bbb` | 0.63 MB | `runtime/audit/core_module_boundary/V48_3_1/UNRESOLVED_IMPORTS_20260814_201705.json` | Objet d'historique Git | CONSERVER |
| 79 | `79d3cf29c7` | 0.62 MB | `runtime/audit/system/rpg_memory_qualification.json` | Objet d'historique Git | CONSERVER |
| 80 | `ed9cf0761c` | 0.54 MB | `runtime/realtime/audio/piper/espeak-ng-data/yue_dict` | Objet d'historique Git | CONSERVER |
| 81 | `5b3c94a570` | 0.52 MB | `runtime/realtime/audio/piper/espeak-ng-data/phondata` | Objet d'historique Git | CONSERVER |
| 82 | `7d350f5386` | 0.52 MB | `runtime/audit/intelligence_scan/V7_REGISTRY/quarantine_discovery_report.json` | Objet d'historique Git | CONSERVER |
| 83 | `710007027d` | 0.52 MB | `runtime/audit/core_module_boundary/V48_2/AST_RESULTS_20260814_192907.json` | Objet d'historique Git | CONSERVER |
| 84 | `44826fc0b9` | 0.52 MB | `runtime/audit/core_module_boundary/V48_3_1/AST_RESULTS_20260814_201705.json` | Objet d'historique Git | CONSERVER |
| 85 | `bff5e4f690` | 0.50 MB | `runtime/audit/intelligence_scan/REAL_EXECUTION_MATRIX_V7.json` | Objet d'historique Git | CONSERVER |
| 86 | `bc27bcc355` | 0.49 MB | `runtime/dependency_graph.json` | Objet d'historique Git | CONSERVER |
| 87 | `47d908d9ca` | 0.49 MB | `runtime/realtime/audio/piper/piper.exe` | Objet d'historique Git | CONSERVER |
| 88 | `b2b0277203` | 0.47 MB | `runtime/audit/intelligence_scan/V7_REGISTRY/cleanup_validation_result.json` | Objet d'historique Git | CONSERVER |
| 89 | `900b4743e6` | 0.47 MB | `state/audit/current/mapping/content_summary.json` | Objet d'historique Git | CONSERVER |
| 90 | `244a88527f` | 0.47 MB | `reports/g_drive_cleaner_20260610_174722/safe_candidates.json` | Objet d'historique Git | CONSERVER |
| 91 | `512acad38f` | 0.47 MB | `reports/g_drive_cleaner_20260610_174857/safe_candidates.json` | Objet d'historique Git | CONSERVER |
| 92 | `b7667a1418` | 0.47 MB | `runtime/audit/core_module_boundary/V48_2/IMPORT_GRAPH_20260814_192907.json` | Objet d'historique Git | CONSERVER |
| 93 | `36958edb05` | 0.47 MB | `runtime/audit/core_module_boundary/CORE_CANDIDATES_20260814_191914.json` | Objet d'historique Git | CONSERVER |
| 94 | `8fa32b2bd2` | 0.46 MB | `reports/g_drive_cleaner_20260610_174722/actions.jsonl` | Objet d'historique Git | CONSERVER |
| 95 | `108ff2becb` | 0.46 MB | `runtime/realtime/audio/piper/espeak-ng-data/ar_dict` | Objet d'historique Git | CONSERVER |
| 96 | `f064da87b3` | 0.40 MB | `state/baselines/v4_0_0_20260810_204914/runtime_manifest_sha256.json` | Objet d'historique Git | CONSERVER |
| 97 | `76d847c8e2` | 0.39 MB | `runtime/audit/tool_calls.jsonl` | Objet d'historique Git | CONSERVER |
| 98 | `f6fcc5c8df` | 0.39 MB | `runtime/audit/tool_calls.jsonl` | Objet d'historique Git | CONSERVER |
| 99 | `467554a737` | 0.39 MB | `state/audit/current/mapping/dependency_graph.json` | Objet d'historique Git | CONSERVER |
| 100 | `eceaf31b1a` | 0.39 MB | `runtime/realtime/audio/piper/piper_phonemize.dll` | Objet d'historique Git | CONSERVER |

---

## 4. AUDIT DES DÉPENDANCES ET ENVIRONNEMENT

* **Dépendances déclarées dans `pyproject.toml`** :
  * Runtime : `fastapi`, `uvicorn`, `pydantic`, `aiosqlite`, `python-dotenv`, `httpx`, `requests`, `psutil`, `ollama`.
  * Dev : `pytest`, `pytest-asyncio`, `ruff`.
* **État de `.venv` (298 paquets installés, ~595 MB)** :
  * Présence de dépendances accumulées : `polars` (178 MB), `opencv-python` (111 MB), `azure-*`, `boto3`, `crewai`, `chromadb`, `faster-whisper`.
  * *Constat d'audit* : L'environnement est complet et auto-suffisant pour tous les benchmarks et qualifications. Aucune suppression n'est requise pour le moment ; le runtime canonique n'importe que les dépendances nécessaires au démarrage.

---

## 5. AUDIT DE L'ARCHITECTURE ET CODE DU SYSTÈME

* **Modules Canoniques** :
  * `core/` (384 fichiers) : Coeur d'E-ZzIO. Comprend `capabilities/`, `security/`, `governance/`, `cognition/`, `memory/`, `identity/`.
  * `routers/` (40 fichiers) : Endpoints de la passerelle FastAPI.
  * `runtime/web/` : Interface Web tactique V9.4 Living Office (100% offline self-contained, Canvas 2.5D, CSS tactique sans CDN).
* **Modules Doublons / Code Mort Potentiel** :
  * Coexistence de `src/ezzio/` (25 fichiers) et de `core/` : `src/` correspond à une ancienne structure modulaire type package pip, alors que `core/` est l'architecture centrale active importée par 881 fichiers.
  * Présence de `legacy_archive/` (3.9 MB) contenant des résidus de versions antérieures (v17, v18, v19).
  * `tests/_quarantine_dead_imports/` : 18 fichiers de tests mis en quarantaine pour imports obsolètes.
  * Présence de 145 scripts dans `tools/` et 12 scripts Python à la racine, dont des audits ponctuels de version (`gate_v6_45_*.py`).

---

## 6. REGISTRE INITIAL DE DETTE TECHNIQUE (TECHNICAL DEBT REGISTER)

| ID | Fichier / Composant | Problème Constaté | Impact | Risque | Priorité | Solution Recommandée | Statut |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| `DEBT-01` | `.git` (2.52 GB) | Modèles binaires (GGUF 992MB, ONNX 310MB) historisés dans 68 tags | Stockage élevé | P0 si mal manipulé | `P2` | Audit forensique complet sans réécriture Git pour cette phase | `OPEN` |
| `DEBT-02` | `tools/semantic_model/` | Fichiers JSON géants (415 MB) dans l'espace de travail | Stockage local | Faible | `P3` | Compression ou archivage hors chemin actif si non requis | `OPEN` |
| `DEBT-03` | `tests/` | 18 tests en quarantaine (`_quarantine_dead_imports`) | Lisibilité des tests | Faible | `P2` | Analyser si adaptables ou à archiver formellement | `OPEN` |
| `DEBT-04` | Racine `G:/AI/E-zzio/` | 125 fichiers à la racine (scripts `.ps1`, `.json`, `.py`) | Clarté architecturale | Faible | `P2` | Regrouper les outils dans `tools/` et la documentation dans `docs/` | `OPEN` |
| `DEBT-05` | `src/ezzio` vs `core/` | Dualité d'arborescence entre `src/ezzio` et `core/` | Risque de confusion d'import | Moyen | `P1` | Vérifier les imports actifs et unifier sur `core/` | `OPEN` |
| `DEBT-06` | Dépendances non figées | Absence de `requirements-frozen.txt` déterministe | Reproductibilité | Moyen | `P1` | Générer un lockfile déterministe certifié | `OPEN` |

---

## 7. ÉLÉMENTS PROTÉGÉS (À CONSERVER ABSOLUMENT)

* **Frozen Core inviolable (3/3 SHA-256 certifiés à 100%)** :
  * `core/capabilities/capability_policy.py`
  * `core/capabilities/registry.py`
  * `core/security/audit_ledger.py`
* **Archives officielles de release** :
  * `dist/releases/E-ZZIO-V9.4-GOLDEN-SOURCE.zip`
  * Preuves et artefacts de certification : `state/audit/visual/v9.4-counter-certification/` (11 fichiers scellés).
* **Fichiers Identity Forge** :
  * `E-ZZIO — IDENTITY FORGE QUESTIONNAI.txt` et toutes ses occurrences dans l'arborescence.

---

## 8. ÉVALUATION INITIALE SUR LES 17 AXES DE QUALITÉ (SCORES 10/10)

| Axe d'Excellence | Score Initial | Faiblesses & Risques Identifiés | Actions Prioritaires pour Atteindre l'Excellence | Score Cible |
| :--- | :---: | :--- | :--- | :---: |
| **ARCHITECTURE** | 7.5 / 10 | Coexistence `src/` et `core/`, fichiers de scripts dispersés à la racine | Consolider sur une arborescence canonique claire, documentée | 10 / 10 |
| **ROBUSTESSE** | 9.0 / 10 | Serveur résistant aux crashs, fail-safe antigravity fonctionnel | Blindage des timeouts et gestion de coupure mémoire | 10 / 10 |
| **SÉCURITÉ** | 9.5 / 10 | Frozen core parfait, Default Deny, zero secret leak en modal HITL | Audit complet de tous les subprocess et lecture filesystem | 10 / 10 |
| **CERTIFICATION** | 9.5 / 10 | Contre-certification V9.4 validée (16/16 pytest, 11 artefacts scellés) | Formalisation du Quality Gate 10/10 complet et automatisé | 10 / 10 |
| **FORENSIC / OBSERVABILITÉ** | 9.0 / 10 | Audit Ledger SHA-256 fonctionnel, événements structurés | Traces unifiées Who/What/When/Why sur toutes les routes | 10 / 10 |
| **TESTABILITÉ** | 8.0 / 10 | 302 fichiers de tests mais certains orphelins ou en quarantaine | Pyramide de tests clarifiée (Unit, Contract, Runtime, Evidence) | 10 / 10 |
| **MAINTENABILITÉ** | 7.0 / 10 | Nombreux fichiers historiques et scripts de gate v6.45 résiduels | Registre de dette technique et nettoyage sûr sans casse | 10 / 10 |
| **SIMPLICITÉ** | 7.0 / 10 | Complexité résiduelle accumulée au fil des versions | Élimination de la complexité accidentelle hors chemins certifiés | 10 / 10 |
| **PERFORMANCE** | 8.5 / 10 | Moteur 2.5D fluide, 8 workers Uvicorn rapides, latences providers affichées | Réduction du temps de démarrage et lazy-loading des gros modules | 10 / 10 |
| **GESTION DÉPENDANCES** | 7.0 / 10 | 298 paquets dans .venv, pas de lockfile certifié | Création d'un `requirements-frozen.txt` déterministe | 10 / 10 |
| **GESTION STOCKAGE** | 6.5 / 10 | Repo de 4.3 GB (dont .git 2.5 GB et JSON structural 415 MB) | Identification forensique des blobs et isolation du reconstructible | 9.5 / 10 (*) |
| **DOCUMENTATION** | 8.0 / 10 | Specs V9.4 riches mais dispersées sur plusieurs versions | Création d'ARCHITECTURE.md, OPERATIONS.md, SECURITY.md unifiés | 10 / 10 |
| **UX / UI** | 9.5 / 10 | Living AI Office 2.5D certifié, responsive Android & Desktop | Confort d'inspection et raccourcis clavier enrichis | 10 / 10 |
| **OFFLINE SELF-CONTAINED** | 10 / 10 | 100% self-contained, zéro CDN, assets locaux servis par FastAPI | Maintien absolu de cette propriété inviolable | 10 / 10 |
| **RÉSILIENCE** | 9.0 / 10 | Démarrage garanti même si backends IA hors-ligne | Tests de chaos et de déconnexion réseau | 10 / 10 |
| **DÉTERMINISME** | 9.0 / 10 | Déplacement A* déterministe, seed et routing déterministes | Élimination de toute dérive de date/aléatoire non contrôlée | 10 / 10 |
| **EXTENSIBILITÉ** | 9.0 / 10 | Système de plugins de capacités et passerelle MCP Hermes | Contrats d'interface standardisés pour nouveaux providers | 10 / 10 |

*Note sur le stockage : Le score 10/10 absolu en stockage nécessiterait une réécriture de l'historique Git (purge des blobs GGUF/ONNX scellés dans 68 tags), ce qui est formellement interdit dans cette phase pour préserver l'intégrité forensique totale. Le score 9.5/10 est le maximum sain réalisable.*

---

## 9. PLAN D'ACTION PRIORISÉ VERS LE 10/10

1. **Phase 1 (Audit Baseline)** : *Terminée avec le présent rapport.*
2. **Phase 2 (Cartographie & Lockfile)** : Figer formellement les dépendances canoniques et cartographier les interfaces `core/` vs `src/`.
3. **Phase 3 (Nettoyage Non-Destructif)** : Isoler les scripts historiques résiduels (`gate_v6_45_*`) dans un répertoire dédié `tools/archive_gates/` sans altérer Git.
4. **Phase 4 (Durcissement Sécurité & Déterminisme)** : Vérifier que toutes les capacités respectent le Default Deny et ajouter les tests de non-déterminisme.
5. **Phase 5 (Consolidation de la Documentation)** : Rédiger la suite documentaire canonique (`ARCHITECTURE.md`, `OPERATIONS.md`, `SECURITY.md`, `TECHNICAL_DEBT_REGISTER.md`).
6. **Phase 6 (Quality Gate 10/10 Automatisé)** : Exécuter la suite complète de vérification finale.