# E-ZZIO — ARCHITECTURE CHANGELOG

---

## [V9.1.0] - 2026-09-01 - GEMINI REGISTRY AUTO-REFRESH
- **Gemini Registry** : Synchronisation dynamique du registre Gemini depuis l'API Google (`core/models/registry_refresh.py`, `core/models/registry_refresh_service.py`).
- **Déclencheurs** : Startup (fail-safe), déclenchement manuel (`POST /api/models/registry/refresh/gemini`), scheduler quotidien asyncio (single-process).
- **Invariants** : ModelRouter frozen, gemini_pool frozen, aucune activation automatique, aucune suppression physique, fail-safe complet.
- **Tests** : 17/17 PASS (7 registry + 10 auto-refresh).
- **Documentation** : `docs/GEMINI_REGISTRY_AUTO_REFRESH.md`.
- **Limitation documentée** : Scheduler interne non process-safe — single-process requis.

## [V9.0.0] - 2026-08-29 - ARCHITECTURE FREEZE & GOVERNANCE
- **Core Freeze** : Verrouillage formel des 12 composants souverains (`docs/FROZEN_CORE_MANIFEST.json`).
- **Gouvernance des Modèles** : Séparation stricte entre l'architecture (gelée) et le catalogue de modèles (dynamique / évolutif).
- **Assainissement des Dépendances** : Retrait total de `requests` (0 import actif), unification sous `httpx.AsyncClient`.
- **Routage HTTP Minimal** : Confinement de la surface HTTP aux 7 routeurs canoniques montés.
- **Sécurité & Traçabilité** : 20 tests d'invariants architecturaux automatisés (`tests/test_architecture_freeze.py`).
- **Performance** : Exécution de la suite complète de 308 tests passée à 85.63s (-67% de temps d'exécution).

