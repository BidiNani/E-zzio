# 🏛️ E-ZZIO — RAPPORT DE GEL D'ARCHITECTURE & DOCUMENTATION UTILISATEUR OFFICIELLE

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Document créé :** [`docs/EZZIO_USER_GUIDE.md`](file:///G:/AI/E-zzio/docs/EZZIO_USER_GUIDE.md)

---

## 1. LIVRABLE MAJEUR : GUIDE UTILISATEUR OFFICIEL

Le guide complet d'utilisation [`docs/EZZIO_USER_GUIDE.md`](file:///G:/AI/E-zzio/docs/EZZIO_USER_GUIDE.md) a été rédigé en français intégral. Il structure l'expérience utilisateur sans jargon inutile :
1. **Quick Start (5 minutes pour démarrer) :** Lancement de `web_server.py` et premier message.
2. **Les 4 Interfaces :** Web HUD, Discord (`!bidi`), CLI (`ezzio_cli.py`), et API REST FastAPI.
3. **Ingestion Documentaire :** Matrice des 8 formats (`PDF`, `DOCX`, `XLSX`, `CSV`, `TSV`, `HTML`, `TXT`, `ZIP`) avec garde-fous de 50 Mo.
4. **Architecture Cloud-First Déystifiée :** Explication simple du circuit Cache -> Gemini -> Groq -> Ollama (dernier recours CPU, nominal = 0).
5. **Recherche Web & Anti-SSRF :** Moteurs Tavily/DuckDuckGo et protection des IP privées.
6. **Mémoire FTS5 & Rappel :** Fonctionnement de l'indexation SQLite WAL.
7. **Voix & Vision :** Synthèse Kokoro ONNX, reconnaissance Nemotron/Whisper et analyse multimodale Gemini.
8. **Guide de Dépannage & FAQ :** Tableaux des symptômes/actions et réponses aux 5 questions récurrentes.

---

## 2. AUDIT DE DÉCOUVRABILITÉ & INTÉGRITÉ

- **Zéro modification de code de production :** L'ensemble des 23 endpoints et du ModelRouter demeure 100% gelé et stable.
- **Découvrabilité optimale :** Chaque capacité prouvée est immédiatement repérable et utilisable depuis l'interface adéquate.
