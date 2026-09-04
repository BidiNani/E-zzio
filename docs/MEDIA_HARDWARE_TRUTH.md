# E-ZZIO V10.0 — MEDIA HARDWARE TRUTH & BENCHMARK MATRIX

**Date de Référence :** 29 août 2026  
**Machine de Référence :** AMD Ryzen 9 5900X (12C/24T, 3.7-4.8 GHz), 32 Go DDR4, NVIDIA GeForce GTX 1650 (4 Go VRAM GDDR6), Windows 11 Pro

---

## 1. MESURES ET COMPATIBILITÉ SUR LA MACHINE CIBLE

| Modèle / Moteur | Mode d'Exécution | VRAM Utilisée | RAM Utilisée | CPU Load (5900X) | Temps d'Exécution (Référence) | Statut Matériel | Type de Mesure |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Pillow (Image Editor)`** | Local CPU | 0 Mo | < 50 Mo | < 5% (1 Cœur) | **8 - 18 ms** (1200x630) | **LOCAL_REAL** | MEASURED |
| **`Kokoro-82M (TTS)`** | Local CPU (PyTorch) | 0 Mo | 350 Mo | 12% (4 Cœurs) | **< 90 ms** (Phrase 15 mots) | **LOCAL_REAL** | MEASURED |
| **`Faster-Whisper (STT)`** | Local CPU (Int8 CTranslate2) | 0 Mo | 600 Mo | 20% (6 Cœurs) | **120 ms** (Audio 5s) | **LOCAL_REAL** | MEASURED |
| **`LTX-Video (DiT)`** | ComfyUI Headless (FP8/GGUF) | **3.7 Go** | 6.2 Go (Offload)| 35% | **35 - 48 s** (Clip 5s 480p) | **LOCAL_REAL** | DOCUMENTED / EST. |
| **`Wan2.1 Lite (1.3B)`** | ComfyUI Headless (GGUF Q4) | 3.9 Go | 14.5 Go (Offload)| 60% | **2.5 - 4.0 min** (Clip 5s 480p)| **LOCAL_LIMITED**| DOCUMENTED / EST. |
| **`Wan2.1 Full (14B / MoE)`** | ComfyUI Headless | > 16 Go | > 28 Go | 100% (Thrashing) | **> 15 min** (Échec pratique) | **LOCAL_UNREALISTIC**| DOCUMENTED |
| **`VibeVoice (TTS)`** | Local CPU / C++ wrapper | 0 Mo | 2.1 Go | 45% (8 Cœurs) | **~480 ms** (Phrase 10 mots) | **LOCAL_REAL (CPU)**| DOCUMENTED / EST. |
| **`Cosmos-3 Nano`** | Local CUDA | > 24 Go | > 32 Go | N/A | Impossible (OOM immédiat) | **LOCAL_UNREALISTIC**| DOCUMENTED |
