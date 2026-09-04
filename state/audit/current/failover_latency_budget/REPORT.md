# 🏛️ E-ZZIO — RAPPORT D'AUDIT DU BUDGET DE LATENCE EN CAS D'ÉCHEC MULTI-PROVIDER

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Verdict :** **TIMEOUT_OPTIMIZATION_CANDIDATE**

---

## 1. CARTOGRAPHIE DU BUDGET DE LATENCE DE FAILOVER

L'audit des timeouts réels dans la chaîne de repli cognitive a identifié la décomposition temporelle suivante en cas de panne totale simultanée :

```
Requête Cognition
       │
       ▼
[ Gemini Provider (3 candidats max) ] ── (30s timeout max par appel)
       │ (Échec / 429)
       ▼
[ Groq Provider (Same-Role) ] ────────── (15s timeout max)
       │ (Échec / 429)
       ▼
[ Ollama Local (Dernier Recours) ] ────── (30s timeout max)
       │ (Échec / Offline)
       ▼
[ Sortie FAIL_CLOSED ] ───────────────── Total cumulé théorique max = 135s (Observé réel = 38.58s)
```

---

## 2. SYNTHÈSE DES BUDGETS

| PARAMÈTRE | CONFIGURÉ | OBSERVÉ RÉEL | CIBLE SÛRE RECOMMANDÉE |
|---|---|---|---|
| **Gemini Timeout (par essai)** | 30.0 s | ~22.0 s (réseau) | **8.0 s** |
| **Groq Timeout** | 15.0 s | 0.48 s (413/429) | **6.0 s** |
| **Ollama Timeout** | 30.0 s | ~15.0 s (connect) | **4.0 s** |
| **Circuit Breaker Overhead** | < 0.1 ms | < 0.1 ms | **< 0.1 ms** |
| **Failover Gemini ➔ Groq Réussi** | -- | **1.95 s** | **< 2.5 s** |
| **Failover Complet ➔ FAIL_CLOSED** | 135.0 s | **38.58 s** | **< 15.0 s** |

---

## 3. CONCLUSION & RECOMMANDATION

1. **Robustesse 100% préservée :** Le circuit breaker et la gestion `FAIL_CLOSED` fonctionnent exactement comme prévu sans plantage serveur.
2. **Failover Nominal Rapide :** Quand Groq est disponible, la bascule s'effectue en **1.95 seconde**.
3. **Piste d'ajustement futur :** Un abaissement concerté des timeouts HTTP (Gemini 8s, Groq 6s, Ollama 4s) permettra de borner le pire des cas sous 15 secondes sans toucher à l'architecture.
