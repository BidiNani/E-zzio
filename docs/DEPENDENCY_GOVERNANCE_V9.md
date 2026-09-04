# E-ZZIO V9.0 — DEPENDENCY GOVERNANCE

---

## 1. MATRICE DE GOUVERNANCE DES PACKAGES

| Package | Version | Scope | Catégorie | Rôle Exact | Licence | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `fastapi` | `>=0.115.0` | Direct | `CORE` | Framework de routage HTTP ASGI | MIT | **MAINTENU** |
| `uvicorn` | `>=0.30.0` | Direct | `CORE` | Serveur d'exécution asynchrone | BSD-3 | **MAINTENU** |
| `pydantic` | `>=2.10.0` | Direct | `CORE` | Validation des contrats de données | MIT | **MAINTENU** |
| `httpx` | `>=0.28.0` | Direct | `CORE` | Transport HTTP REST universel | BSD-3 | **MAINTENU** |
| `opentelemetry-api`| `>=1.27.0` | Direct | `CORE` | Télémétrie W3C et traces | Apache-2.0 | **MAINTENU** |
| `faster-whisper` | `>=1.0.3` | Direct | `CAPABILITY` | STT local audio | MIT | **MAINTENU** |
| `yt-dlp` | `2026.08.19`| Direct | `CAPABILITY` | Extraction métadonnées/sous-titres | Unlicense | **MAINTENU** |
| `Pillow` | `>=10.4.0` | Direct | `CAPABILITY` | Générateur visuel déterministe | HPND | **MAINTENU** |
| `openpyxl` | `>=3.1.5` | Direct | `CAPABILITY` | Tableurs XLSX déterministes | MIT | **MAINTENU** |
| `python-docx` | `>=1.1.2` | Direct | `CAPABILITY` | Documents DOCX déterministes | MIT | **MAINTENU** |
| `python-pptx` | `>=1.0.2` | Direct | `CAPABILITY` | Présentations PPTX déterministes | MIT | **MAINTENU** |
| `aiohttp` | `>=3.10.0` | Direct | `PROTOCOL` | WebSocket Gateway Discord | Apache-2.0 | **MAINTENU** |
| `litellm` | `>=1.52.0` | Direct | `BRIDGE` | Schémas types & repli multi-cloud | MIT | **MAINTENU** |

---

## 2. RÈGLE D'INTRODUCTION D'UNE NOUVELLE DÉPENDANCE
Toute nouvelle dépendance doit obligatoirement satisfaire à l'équation de valeur nette :
$$\text{Valeur Nette} = (\text{Gain Fonctionnel} + \text{Gain Sécurité} + \text{Gain Performance} + \text{Réduction Maintenance}) - (\text{Complexité} + \text{Poids} + \text{Surface d'Attaque}) > 0$$
