# E-ZZIO V10.0 — CAPABILITY INSTALLATION SPECIFICATION V1

---

## 1. STRUCTURE DU SAS EXTERNE

```text
G:\AI\external\capabilities\
    ├── <capability_name>\
    │   ├── capability.manifest.json  (Métadonnées, licence, permissions, statut)
    │   ├── runtime\                  (Environnement ou binaire isolé)
    │   ├── models\                   (Poids de modèles quantifiés éventuels)
    │   ├── logs\                     (Traces d'exécution)
    │   └── tests\                    (Tests d'intégrité locaux)
```
