# 🏛️ E-ZZIO — RAPPORT DE CRÉATION DU RUNBOOK D'EXPLOITATION QUOTIDIENNE

**Date :** 1 septembre 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Document Officiel :** [`docs/EZZIO_OPERATIONS_RUNBOOK.md`](file:///G:/AI/E-zzio/docs/EZZIO_OPERATIONS_RUNBOOK.md)  
**Verdict :** **RUNBOOK_COMPLETE**

---

## 1. SYNTHÈSE DU RUNBOOK D'EXPLOITATION

Le runbook opérationnel d'E-ZzIO a été formalisé pour guider l'exploitation quotidienne du système sans toucher au code de production :

- **Démarrage en 1 commande :** `python web_server.py` pour lancer l'ensemble des routes API et le Web HUD sur le port 8000.
- **Preflight en 10 secondes :** Procédure de vérification rapide via `GET /health` et `GET /metrics`.
- **Guide des Incidents (Playbook) :** Comportement automatisé documenté pour 429 Quota, Fast Exit Réseau, et Bascule Groq/Ollama.
- **Séparation des Quotas :** Distinction stricte entre le quota Antigravity IDE et le runtime API Gemini.
