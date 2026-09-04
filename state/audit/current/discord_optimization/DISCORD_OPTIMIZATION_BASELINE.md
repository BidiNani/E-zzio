# 🏛️ DISCORD OPTIMIZATION — BASELINE FORENSIQUE

**Date de référence :** 31 août 2026  
**Dépôt cible :** `G:\AI\E-zzio`  
**Composant audité :** `core/integrations/discord/discord_client.py`

---

## 1. MÉTROLOGIE INITIALE (AVANT OPTIMISATION)

| Métrique | Valeur Observée | Interprétation |
| :--- | :---: | :--- |
| **`ASK_TTFT`** | 10.6903 s | Délai d'arrivée du premier token backend. |
| **`ASK_FIRST_VISIBLE`** | 10.6903 s | Délai avant le premier edit Discord. |
| **`ASK_TOTAL`** | 10.6904 s | Durée totale d'inférence et de rendu. |
| **`CONCURRENT_2`** | 1.007 s | Traitement simultané de 2 utilisateurs. |
| **`CONCURRENT_5`** | 0.9923 s | Traitement simultané de 5 utilisateurs. |
| **`STATUS_TOTAL`** | 0.0011 s | Récupération de télémétrie `/metrics`. |
| **`PDF_TOTAL`** | 0.0034 s | Génération vectorielle ReportLab. |
| **`XLSX_TOTAL`** | 0.1172 s | Génération OpenPyXL avec formules. |
| **`ERROR_RECOVERY`** | 0.7426 s | Reprise gracieuse sur requête invalide. |

---

## 2. GOULOTS D'ÉTRANGLEMENT IDENTIFIÉS

1. **Latence de Premier Rendu Artificielle :** Le timer de cadencement initialisait `last_edit_time = time.perf_counter()`, obligeant le premier token à attendre $\ge 1.2$ s avant affichage initial.
2. **Gestion de Session HTTP :** Création répétée de `aiohttp.ClientSession` sans pool de connexions persistant `TCPConnector`.
3. **Absence de Backoff 429 Dédié :** Les erreurs HTTP Discord lors du streaming étaient simplement ignorées sans réajustement de cadence.
