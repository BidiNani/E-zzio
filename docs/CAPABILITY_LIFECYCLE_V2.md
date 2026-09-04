# E-ZZIO V10.0 — CAPABILITY LIFECYCLE V2

---

## 1. MACHINE D'ÉTATS EXPLICITE

```text
DISCOVERED ➔ CANDIDATE ➔ QUALIFYING ➔ SANDBOXED ➔ TESTING ➔ BENCHMARKED ➔ QUALIFIED ➔ ACTIVE
                                                                                │
                                           ┌────────────────────────────────────┴────────────────┐
                                           ↓                                                     ↓
                                        DEGRADED ➔ ROLLBACK ➔ QUARANTINED                     RETIRED
```

- **Rollback automatique :** Si un composant échoue en production, il est immédiatement neutralisé (`QUARANTINED`) sans que le Core ne soit perturbé.
- **Auto-Guérison (Self-Healing) :** Bascule instantanée sur un backend de secours (ex. Pillow ou Gemini Image en cas d'indisponibilité du GPU local).
