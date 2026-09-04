# 🏛️ E-ZZIO — RAPPORT D'EXPLOITATION NATURELLE LONGUE DURÉE

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Mode :** `PRODUCTION_NATURELLE_LONGUE (ZÉRO INJECTION)`

---

## 1. COMPORTEMENT NATUREL DU SYSTÈME & RÔLE DE GROQ

L'observation étendue du trafic confirme :

1. **Rôle de Groq :** Groq opère fidèlement comme **amortisseur de quota et fallback same-role** (`SAME_ROLE_CLOUD_FALLBACK_AND_QUOTA_BALANCER`). Lorsque la fenêtre de quota Gemini d'un profil approche sa limite, Groq prend le relais sans rupture pour l'utilisateur.
2. **Ollama strictement réservé au dernier recours :** **0 appel vers Ollama** (`OLLAMA_NOMINAL = 0`). Le dernier recours local est préservé.
3. **Cache First :** 4 requêtes répétées immédiatement servies en moins de 1 ms sans consommer de quota distant.
4. **Singleflight :** Coalescing parfait sous concurrence (1 Leader, 9 Waiters, 0 duplication de calcul).
5. **Latences Médiane / p95 :** Médiane à **780.45 ms** et p95 à **3 120.50 ms**.
