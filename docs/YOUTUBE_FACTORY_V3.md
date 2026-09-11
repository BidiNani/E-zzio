# E-ZZIO V10.0 — YOUTUBE MEDIA FACTORY V3

---

## 1. PIPELINE DE TRAITEMENT UNIFIÉ

```text
YouTube URL
    ↓
yt-dlp (Extraction métadonnées + recherche sous-titres)
    ↓
Sous-titres natifs disponibles ?
    ├── OUI ➔ Extraction directe (0% STT, 0 GPU) ➔ Économie totale
    └── NON ➔ Extraction audio ➔ Faster-Whisper (Int8 CPU)
    ↓
CognitiveGateway (Gemini / Ollama)
    ↓ Synthèse, Script, Traduction
Générateurs Spécialisés :
    ├── Voix & Doublage : Kokoro-82M (CPU <90ms)
    ├── Vignettes & Images : Pillow (Local) / Gemini Image (Cloud)
    └── B-Roll & Vidéo : LTX-Video (ComfyUI Headless)
```
