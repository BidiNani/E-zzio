# 🏛️ E-ZZIO — RAPPORT D'AUTOPSIE DE LA REQUÊTE ~49s APRÈS TIMEOUT TUNING

**Date :** 1 septembre 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Verdict :** **OUTLIER_EXPLAINED**

---

## 1. DÉCOMPOSITION CHRONOLOGIQUE ET MATHEMATIQUE DE LA REQUÊTE #2 (~49.2s)

L'autopsie forensic révèle l'enchaînement temporel exact de la requête #2 (*"Explique succinctement le théorème de Bayes..."*, profil `general`) :

```
Requête #2 (speed="general")
    │
    ├─ 1. GeminiPool Cible 1 (`gemini-3.6-flash`) ➔ Timeout HTTPX (15.00s)
    │
    ├─ 2. GeminiPool Cible 2 (`gemini-3.5-flash`) ➔ Timeout HTTPX (15.00s)
    │
    ├─ 3. GeminiPool Cible 3 (`gemini-3-flash`)    ➔ Timeout HTTPX (15.00s)
    │     [Total Recherche Gemini : 3 x 15.0s = 45.00s]
    │
    ├─ 4. Déclenchement du repli Same-Role Cloud ➔ Groq (`groq/compound`)
    │
    └─ 5. Réponse Groq réussie en 4.19s ➔ HTTP 200 OK
          [Total cumulé : 45.00s + 4.195s = 49.195s (100% exact)]
```

---

## 2. ANALYSE STATISTIQUE (N = 20)

| MÉTRIQUE | VALEUR | INTERPRÉTATION |
|---|---|---|
| **P50 (Médiane)** | **29.52 ms** | Performance nominale ultra-rapide |
| **P90** | **11 016.37 ms** | `FAIL_CLOSED` rapide post-tuning (vs 38.6s avant) |
| **P95 / P99 / MAX** | **49 195.89 ms** | 1 unique requête soumise à 3 timeouts consécutifs Gemini avec récupération réussie sur Groq |

---

## 3. CONCLUSION FORENSIC

1. **Aucune régression logicielle :** Le `FAIL_CLOSED` général a bien été réduit de **38.6s à 11.0s**.
2. **Mécanisme de résilience validé :** Malgré l'échec consécutif de 3 modèles Gemini par timeout de 15s, le système n'a ni crashé ni levé d'exception non gérée : il a basculé proprement sur Groq et fourni la bonne réponse à l'utilisateur.
