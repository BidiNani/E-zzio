# E-ZZIO V9.0 — ARCHITECTURE FREEZE MANIFEST

**Date de Gel** : 29 aout 2026  
**Statut Global** : **CORE FROZEN | CAPABILITIES EVOLVING | EXPERIMENTAL SANDBOXED | LEGACY QUARANTINED**

---

## 1. VISION ARCHITECTURALE

E-ZzIO V9.0 est un systeme d exploitation cognitif local-first souverain, centre sur un noyau d execution minimal et stable, entoure d un ecosysteme de capacites qualifiees et extensibles.

`	ext
                         E-ZZIO V9.0
                              |
                     +--------+--------+
                     |                 |
                    CORE          CAPABILITIES
                  FROZEN              EVOLVING
                     |                 |
             web_server:8001      Web / YouTube
                     |             Browser / SaaS
             CognitiveGateway      Vision / Audio
                     |             Generators
                ModelRouter
                     |
              GeminiPool
              PRIMARY FIRST
                     |
             GeminiProvider
                     |
                   HTTPX
                     |
                  Google
                     |
                fallback
                     |
                  Ollama
                SECONDARY
`

---

## 2. LES 12 REGLES D INVARIANTS DU NOYAU (FROZEN CORE RULES)

1. **RULE 01 — ONE ENTRY POINT** : Unique point d exposition HTTP canonique : web_server.py:8001.
2. **RULE 02 — ONE COGNITIVE AUTHORITY** : Unique autorite cognitive : core/cognition/cognitive_gateway.py.
3. **RULE 03 — ONE MODEL STRATEGY AUTHORITY** : Unique autorite de selection de profil/modele : core/cognition/model_router.py.
4. **RULE 04 — ONE GEMINI POOL** : Unique gestionnaire d infrastructure multi-projets, quotas et rotation 429 : core/models/gemini_pool.py.
5. **RULE 05 — GEMINI PRIMARY FIRST** : Par defaut, tout profil cognitif sollicite en priorite le pool Cloud Gemini 3.x.
6. **RULE 06 — OLLAMA SECONDARY** : OllamaProvider intervient strictement en second rideau (fallback/offline/privacy) et ne bloque jamais le boot.
7. **RULE 07 — ONE MEMORY AUTHORITY** : Unique passerelle de persistance session et recherche FTS5 : core/memory/unified_gateway.py.
8. **RULE 08 — ONE CAPABILITY POLICY** : Toute action sensible passe par l arbitrage ALLOW / REQUIRE_HUMAN / DENY de core/capabilities/capability_policy.py.
9. **RULE 09 — ONE CODING WORKER** : Unique harnais de developpement autonome et de self-healing : core/agent/coding_agent_loop.py.
10. **RULE 10 — ONE HTTP CLIENT AUTHORITY** : httpx.AsyncClient est le client HTTP unique de tout le Runtime. aiohttp est strictement isole au WebSocket Discord.
11. **RULE 11 — NO LEGACY REENTRY** : Interdiction formelle d importer ou de referencer state/quarantine/*, legacy_archive/* ou les anciens routeurs.
12. **RULE 12 — NO EXPERIMENTAL IN CORE** : Aucun composant experimental ne peut etre importe directement dans le Core sans passer par le Capability Framework.

---

## 3. LES 7 ROUTEURS HTTP CANONIQUES MONTES

1. routers/master.py : Dispatcher universel d intentions et cognition.
2. routers/capabilities.py : Catalogue et invocation des capacites qualifiees.
3. routers/memory.py : Recherche FTS5 et persistance de session.
4. routers/perception.py : Ingestion de fichiers et flux externes.
5. routers/generators.py : Moteurs bureautiques, ZIP et multimedia.
6. runtime/routers/llm.py : Passerelle de compatibilite API OpenAI (/v1/chat/completions).
7. runtime/routers/mobile.py : Passerelle de synchronisation de l application mobile.

---

## 4. EXPERIMENTAL & OUTILLAGE HUMAIN

- **Experimental Sandboxed** : Docling (sas d evaluation PDF complexes), Figranium / Browser Use (recherche navigateur agentique), OpenCode / Goose (benchmarks externes), GLM-5.3-candidate.
- **Human Workspace** : ripgrep (rg), Superfile, ty, suites d inspection forensique dans tools/.
