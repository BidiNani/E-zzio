# E-ZZIO V10.0 — COMFYUI INTEGRATION & ISOLATION V3

---

## 1. DÉFINITION ET PROTOCOLE
- **Emplacement :** `G:\AI\external\ComfyUI\` (Environnement Python indépendant).
- **Protocole :** API REST locale `POST http://127.0.0.1:8188/prompt` et WebSocket `/ws`.
- **Rôle :** Moteur d'exécution externe pour les modèles de diffusion lourds (LTX-Video, Wan2.1 GGUF, LivePortrait).
- **Zéro intrusion :** Aucune modification de `pyproject.toml` ou de `G:\AI\E-zzio\.venv`.
