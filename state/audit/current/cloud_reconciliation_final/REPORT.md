# 🏛️ E-ZZIO — RAPPORT DE RÉCONCILIATION FINALE DES RESSOURCES CLOUD

**Date :** 1 septembre 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Verdict :** **FINAL_CLOUD_TRUTH_ESTABLISHED**

---

## 1. RÉSOLUTION DÉFINITIVE DES 6 CONTRADICTIONS

1. **FAST (3.1 vs 3.5) :** `ModelRouter` sélectionne `gemini-3.1-flash-lite` comme modèle primaire souverain, avec `gemini-3.5-flash-lite` comme candidat alternatif de pool.
2. **GENERAL (3.6 vs 3.5) :** `ModelRouter` sélectionne `gemini-3.6-flash` comme modèle primaire souverain, avec `gemini-3.5-flash` comme candidat alternatif de pool.
3. **Tavily / Jina :** Implémentés et validés en code, mais en statut **CONFIG_OPTIONAL / DORMANT** car DuckDuckGo et SafeWebFetcher traitent 100% des requêtes en totale autonomie.
4. **Gemini Pool Size :** 1 projet configuré (`project_default`) avec support multi-clés et découverte dynamique de projets additionnels.
5. **1 104 Credentials :** Occurrences de lecture AST dans le code source, correspondant à **45 noms de variables uniques** et **4 clés réelles actives en production**.
6. **Modèles Groq Actifs :** `groq/compound-mini` (Fast), `groq/compound` (General), `qwen/qwen3.6-27b` (Coding), `openai/gpt-oss-120b` (Deep).

---

## 2. VÉRITÉ CANONIQUE DU ROUTAGE CLOUD

| PROFIL | PRIMAIRE (GEMINI) | SECONDAIRE (GROQ) | DERNIER RECOURS (OLLAMA) | STATUT |
|---|---|---|---|---|
| **FAST** | `gemini-3.1-flash-lite` | `groq/compound-mini` | `phi4-mini:latest` | **CANONIQUE** |
| **GENERAL** | `gemini-3.6-flash` | `groq/compound` | `hermes3:8b` | **CANONIQUE** |
| **CODING** | `gemini-3.7-flash` | `qwen/qwen3.6-27b` | `qwen3.5:9b` | **CANONIQUE** |
| **DEEP** | `gemini-3.1-pro-preview` | `openai/gpt-oss-120b` | `qwen3.5:9b` | **CANONIQUE** |
| **IMAGE** | `gemini-3.1-flash-image` | `gemini-3-pro-image` | N/A | **CANONIQUE** |
| **VIDEO** | `gemini-omni-1.1-flash` | N/A | N/A | **CANONIQUE** |
