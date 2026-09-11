# E-ZZIO — CLAIM ↔ EVIDENCE MATCH MATRIX (v5.0 Master Reality & Parallelism Sweep)

**Date :** 30 août 2026  
**Standard :** `EVIDENCE RULE v1.1`

---

| Composant / Capacité | Affirmation Audité | Preuve Réelle Observée | Niveau de Preuve | Référence du Fichier de Preuve | Classification Finale |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Mémoire Souveraine (FTS5)** | "Mémoire autoritaire SQLite WAL avec indexation FTS5" | Write 3.7ms, Search FTS5 3.08ms, Read 1.14ms, Persistance après reboot vérifiée | RUNTIME_VERIFIED | `state/audit/optimization/memory_probe_evidence.json` | **PROVEN (SQLite FTS5)** |
| **ChromaDB Vectorstore** | "ChromaDB utilisé comme backend mémoire actif" | Package installé (1.5.9), mais 0 appel dans UnifiedMemoryGateway ou CognitiveGateway | INSTALLED / DORMANT | `state/audit/optimization/memory_probe_evidence.json` | **INSTALLED_BUT_DORMANT** |
| **Kokoro-82M TTS** | "Synthèse vocale neuronale principale active sur CPU" | VoiceGateway génère un WAV 24kHz via Kokoro ONNX (Sweet spot 12 threads = 2633ms / RTF 0.4879) | RUNTIME_VERIFIED | `state/audit/optimization/kokoro_runtime_evidence.json` | **PROVEN (TTS Principal)** |
| **Piper TTS (Fr-Siwis)** | "Synthèse vocale ultra-légère alternative qualifiée en sandbox" | Modèle 63Mo installé, inférence 452ms (RTF 0.0741, 13.5x temps réel sur CPU Ryzen) | EXECUTED / QUALIFIED | `state/audit/optimization/piper_qualification_evidence.json` | **PROVEN (TTS Léger Qualifié)** |
| **E-ZzIO Procedural TTS** | "Générateur procédural interne comme fallback souverain" | Moteur déterministe PCM/WAV interne actif en secours dans `core/voice/voice_gateway.py` (0.06ms) | RUNTIME_VERIFIED | `outputs/kokoro_runtime_fallback.wav` | **PROVEN (Fallback)** |
| **Ollama LLM (phi4-mini)** | "Routeur cognitif local 3.8B CPU-only" | Modèle 3.8B Q4_K_M mesuré à 12.44 tok/s à 4 threads (Sweet spot single-CCD) | EXECUTED | `state/audit/optimization/cpu_parallelism_evidence.json` | **PROVEN (Best Router CPU)** |
| **Ollama LLM (qwen3.5:9b)** | "Cœur d'inférence sécurisé local 9.7B CPU-only" | Modèle 9.7B Q4_K_M mesuré à 5.71 tok/s à 4 threads sur Ryzen 9 5900X | EXECUTED | `state/audit/optimization/cpu_parallelism_evidence.json` | **PROVEN (Best Core Safe CPU)** |
| **ZIP Ingestion Sécurisée** | "Plafonnement explicite à 25 entrées et rejet à 60 Mo" | Rejet bomb 65Mo validé, Cap 35->25 avec `truncated: true` et anti-slip validés | RUNTIME_VERIFIED | `state/audit/forensic/zip_boundary_evidence.json` | **PROVEN** |
