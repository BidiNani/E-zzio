# E-ZZIO V10.0 — MEDIA RESOURCE GOVERNANCE POLICY V3

---

## 1. PLAFONDS STRICTS DE RESSOURCES (FAIL-CLOSED)

| Ressource | Plafond Strict Local | Comportement en cas de Dépassement |
| :--- | :--- | :--- |
| **CPU Load** | Maximum 80% (sur 12C/24T) | Régulation automatique des threads |
| **RAM Système** | Maximum 24 Go (sur 32 Go) | Interdiction de swap non contrôlé (Fail-Closed) |
| **VRAM GPU** | Maximum 3.9 Go (sur 4 Go) | Offload séquentiel CPU forcé ou rejet explicite |
| **Disque Temporaire**| Maximum 10 Go dans `runtime/exports/` | Nettoyage TTL (24h) automatique |
| **Timeout Vidéo** | 180 secondes | Annulation et libération mémoire immédiate |
