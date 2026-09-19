# Contribuer à E-ZZIO

## Setup

### Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q

### Frontend
npm install --legacy-peer-deps
npm test
npm run build

## Règles

### Frontend
- JAMAIS de `setInterval` brut sans `usePolling`
- TOUJOURS `useMemo` sur le return d'un hook objet
- TOUJOURS des tests pour les hooks critiques

### Backend
- TOUJOURS des modèles Pydantic pour les payloads
- JAMAIS de secrets hardcodés (`os.getenv`)

## CI

GitHub Actions lance `pytest` + `tsc --noEmit` + `vitest` + `build` sur chaque push.
