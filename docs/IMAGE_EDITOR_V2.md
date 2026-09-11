# E-ZZIO V10.0 — IMAGE EDITOR V2 SPECIFICATION

---

## 1. ENDPOINT REST CANONIQUE
- **Route :** `POST /generators/image/edit` (dans `routers/generators.py`)
- **Corps de Requête :**
```json
{
  "input_path": "outputs/banniere_tech.png",
  "output_filename": "banniere_modifiee.png",
  "operations": [
    {"action": "resize", "width": 800, "height": 400},
    {"action": "rotate", "angle": 90},
    {"action": "brightness", "factor": 1.2},
    {"action": "contrast", "factor": 1.1},
    {"action": "blur", "radius": 1.5},
    {"action": "text_overlay", "text": "ÉDITÉ PAR E-ZZIO", "position": [30, 30]}
  ]
}
```

---

## 2. GARANTIES D'ÉDITION
- **Non-destructive :** Original 100% préservé.
- **Traçabilité :** `hash_before` (SHA-256) et `hash_after` (SHA-256) systématiquement retournés.
- **Performance :** Moins de 20 ms en local CPU via Pillow.
