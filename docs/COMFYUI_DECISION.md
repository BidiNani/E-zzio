# E-ZZIO V10.0 — COMFYUI ARCHITECTURAL DECISION

**Date de Référence** : 29 août 2026

---

## 1. LA QUESTION CRITIQUE : COMFYUI EST-IL UN GAIN NET ?

### Comparaison Directe :

| Axe d'Évaluation | Sans ComfyUI (Wrappers Python Locaux) | Avec ComfyUI Headless (`G:\AI\external\ComfyUI\`) |
| :--- | :--- | :--- |
| **Pollution Environnement E-ZzIO** | **CATASTROPHIQUE** (+40 Go de PyTorch, CUDA, Diffusers dans `.venv`) | **NULLE** (0 Mo ajouté à l'environnement E-ZzIO) |
| **Gestion VRAM 4 Go & Offload** | Manuelle, complexe, instable | **AUTOMATISÉE** (Génération GGUF/FP8 avec offload RAM natif) |
| **Maintenance des Moteurs** | 1 wrapper à réécrire par modèle (LTX, Wan, LivePortrait) | **UNIFIÉE** via l'API standard `POST 127.0.0.1:8188/prompt` |
| **Autorité dans E-ZzIO** | Risque de contamination du Core | **ISOLATION TOTALE** (Considéré comme simple backend externe) |

### VERDICT : **`COMFYUI_NET_POSITIVE`**
ComfyUI est conservé comme **Moteur d'Exécution Multimédia Externe Sandboxé**. Il ne possède aucune autorité cognitive, décisionnelle ou mémorielle sur E-ZzIO.
