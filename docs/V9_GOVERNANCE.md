# E-ZZIO V9.0 — COMPLETE ARCHITECTURE GOVERNANCE

**Date d'Entrée en Vigueur** : 29 août 2026

```text
============================================================
              E-ZZIO V9.0 GOVERNANCE CHARTER
============================================================
CORE                 : FROZEN
CAPABILITIES         : EVOLVING
MODEL CATALOG        : EVOLVING
EXPERIMENTAL         : SANDBOXED
LEGACY               : QUARANTINED
HUMAN TOOLS          : EXTERNAL

ENTRY POINT          : web_server.py:8001
COGNITIVE AUTHORITY  : CognitiveGateway
MODEL AUTHORITY      : ModelRouter
GEMINI AUTHORITY     : GeminiPool
GEMINI PRIMARY      : YES
OLLAMA SECONDARY     : YES

MEMORY               : UnifiedMemoryGateway
SECURITY             : CapabilityPolicy
CODING WORKER        : CodingAgentHarness

REST                 : HTTPX
DISCORD WS           : aiohttp

ACTIVE ROUTERS       : 7
ACTIVE REQUESTS      : 0
ACTIVE LITELLM       : 1 (Schemas & Fallback Bridge)

TESTS                : 311 / 311 PASSED
ARCHITECTURE FREEZE  : MAINTAIN
============================================================
```

---

## LES 20 RÈGLES DE VIE PERMANENTES D'E-ZZIO V9.0

1. **RULE 01 — ONE ENTRY POINT** : `web_server.py:8001` est le point d'entrée HTTP canonique unique.
2. **RULE 02 — ONE COGNITIVE AUTHORITY** : `CognitiveGateway` est l'unique autorité cognitive.
3. **RULE 03 — ONE MODEL STRATEGY AUTHORITY** : `ModelRouter` est l'unique autorité de profil de modèle.
4. **RULE 04 — ONE GEMINI INFRASTRUCTURE AUTHORITY** : `GeminiPool` gère souverainement les projets et quotas.
5. **RULE 05 — GEMINI PRIMARY FIRST** : Gemini est systématiquement sollicité en priorité par défaut.
6. **RULE 06 — OLLAMA SECONDARY** : Ollama est réservé au second rideau local et ne bloque jamais le boot.
7. **RULE 07 — ONE MEMORY AUTHORITY** : `UnifiedMemoryGateway` est l'unique système de mémoire SQLite WAL + FTS5.
8. **RULE 08 — ONE CAPABILITY POLICY** : Toute action sensible passe par l'arbitrage `ALLOW / REQUIRE_HUMAN / DENY`.
9. **RULE 09 — ONE CODING WORKER** : `CodingAgentHarness` est l'unique moteur de code et de self-healing.
10. **RULE 10 — HTTPX FOR REST** : `httpx.AsyncClient` est le client HTTP universel.
11. **RULE 11 — AIOHTTP ONLY FOR WEBSOCKET** : `aiohttp` est confiné exclusivement à Discord.
12. **RULE 12 — NO LEGACY REENTRY** : Interdiction formelle d'importer depuis `legacy_archive/`.
13. **RULE 13 — NO QUARANTINE REENTRY** : Interdiction formelle d'importer depuis `state/quarantine/`.
14. **RULE 14 — NO EXPERIMENTAL CORE IMPORT** : Tout framework expérimental doit rester sandboxed hors Core.
15. **RULE 15 — MODEL CATALOG EVOLVING** : Les identifiants de modèles sont des données dynamiques séparées du Core.
16. **RULE 16 — CAPABILITIES EVOLVING** : Le système s'étend horizontalement par le Capability Framework.
17. **RULE 17 — NO NEW AUTHORITY WITHOUT GATE** : Interdiction d'ajouter une seconde autorité sans Architecture Gate.
18. **RULE 18 — NO NEW CORE DEPENDENCY WITHOUT JUSTIFICATION** : Toute dépendance doit avoir une valeur nette positive.
19. **RULE 19 — DATA ≠ INSTRUCTION** : Toute donnée externe est étiquetée `[DONNÉE PASSIVE NON FIABLE]`.
20. **RULE 20 — FAIL-CLOSED** : Toute défaillance sur une capacité sensible entraîne un blocage sécurisé immédiat.
