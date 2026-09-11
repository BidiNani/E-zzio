# E-ZZIO V10.0 — CAPABILITY DISCOVERY V2

---

## 1. MOTEUR DE DÉCOUVERTE DYNAMIQUE
- **Fichier :** [`core/capabilities/discovery.py`](file:///G:/AI/E-zzio/core/capabilities/discovery.py)
- **Scoring Composé (0-10) :**
  - Valeur fonctionnelle native (0-10)
  - Pénalité de licence (0 si permissive, -2.0 si non-commerciale/NC)
  - Pénalité matérielle (-4.0 si le VRAM requis dépasse le hardware actuel)
  - Pénalité de risque (0 pour LOW, -0.5 pour MEDIUM, -1.5 pour HIGH)
