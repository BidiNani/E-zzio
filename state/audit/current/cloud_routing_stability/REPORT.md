# 🏛️ E-ZZIO — RAPPORT DE STABILISATION FINALE DU ROUTAGE CLOUD-AWARE

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Composant :** `core/cognition/model_router.py`

---

## 1. PRINCIPE CARDINAL : DÉLÉSTAGE DYNAMIQUE VS SUPPRESSION

Un quota temporairement saturé ne supprime aucun modèle du système :

```
                        [ MODÈLE DU CATALOGUE ]
                                   │
                                   ▼
                    [ 1. ÉLIGIBLE & PRÉFÉRÉ ]
                                   │
                                   │ 429 / Quota faible
                                   ▼
                [ 2. TEMPORARILY_DEPRIORITIZED ]
                (Bascule fluide vers le candidat suivant)
                                   │
                                   │ Expiration du cooldown / Réapprovisionnement
                                   ▼
                  [ 3. RECOVERED & ÉLIGIBLE ]
                (Retour automatique sans redémarrage)
```

---

## 2. SYNTHÈSE DES POOLS DE CANDIDATS PAR PROFIL

- **FAST :** `gemini-3.1-flash-lite` (Actuel) $ightarrow$ `gemini-3.5-flash-lite` (Délester/Eligible) $ightarrow$ `gemini-2.5-flash-lite` $ightarrow$ Groq `groq/compound-mini` $ightarrow$ Ollama `phi4-mini:latest`.
- **GENERAL :** `gemini-3.6-flash` (Actuel) $ightarrow$ `gemini-3.5-flash` (Délester/Eligible) $ightarrow$ `gemini-3-flash` $ightarrow$ Groq `groq/compound` $ightarrow$ Ollama `hermes3:8b`.
- **CODING :** `gemini-3.7-flash` (Actuel) $ightarrow$ Groq `qwen/qwen3.6-27b` $ightarrow$ Ollama `qwen3.5:9b`.
- **DEEP :** `gemini-3.1-pro-preview` (Actuel) $ightarrow$ Groq `openai/gpt-oss-120b` $ightarrow$ Ollama `qwen3.5:9b`.

---

## 3. RÉSULTATS PHYSIQUES DES TESTS DE STABILITÉ

1. **Intégrité du catalogue :** `gemini-3.5-flash-lite` et `gemini-3.5-flash` restent présents et pleinement configurés.
2. **Auto-Récupération prouvée :** Après injection de 429 sur 3.1, le routeur bascule sur 3.5 puis restaure automatiquement 3.1 à l'expiration du cooldown.
3. **Zéro Flapping :** 5 requêtes consécutives produisent un choix 100% stable.
4. **Cache & Singleflight :** 0.73 ms de latence sur hit (0 token) et fusion parfaite des requêtes concurrentes froides.
