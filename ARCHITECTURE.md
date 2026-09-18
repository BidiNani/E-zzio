# E-ZZIO — Architecture

## Vue d'ensemble

- **Frontend** : React 18 + TypeScript + Vite 5 → http://localhost:1420
- **Backend**  : FastAPI + Uvicorn → http://127.0.0.1:8001

## Frontend

- State : hooks custom
- Polling : `usePolling` (visibility-aware)
- Tests : Vitest (unit) + Playwright (e2e)

### Hooks critiques

| Hook | Rôle | Fréquence |
|---|---|---|
| `usePolling` | Polling générique, pause si onglet caché | n/a |
| `useEzzioApi` | Client HTTP mémoïsé | n/a |
| `useBackendStatus` | Statut `/health` | 30s |
| `useAccounts` | Comptes + watcher OAuth | 60s |

### Règle d'or

Tout hook qui retourne un objet DOIT utiliser `useMemo`. Sinon boucle infinie dans les `useEffect` qui en dépendent. Test anti-régression : `src/test/useEzzioApi.test.ts`.

## Backend

- Routes : `/health`, `/master/*`, `/api/*`, `/perception/*`
- Debug : `GET /api/_routes`
- Rate limit : 600 req/min, exemptions `/health` + `/master/*`

### Watchdog

Tâche planifiée Windows `E-ZZIO-Watchdog` : relance uvicorn si `/health` KO 3 fois.

## Métriques

| Métrique | Avant | Après |
|---|---|---|
| Logs / 60s (1 onglet) | 3182 | 8 |
| Tests backend | — | 869 |
| Tests frontend | 0 | 6 |
