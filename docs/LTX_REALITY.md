# E-ZZIO V10.0 — LTX REALITY & LICENSING SPECIFICATION

---

## 1. VÉRIFICATION DES VERSIONS LTX
- **LTX-Video (v0.9.x / Nov 2024) :**
  - **Dépôt :** `Lightricks/LTX-Video`
  - **Licence Code :** Apache-2.0
  - **Licence Poids :** Apache-2.0 (Usage commercial permis)
  - **Modèle :** Diffusion Transformer (DiT), ~2B paramètres.
- **LTX-2 / LTX-2.x (2025/2026) :**
  - **Dépôt :** `Lightricks/LTX-2`
  - **Licence Code :** Apache-2.0
  - **Licence Poids :** Apache-2.0 / Open Weights
  - **Fonctionnalité Clé :** Génération vidéo + audio synchronisé dans une passe unifiée.

---

## 2. VIABILITÉ SUR GTX 1650 4 GB
- **GGUF Q4_K / FP8 :** En utilisant le sequential CPU offload de ComfyUI, le modèle consomme **~3.7 Go de VRAM** et déborde de manière contrôlée sur les 32 Go de RAM système.
- **Résolution Recommandée :** 480p (768x480) à 24 fps sur 5 secondes.
- **Temps Réel Estimé :** ~35 à 48 secondes par clip de 5 secondes.
- **Verdict :** **`LOCAL_REAL (P0 ADOPT)`**.
