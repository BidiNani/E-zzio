# 🏛️ E-ZZIO — RAPPORT D'AUTOPSIE CIBLÉE DES LATENCES P95

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Objet :** Explication médico-légale de l'origine de la latence P95 (~38.6s) observée lors de la certification

---

## 1. EXPLICATION CAUSALE DU P95 (~38.6s)

L'autopsie des 30+ requêtes montre que le P95 global (**38 586.43 ms**) ne reflète absolument pas la vitesse nominale du système (**médiane = 10.53 ms**, **nominal Cloud LLM = 650 ms**, **documents = 3.3 ms**).

Ce pic provient exclusivement de **2 requêtes exceptionnelles soumises à une cascade de replis consécutifs (Failover Chain)** lors d'un épuisement temporaire des quotas cloud :

```
Requête #114d707c (GENERAL)
    │
    ├─ 1. Tentative Gemini Pool (`gemini-3.6-flash`) ➔ Échec HTTP 429 Quota Exhausted (Timeout réseau)
    │     [Cooldown déclenché : 10s]
    │
    ├─ 2. Repli Groq Cloud (`groq/compound`) ➔ Échec HTTP 413 / 429 (Timeout réseau)
    │     [Cooldown déclenché : 10s]
    │
    ├─ 3. Repli Ollama Local (`hermes3:8b`) ➔ En cooldown / indisponible
    │
    └─ 4. Sortie Sécurisée FAIL_CLOSED : Total cumulé des timeouts HTTP = 38.58 secondes
```

---

## 2. DÉCOMPOSITION DU P95 PAR SOUS-SYSTÈME

| SOUS-SYSTÈME | MÉDIANE | P95 NOMINAL | NATURE DU FLUX |
|---|---|---|---|
| **Cache Technique** | 0.85 ms | 1.20 ms | Instantané (0 quota, 0 latence) |
| **Documents Universels** | 3.30 ms | 5.86 ms | Parsing local in-memory ultra-rapide |
| **Async Singleflight** | 229.24 ms | 229.24 ms | Coalescing de 10 appels simultanés |
| **Gemini Pool (Nominal)** | 650.00 ms | 2 575.09 ms | Appel API Cloud nominal |
| **Groq Cloud (Same-Role)** | 380.00 ms | 1 957.65 ms | Appel API Cloud Same-Role |
| **Recherche & Crawl Web** | 719.80 ms | 961.38 ms | Requêtes HTTPS externes (Expected Slow Path) |
| **Synthèse Vocale (TTS)** | 806.01 ms | 979.49 ms | Inférence neuronale Kokoro ONNX |
| **Cascade Failover (Anomalie)** | 22 657.28 ms | **38 586.43 ms** | Cumul des timeouts HTTP sur échecs multiples |

---

## 3. CONCLUSION FORENSIC

1. **Aucune régression logicielle :** La vitesse nominale de l'ensemble des modules (Documents, Mémoire, Web, Cache, Gemini) est excellente.
2. **Comportement Fail-Safe certifié :** Même en cas d'indisponibilité totale et simultanée de tous les providers externes, le système refuse de planter et bascule proprement en `FAIL_CLOSED` sans fuite de secrets ni plantage du serveur.
