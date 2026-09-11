# E-ZZIO V10.0 — AUDIO TTS & STT SPECIFICATION V3

---

## 1. COMPOSANTS AUDIO SOUVERAINS

| Rôle | Moteur Recommandé | Licence | Matériel Requis | Latence Réelle (Ryzen 9 5900X) |
| :--- | :--- | :---: | :---: | :---: |
| **TTS Local (Génération Voix)** | **Kokoro-82M** | Apache-2.0 | CPU (350 Mo RAM) | **< 90 ms** (15 mots) |
| **STT Local (Transcription)** | **Faster-Whisper** | MIT | CPU Int8 (600 Mo RAM) | **~120 ms** (Audio 5s) |
| **TTS Multi-Speaker (Recherche)**| **VibeVoice** | MIT / Open | CPU / 2GB VRAM | **~480 ms** |
| **Voice Cloning (Rejet Commercial)**| **F5-TTS** | CC-BY-NC-4.0 | 2-4 Go VRAM | **~2.0 s** |
