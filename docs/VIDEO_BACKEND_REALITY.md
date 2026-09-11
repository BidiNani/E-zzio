# E-ZZIO V10.0 — VIDEO BACKEND REALITY & HARDWARE FIT

---

## 1. VÉRITÉ SUR LTX-VIDEO / LTX-2.X SUR GTX 1650 (4 GB VRAM)
- **Quantification Requise** : FP8 ou GGUF Q4_K.
- **Utilisation VRAM Mesurée / Documentée** : **~3.6 à 3.8 Go VRAM** (avec sequential CPU offload vers les 32 Go de RAM système).
- **Vitesse Réelle** : ~30 à 50 secondes pour un clip de 5 secondes en 480p/720p (24 fps).
- **Classification Matérielle** : **`LOCAL_REAL`** (sur GTX 1650 avec ComfyUI GGUF).

---

## 2. VÉRITÉ SUR WAN 2.1 / WAN-ANIMATE-2
- **Wan 14B / Wan 2.2 MoE** : Exige 16 à 24 Go de VRAM. Sur 4 Go VRAM, l'offload CPU est trop lent (>10 minutes/clip).
- **Wan 1.3B Lite** : Fonctionne en GGUF (~2-4 minutes/clip).
- **Classification Matérielle** : **`SANDBOX / REMOTE / FUTURE GPU`**.
