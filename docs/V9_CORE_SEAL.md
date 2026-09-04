# E-ZZIO V9.0 — CORE ARCHITECTURE SEAL

**Date de Scellement** : 29 août 2026  
**Statut Légal & Technique** : **CORE SCELLÉ (FROZEN ARCHITECTURE) │ CAPABILITIES ÉVOLUTIVES**

---

## 1. DÉFINITION DU SCELLEMENT DU NOYAU
Le scellement du Core signifie que **l'architecture fondamentale, les frontières de sécurité et les autorités uniques sont figées**.

Il ne signifie pas que le code est interdit de correction.

### Modifications Autorisées (sans briser le scellement) :
1. `SECURITY FIX` : Correction immédiate d'une vulnérabilité ou faille de sécurité.
2. `CRITICAL BUG FIX` : Correction d'un dysfonctionnement bloquant avec test de non-régression associé.
3. `PERFORMANCE FIX` : Optimisation de latence ou consommation mémoire démontrée par benchmark.
4. `COMPATIBILITY FIX` : Mise à jour pour compatibilité OS ou mise à jour de l'interpréteur Python.
5. `ARCHITECTURE CHANGE GATE` : Évolution contractuelle formalisée et validée par une Gate d'Architecture dédiée.

### Modifications Interdites :
- Ajout d'une seconde autorité (modèle, mémoire, code, serveur).
- Contournement de `CapabilityPolicy`.
- Réintroduction de dépendances obsolètes (`requests`, `langgraph`).
- Import de composants expérimentaux directement dans le noyau.

---

## 2. LES 12 COMPOSANTS DU NOYAU SCELLÉ
1. `web_server.py:8001` (Serveur ASGI FastAPI canonique)
2. `core/sdk.py` (Façade SDK in-process)
3. `core/cognition/cognitive_gateway.py` (Autorité cognitive)
4. `core/cognition/model_router.py` (Autorité stratégique de modèle)
5. `core/models/gemini_pool.py` (Autorité d'infrastructure multi-projets & quotas)
6. `core/providers/gemini_provider.py` (Transport Gemini Cloud via HTTPX)
7. `core/memory/unified_gateway.py` (Autorité mémoire SQLite WAL + FTS5)
8. `core/capabilities/capability_policy.py` (Autorité d'arbitrage de sécurité)
9. `core/capabilities/registry.py` (Registre canonique des capacités)
10. `core/security/audit_ledger.py` (Journal d'audit cryptographique SHA-256)
11. `core/security/secrets_vault.py` (Gestionnaire de secrets AES-256-GCM / DPAPI)
12. `core/agent/coding_agent_loop.py` (Harnais de développement autonome souverain)
