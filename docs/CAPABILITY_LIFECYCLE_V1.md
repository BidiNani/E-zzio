# E-ZZIO V10.0 — CAPABILITY LIFECYCLE & ROLLBACK V1

---

## 1. LES ÉTATS DU CYCLE DE VIE

```text
DISCOVERED
    ↓
CANDIDATE (Vérification Licence & Hardware)
    ↓
SANDBOXED (Installation dans G:\AI\external\capabilities\)
    ↓
QUALIFIED (Tests unitaires et benchmarks passés)
    ↓
ACTIVE (Enregistré dans CapabilityRegistry)
    ├── DÉGRADATION ➔ ROLLBACK IMMÉDIAT ➔ QUARANTINED
    └── OBSOLÈTE    ➔ RETIRED
```
