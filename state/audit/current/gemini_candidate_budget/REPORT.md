# 🏛️ E-ZZIO — RAPPORT D'AUDIT DU BUDGET MULTI-CANDIDATS GEMINI

**Date :** 1 septembre 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Verdict :** **CANDIDATE_BUDGET_OPTIMIZABLE**

---

## 1. SOURCE STRUCTURELLE DES ~49 SECONDES

L'audit démontre que le timeout unitaire de **15 secondes** est parfaitement respecté.

La source des **49.195 secondes** provient exclusivement de la **sérialisation de 3 modèles candidats dans `GeminiProvider.search`** :

```
Requête Cognition
       │
       ├─ Candidat #1 (`gemini-3.6-flash`) ➔ Timeout réseau (15.00s)
       │
       ├─ Candidat #2 (`gemini-3.5-flash`) ➔ Timeout réseau (15.00s)
       │
       ├─ Candidat #3 (`gemini-3-flash`)    ➔ Timeout réseau (15.00s)
       │  [Total boucle Gemini : 3 × 15.0s = 45.00s]
       │
       └─ Repli Same-Role Groq (`groq/compound`) ➔ Succès 200 OK (4.195s)
          [Total : 45.00s + 4.195s = 49.195s]
```

---

## 2. SYNTHÈSE DES PROFILS ET BUDGETS

| PROFIL | CANDIDATS GEMINI | TIMEOUT UNITAIRE | WORST-CASE GEMINI | REPLI GROQ | WORST-CASE TOTAL |
|---|---|---|---|---|---|
| **FAST** | 3 modèles | 15.0 s | 45.0 s | 8.0 s | **53.0 s** |
| **GENERAL** | 3 modèles | 15.0 s | 45.0 s | 8.0 s | **53.0 s** |
| **CODING** | 3 modèles | 15.0 s | 45.0 s | 8.0 s | **53.0 s** |
| **DEEP** | 3 modèles | 15.0 s | 45.0 s | 8.0 s | **53.0 s** |

---

## 3. ANALYSE DES SOLUTIONS & SÉCURITÉ

1. **Parallélisation des candidats :** Rejetée (**UNSAFE**). Sonder 3 modèles en parallèle pour une seule question triplerait la consommation de tokens et violerait les quotas de requêtes.
2. **Candidat d'optimisation futur :**
   - **Interruption sur Timeout Réseau :** Si le candidat #1 subit un `httpx.TimeoutException` (panne réseau de l'endpoint Google), interrompre immédiatement la boucle de modèles pour basculer sur Groq sans infliger les 2 timeouts redondants.
   - **Plafond de candidats :** Limiter à 2 candidats max par profil.
3. **Maintien du gel :** Aucune modification de code n'est effectuée pendant cette phase d'audit.
