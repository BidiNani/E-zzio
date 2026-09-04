# E-ZZIO V9.0 — MODEL CATALOG POLICY

**Principe Fondamental** :
```text
ARCHITECTURE = FROZEN
MODEL CATALOG = EVOLVING
MODEL AUTHORITY = FROZEN (GeminiPool / ModelRouter)
```

---

## 1. DISTINCTION ENTRE ARCHITECTURE ET CATALOGUE DE MODÈLES
- L'architecture d'E-ZzIO verrouille les autorités cognitives, les interfaces asynchrones, les flux de sécurité et la hiérarchie de repli.
- Les identifiants spécifiques de modèles (ex: `gemini-3.7-flash`, `gemini-3.5-flash`, `qwen2.5-coder:7b`) appartiennent au **catalogue dynamique** et ne sont pas des invariants figés du Core.

---

## 2. RÈGLES DE GESTION DU CATALOGUE
1. **Ajout d'un nouveau modèle** : Tout nouveau modèle Gemini ou local peut être déclaré dans `core/models/gemini_pool.py` ou `core/cognition/model_router.py` sans briser le gel architectural.
2. **Dépréciation d'un modèle** : Le retrait d'une version de modèle obsolète se fait par simple bascule de mapping dans le `MODEL_LIFECYCLE_REGISTRY`.
3. **Maintien des Invariants** :
   - L'autorité d'infrastructure reste `GeminiPoolManager`.
   - La priorité par défaut reste `Gemini PRIMARY FIRST`.
   - Ollama reste `SECONDARY LOCAL FALLBACK`.
