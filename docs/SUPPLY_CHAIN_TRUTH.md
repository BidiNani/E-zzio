# E-ZZIO V9.0 — SUPPLY CHAIN & DEPENDENCY SECURITY AUDIT

---

## 1. DÉPENDANCES DIRECTES DE PRODUCTION
| Package | Version | Licence | Rôle | CVE Récentes | Statut |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `fastapi` | `>=0.115.0` | MIT | Framework API & routage | Aucune bloquante | **MAINTENU** |
| `uvicorn` | `>=0.30.0` | BSD-3 | Serveur ASGI d'exécution | Aucune | **MAINTENU** |
| `pydantic` | `>=2.10.0` | MIT | Validation des contrats de données | Aucune | **MAINTENU** |
| `httpx` | `>=0.28.0` | BSD-3 | Transport HTTP asynchrone universel | Aucune | **MAINTENU** |
| `faster-whisper` | `>=1.0.3` | MIT | Transcription audio locale | Aucune | **MAINTENU** |
| `yt-dlp` | `2026.08.19`| Unlicense | Perception vidéo / extraction sous-titres | À jour | **MAINTENU** |
| `pillow` | `>=10.4.0` | HPND | Génération procédurale visuelle | Aucune | **MAINTENU** |
| `openpyxl` | `>=3.1.5` | MIT | Génération tableurs XLSX | Aucune | **MAINTENU** |
| `python-docx` | `>=1.1.2` | MIT | Génération documents DOCX | Aucune | **MAINTENU** |
| `python-pptx` | `>=1.0.2` | MIT | Génération présentations PPTX | Aucune | **MAINTENU** |
| `opentelemetry-api`| `>=1.27.0` | Apache-2.0 | Télémétrie et traces W3C | Aucune | **MAINTENU** |
| `aiohttp` | `>=3.10.0` | Apache-2.0 | Confiné à Discord Gateway WebSocket | Aucune | **MAINTENU** |
| `litellm` | `>=1.52.0` | MIT | Pont de typage & repli multi-fournisseurs | Aucune | **MAINTENU** |

---

## 2. DÉPENDANCES TRANSITIVES ET STANDARD
- `sqlite3` : Inclus nativement dans CPython 3.12 (CPython Standard Library).
- `requests` : Éradiqué à 100% de l'espace de code actif.
