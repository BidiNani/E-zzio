# E-ZZIO V10.0 — COMFYUI REALITY & INTEGRATION MATRIX

---

## 1. VÉRIFICATION DU DÉPÔT ET CARACTÉRISTIQUES OFFICIELLES
- **Dépôt Officiel :** `https://github.com/comfyanonymous/ComfyUI`
- **Licence :** GPL-3.0
- **Support Windows :** Natif (Standalone Python bundle ou script d'amorçage `python main.py --listen 127.0.0.1 --port 8188 --headless --disable-auto-launch`)
- **API Headless :** Expose `POST /prompt` (chargement de graphes JSON) et `GET /history/{prompt_id}`
- **Réseau :** Localhost uniquement (`127.0.0.1:8188`), sans exposition WAN.

---

## 2. COMFYUI_INTEGRATION_MATRIX

| Moteur / Modèle | Intégration Officielle | Custom Node | Fonctionne Réellement | Statut dans E-ZzIO |
| :--- | :---: | :---: | :---: | :--- |
| **`LTX-Video / LTX-2`** | `ComfyUI-LTXVideo` (Lightricks) | Natif / Official Node | **OUI** (FP8/GGUF sur 4GB) | **P0 ADOPT (Primary Local Video)** |
| **`Wan2.1 / Wan-Animate`** | `ComfyUI-WanVideoWrapper` | Custom Node | **OUI** (1.3B GGUF sur 4GB, 14B sur Remote) | **P2 SANDBOX / CLOUD** |
| **`LivePortrait`** | `ComfyUI-LivePortrait` | Custom Node | **OUI** (Animation visage en 2GB VRAM) | **P1 HIGH VALUE** |
| **`Kokoro-82M`** | `ComfyUI-Kokoro` | Custom Node | **OUI** (Exécutable directement en Python CPU) | **P0 ADOPT (Local CPU)** |
