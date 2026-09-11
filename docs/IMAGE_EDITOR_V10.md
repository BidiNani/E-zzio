# E-ZZIO V10.0 — IMAGE EDITOR CAPABILITY SPECIFICATION

**Date d'Activation** : 29 août 2026

---

## 1. ENDPOINT REST CANONIQUE
- **Route** : `POST /generators/image/edit` (dans `routers/generators.py`)
- **Corps de Requête** :
```json
{
  "input_path": "outputs/banniere_tech.png",
  "output_filename": "banniere_modifiee.png",
  "operations": [
    {"action": "resize", "width": 800, "height": 400},
    {"action": "rotate", "angle": 90},
    {"action": "brightness", "factor": 1.2},
    {"action": "contrast", "factor": 1.1},
    {"action": "text_overlay", "text": "ÉDITÉ PAR E-ZZIO", "position": [30, 30]}
  ]
}
```

---

## 2. INVARIANTS D'ÉDITION SOUVERAINE
1. **Non-destructive** : L'image source originale n'est jamais écrasée.
2. **Traçabilité par Hash** : Le résultat retourne systématiquement `hash_before` et `hash_after`.
3. **Moteur Déterministe** : Exécution locale via Pillow en moins de **30 ms**.
