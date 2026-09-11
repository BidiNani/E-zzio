# E-ZZIO V10.0 — YOUTUBE MEDIA FACTORY PIPELINE

---

## 1. FLUX D'EXÉCUTION UNIFIÉ

```text
YouTube URL
    ↓
yt-dlp (Extraction locale métadonnées + sous-titres)
    ↓
Vérification des sous-titres natifs ?
    ├── OUI ➔ Extraction directe (0% STT, 0 GPU) ➔ Économie totale
    └── NON ➔ Extraction audio ➔ Faster-Whisper (STT Int8 CPU)
    ↓
CognitiveGateway (Gemini / Ollama)
    ↓ Synthèse, Script, Traduction
Générateurs Spécialisés :
    ├── Voix & Doublage : Kokoro-82M / VibeVoice
    ├── Vignettes & Images : Pillow / Gemini Image
    └── B-Roll & Vidéo : LTX-Video (ComfyUI Headless)
```
