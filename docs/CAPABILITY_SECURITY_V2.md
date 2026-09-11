# E-ZZIO V10.0 — CAPABILITY SECURITY V2

---

## 1. GARANTIES CONTRE LES ATTAQUES ADVERSAIRES
- **Protection Anti-Altération du Core :** Tentative d'écriture vers `web_server.py`, `core/`, `routers/` bloquée immédiatement (`DENY`, flag `CORE_WRITE_OR_SECRET_ACCESS_DENIED`).
- **Protection Anti-Fuite de Secrets :** Tentative de lecture de `.env` ou de `secrets/` bloquée immédiatement.
- **Protection Anti-Escalade de Privilèges :** Demandes de privilèges `admin`, `system`, `unbounded_shell` soumises obligatoirement à validation humaine (`REQUIRE_HUMAN`).
