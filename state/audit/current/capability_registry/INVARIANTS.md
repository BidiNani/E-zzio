# E-ZZIO — REGISTRE DES INVARIANTS & GOUVERNANCE ARCHITECTURALE

**Date de validation :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`

---

## 1. SOVEREIGN AUTHORITIES (RÈGLE DES AUTORITÉS UNIQUES)

| DOMAINE | AUTORITÉ CANONIQUE UNIQUE | FICHIER SOURCE | CONTRÔLE D'INTÉGRITÉ |
|---|---|---|---|
| **ROUTAGE COGNITIF** | `ModelRouter` | `core/cognition/model_router.py` | **SECOND_MODEL_AUTHORITY = FALSE** |
| **MÉMOIRE & ÉTAT** | `UnifiedMemoryGateway` | `core/memory/unified_gateway.py` | **SECOND_MEMORY_AUTHORITY = FALSE** |
| **SECRETS & SÉCURITÉ** | `SecretsVault` | `core/security/secrets_vault.py` | **SECOND_SECURITY_AUTHORITY = FALSE** |
| **RUNTIME D'EXÉCUTION** | `Ezzio Sovereign Runtime` | `runtime/` & `core/` | **SECOND_RUNTIME = FALSE** |

---

## 2. AUDIT DES DIVERGENCES ET RÉFÉRENCES STALE

### A. Routing Divergences (`ROUTING_DIVERGENCES`)
- Le fichier `runtime/model_router/config.json` définit des routes locales pointant vers `granite4.1:8b`, `qwen3-coder:30b`, et `mrasif/gpt-oss-20b-GGUF:Q4_K_M`. Ces modèles ne sont pas installés dans Ollama.
- L'autorité souveraine `core/cognition/model_router.py` route en Cloud-First vers le pool Gemini (`gemini-3.7-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`).
- **Statut :** Confinement validé : `core/cognition/model_router.py` a la prééminence absolue.

### B. Références Stale (`STALE_MODEL_REFERENCES`)
1. `qwen2.5-coder:7b` : Référencé comme `LOCAL_FALLBACK_MODEL` dans `ModelRouter`, non installé.
2. `qwen2.5:3b` : Référencé dans `select_engine(complexity < 0.3)`, non installé.
3. `gemma4e4b:latest` : Référencé dans des benchmarks historiques, non présent dans Ollama.
4. `qwen2.5vl:3b` : Référence de repli vision, non installée.

### C. Dérive du Cœur Figé (`FROZEN_CORE_DRIFT`)
- Tous les fichiers du cœur historique (`core/`, `runtime/`, `config/`) sont préservés intacts.
- **FROZEN_CORE_DRIFT = FALSE (0 modification non autorisée)**.
