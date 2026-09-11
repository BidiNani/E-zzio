# E-ZZIO — REGISTRE DES AFFIRMATIONS HISTORIQUES RÉFUTÉES OU CORRIGÉES (KNOWN FALSE CLAIMS)

**Date d'entrée en vigueur :** 30 août 2026  
**Standard :** `EVIDENCE RULE v1.1`

---

## 1. Chatterbox-Nano
- **CLAIM :** "Chatterbox-Nano intégré en local comme moteur TTS souverain (format GGUF, 110M params, watermarking PerTh)."
- **ORIGINAL_SOURCE :** Rapport exploratoire v6.0.
- **OBSERVATION :** 0 commit Git, 0 fichier source dans le dépôt, 0 dépendance. Concept théorique jamais implémenté.
- **CORRECT_STATUS :** `FALSE`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `git log --all --grep="chatterbox"` (0 résultat).

---

## 2. VibeVoice
- **CLAIM :** "VibeVoice moteur TTS haute fidélité intégré."
- **ORIGINAL_SOURCE :** Catalogue préliminaire d'outils.
- **OBSERVATION :** 0 fichier source, 0 référence active dans `core/voice/`.
- **CORRECT_STATUS :** `FALSE`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** Recherche exhaustive sur le disque (0 résultat).

---

## 3. Évolution Historique de Kokoro-82M TTS
- **HISTORIQUE DES ÉTATS :**
  1. *Rapport v6.0 / v1.0 :* Déclaré `RUNTIME_VERIFIED` alors que seuls les manifests descriptifs existaient -> Rétrogradé en `SOURCE_VERIFIED (Catalogue) / UNVERIFIED (Moteur)`.
  2. *Mission d'installation :* Package `kokoro-onnx 0.6.1` et poids `kokoro-v0_19.onnx` (325 Mo) installés et exécutés en sandbox -> Promu en `EXECUTED / TEST_VERIFIED`.
  3. *Mission d'activation runtime :* Intégré dans `VoiceGateway` comme moteur principal avec repli automatique `ezzio-procedural-tts` -> Validé en cycle complet (Nominal, Panne, Restauration) -> Promu en `RUNTIME_VERIFIED`.
- **CORRECT_STATUS :** `RUNTIME_VERIFIED (Moteur principal avec repli fail-safe testé)`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `state/audit/optimization/kokoro_runtime_evidence.json` et `outputs/kokoro_runtime_nominal.wav`.

---

## 4. LTX-Video / ComfyUI "OPERATIONAL"
- **CLAIM :** "VIDEO : OPERATIONAL (LTX-Video FP8 via ComfyUI)."
- **ORIGINAL_SOURCE :** Rapport Master Sovereign Agent Evolution v6.0.
- **OBSERVATION :** GPU hôte GTX 1650 (4 Go VRAM) insuffisant pour exécuter LTX-Video FP8 (exige > 12 Go VRAM). Dossier présent sur disque, mais ComfyUI headless non exécuté en live.
- **CORRECT_STATUS :** `INSTALLED (Dossier) / UNSUPPORTED_HARDWARE_LIMIT`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `nvidia-smi` (4096 MiB VRAM) et `G:\AI\external\ComfyUI\`.

---

## 5. Limites Sécurité ZIP-Bomb : "100 MB / 500 fichiers"
- **CLAIM :** "Protection anti-zip-bomb : plafond à 100 Mo décompressés et 500 fichiers."
- **ORIGINAL_SOURCE :** Rapport d'ingestion v2.1.
- **OBSERVATION :** Le code actif dans `core/perception/universal_reader.py:26-27` applique `MAX_ARCHIVE_FILES = 25` et `MAX_ARCHIVE_UNCOMPRESSED_BYTES = 60 * 1024 * 1024` (60 Mo).
- **CORRECT_STATUS :** `SUPERSEDED` (Remplacé par la valeur réelle du code : 60 Mo / 25 fichiers, validée en test de rejet live `ZIP_BOMB_DETECTED`).
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `core/perception/universal_reader.py:26-27` et `state/audit/forensic/zip_boundary_evidence.json`.

---

## 6. Limite ZIP Fichiers : "REJECTED"
- **CLAIM :** "Archive avec plus de 25 fichiers rejetée."
- **ORIGINAL_SOURCE :** Synthèse d'audit v1.0.
- **OBSERVATION :** Le code applique un plafonnement explicite du manifeste (`truncated: true` à 25 entrées avec `ok=True`), sans lever d'erreur ni rejeter l'archive.
- **CORRECT_STATUS :** `SUPERSEDED (Sémantique réelle = CAP explicite à 25 entrées avec signal truncated=true)`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `core/perception/universal_reader.py:532-570` et `state/audit/forensic/zip_boundary_evidence.json (case_c)`.

---

## 7. Affirmations de "100% Parity Antigravity / Codex"
- **CLAIM :** "100% Antigravity Parity / 100% Codex Parity".
- **ORIGINAL_SOURCE :** Rapports antérieurs v6.0.
- **OBSERVATION :** Formulation superlative non mesurée. E-ZzIO dispose d'équivalents fonctionnels robustes (Loop d'agent, Subagents, MCP, Skills, Patch Engine, Sandbox) mais conserve une architecture différente et des limites spécifiques.
- **CORRECT_STATUS :** `CORRECTED` (Remplacé par matrices de parité disjointes et mesurées).
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `docs/ANTIGRAVITY_PARITY_MATRIX.md` et `docs/CODEX_PARITY_MATRIX.md`.

---

## 8. Statut Initial de Gemma 4 E4B, Qwen3.5-9B MTP et Ministral 3
- **CLAIM :** "Gemma 4 E4B, Qwen3.5-9B MTP et Ministral 3 sont inexistants ou rejetés sans test physique."
- **ORIGINAL_SOURCE :** Synthèse d'optimisation v1.0.
- **OBSERVATION :** Une recherche exhaustive sur l'API Hugging Face a identifié les dépôts officiels/quantifiés `unsloth/Ministral-3-3B-Instruct-2512-GGUF` (2.14 Go, SHA-256: `fd46fc37...`), `unsloth/gemma-4-E4B-it-GGUF` (4.97 Go, SHA-256: `85a896a0...`) et `unsloth/Qwen3.5-9B-MTP-GGUF` (5.86 Go, SHA-256: `e8dd9481...`). Les fichiers ont été physiquement téléchargés dans `G:\AI\external\models\`, vérifiés et benchmarkés en CPU-only sur le Ryzen 9 5900X.
- **CORRECT_STATUS :** `SUPERSEDED (Modèles localisés, installés, hachés et benchmarkés en sandbox CPU)`
- **DATE :** 30 août 2026
- **EVIDENCE_PATH :** `state/audit/optimization/full_model_installation_evidence.json` et `state/audit/optimization/full_model_benchmark_evidence.json`.
