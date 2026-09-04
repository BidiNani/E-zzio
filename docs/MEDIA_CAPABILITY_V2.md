# E-ZZIO V10.0 — UNIFIED MEDIA CAPABILITY ARCHITECTURE V2

---

## 1. ARCHITECTURE DES CAPACITÉS MULTIMÉDIAS

```text
                      E-ZZIO RUNTIME
                            │
                     GenerationRouter
                     (/generators/*)
                            │
                     MediaCapability
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
        IMAGE             VIDEO             AUDIO
          │                 │                 │
       Pillow           LTX-Video         Kokoro-82M
       Gemini          (ComfyUI API)    Faster-Whisper
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                     ComfyUI Headless
                     (127.0.0.1:8188)
                 G:\AI\external\ComfyUI\
```
