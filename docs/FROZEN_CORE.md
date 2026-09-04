# E-ZZIO V9.0 — FROZEN CORE SPECIFICATION

## COMPOSANTS INTOUCHABLES (DO NOT TOUCH WITHOUT ARCHITECTURE GATE)
1. web_server.py : Point d exposition canonique Uvicorn.
2. core/cognition/cognitive_gateway.py : Autorite d orchestration cognitive.
3. core/cognition/model_router.py : Autorite de selection strategique de modele.
4. core/models/gemini_pool.py : Autorite d infrastructure multi-projets Gemini.
5. core/providers/gemini_provider.py : Transport Gemini via HTTPX.
6. core/agent/coding_agent_loop.py : Harnais de coding autonome souverain.
7. core/capabilities/capability_policy.py : Arbitre de securite (ALLOW / REQUIRE_HUMAN / DENY).
8. core/capabilities/registry.py : Registre canonique des capacites.
9. core/memory/unified_gateway.py : Memoire canonique L0-L5 SQLite WAL + FTS5.
10. core/security/audit_ledger.py : Journal d audit cryptographique SHA-256.
11. core/security/secrets_vault.py : Gestionnaire de secrets AES-256-GCM / DPAPI.
12. core/sdk.py : Facade SDK in-process officielle.

## MODIFICATIONS AUTORISEES
- Correctif de securite critique.
- Correction d un bug bloquant atteste par un test unitaire.
- Amelioration de performance mesuree sans alteration de contrat.
- Evolution formelle de contrat validee par une Gate d Architecture.

## MODIFICATIONS INTERDITES SANS NOUVELLE GATE
- Introduction d un second model router.
- Introduction d un second systeme memoire.
- Introduction d un second coding worker actif.
- Contournement de CapabilityPolicy.
- Reintroduction de composants legacy ou de doublons de routeurs.
