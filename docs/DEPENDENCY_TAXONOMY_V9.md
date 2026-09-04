# E-ZZIO V9.0 — DEPENDENCY TAXONOMY

Ce document établit la séparation stricte entre les packages externes tiers et les modules de la bibliothèque standard Python.

---

## 1. PACKAGES EXTERNES TIERS (PYPI / VENDOR)
- **Serveur & HTTP API** : `fastapi`, `uvicorn`, `pydantic`, `httpx`
- **Capacités Spécialisées** : `faster-whisper`, `yt-dlp`, `Pillow`, `openpyxl`, `python-docx`, `python-pptx`
- **Observabilité** : `opentelemetry-api`
- **Protocoles Spécifiques** : `aiohttp` (WebSockets Discord)
- **Ponts & Typage** : `litellm` (Schémas et compatibilité de repli multi-fournisseurs)

---

## 2. BIBLIOTHÈQUE STANDARD PYTHON (STANDARD LIBRARY)
Les modules suivants font partie intégrante de Python 3.12 et ne constituent pas des dépendances externes supplémentaires :
- `sqlite3` : Moteur SQL persistant WAL et FTS5 (intégré nativement à CPython).
- `asyncio`, `pathlib`, `json`, `hashlib`, `re`, `os`, `sys`, `shutil`, `typing`, `time`, `dataclasses`.

---

## 3. DÉPENDANCES PROSCRITES & ÉRADIQUÉES DU RUNTIME
- `requests` : Éradiqué (0 appel actif).
- `langgraph` : Quarantaine confirmée.
