# 🏛️ E-ZZIO — STRATÉGIE CLOUD-FIRST & MATRICE DE REPLI SAME-ROLE

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`

---

## 1. PRINCIPE CARDINAL : LE CLOUD EN CHEMIN NOMINAL

Le flux nominal d'E-ZzIO est désormais strictement ordonné selon la hiérarchie de souveraineté et de performance :

```
                        Requête Utilisateur / Agent
                                     │
                                     ▼
                            [ 1. CACHE TECHNIQUE ]
                            (Hit en 0.72ms -> 0 Token)
                                     │
                                     ▼ (Miss)
                         [ 2. ASYNC SINGLEFLIGHT ]
                         (1 Leader, N-1 Waiters)
                                     │
                                     ▼
                        [ 3. GEMINI POOL (PRIMARY) ]
                    (596ms / 566ms / 690ms — 5 Clés)
                                     │
                                     │ 429 / 5xx / Timeout
                                     ▼
                      [ 4. GROQ CLOUD (SAME-ROLE) ]
                     (141ms / 255ms / 282ms — Cloud)
                                     │
                                     │ 429 / 5xx / Épuisement Cloud
                                     ▼
                       [ 5. OLLAMA (DERNIER RECOURS) ]
                     (phi4-mini / hermes3 / qwen3.5)
```

---

## 2. MATRICE DE REPLI SAME-ROLE VÉRIFIÉE EN DIRECT

| PROFIL COGNITIF | CLOUD PRIMAIRE (GEMINI) | REPLI CLOUD (GROQ) | DERNIER RECOURS LOCAL (OLLAMA) |
|---|---|---|---|
| **FAST** | `gemini-3.5-flash-lite` (596ms) | `groq/compound-mini` (282ms) | `phi4-mini:latest` |
| **GENERAL** | `gemini-3.5-flash` (566ms) | `groq/compound` (255ms) | `hermes3:8b` |
| **CODING / AGENTIC** | `gemini-3.7-flash` (690ms) | `qwen/qwen3.6-27b` (141ms) | `qwen3.5:9b` |
| **DEEP_REASONING** | `gemini-3.1-pro-preview` | `openai/gpt-oss-120b` (376ms) | `qwen3.5:9b` |

---

## 3. PREUVES PHYSIQUES RUNTIME

- **Requête nominale :** Servie par `gemini_pool` (`gemini-3.5-flash-lite`) en 676 ms. **Zéro sollicitation d'Ollama.**
- **Cache Hit :** Servi en **0.72 ms** (zéro appel réseau).
- **Repli Cloud sur 429 :** Bascule immédiate sur `groq:groq/compound-mini` en 756 ms. **Zéro sollicitation d'Ollama.**
- **Dernier recours :** Bascule sur `ollama:phi4-mini:latest` uniquement lorsque l'ensemble des providers cloud sont indisponibles.
