# E-ZZIO V10.0 — IMAGE EDITOR V3 SPECIFICATION

---

## 1. ENDPOINT D'ÉDITION DÉTERMINISTE
- **Route :** `POST /generators/image/edit` dans `routers/generators.py`
- **Moteur :** Pillow (< 20 ms, 0 GPU)
- **Opérations :** `crop`, `resize`, `rotate`, `flip`, `brightness`, `contrast`, `blur`, `text_overlay`, `watermark`.
- **Politique :** 100% non-destructive (l'image originale n'est jamais écrasée). Sortie auditée avec `hash_before` et `hash_after` (SHA-256).
