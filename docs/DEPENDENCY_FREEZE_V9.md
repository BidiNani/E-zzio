# E-ZZIO V9.0 — DEPENDENCY FREEZE

**Date de Gel** : 29 aout 2026  
**Regle** : Toute nouvelle dependance dans le Core requiert une justification formelle de gain et d impact securite.

---

## 1. CRITICAL RUNTIME (INDISPENSABLE AU DEMARRAGE & PROTOCOLE)
- fastapi (>=0.115.0) : Framework de routage HTTP et validation ASGI.
- uvicorn (>=0.30.0) : Serveur d execution asynchrone HTTP.
- pydantic (>=2.10.0) : Validation stricte des contrats de donnees.
- httpx (>=0.28.0) : Transport HTTP asynchrone canonique unique.
- opentelemetry-api : Traces distribuees et observabilite W3C.
- sqlite3 (Standard Library) : Moteur de stockage persistant WAL et FTS5.

---

## 2. CAPABILITIES QUALIFIEES
- faster-whisper : Moteur de transcription vocale locale (STT).
- yt-dlp : Ingestion multimedia YouTube et extraction de sous-titres directs.
- Pillow (PIL) : Moteur deterministe d images procedurales (<30ms).
- openpyxl : Moteur deterministe de tableurs XLSX.
- python-docx : Moteur deterministe de documents DOCX.
- python-pptx : Moteur deterministe de presentations PPTX.

---

## 3. PROTOCOLE SPECIFIQUE
- aiohttp : Isole strictement pour la passerelle WebSocket Discord.

---

## 4. COMPATIBILITE & BRIDGES
- litellm : Utilise pour les schemas de typage et ponts de repli multi-fournisseurs.

---

## 5. DEPENDANCES PURGEES & INTERDITES DU RUNTIME
- requests : 0 import actif, remplace a 100% par httpx.
- langgraph : Retire et consigne en quarantaine.
