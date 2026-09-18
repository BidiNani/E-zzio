# E-zzio — Endpoints backend

Base URL : `http://127.0.0.1:8001`

## Santé

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Statut global (`{ok, status, service}`) |
| GET | `/master/providers/health` | État des providers LLM (ollama, gemini, groq, antigravity) |
| GET | `/master/system/diagnostics` | Diagnostics système (audit ledger, kill switch) |
| GET | `/api/health/full` | Health complet détaillé |

## Recherche web (multi-provider)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/web-search` | Recherche (`{query, provider, max_results, model?}`) |
| GET | `/api/web-search/cache/stats` | Statistiques du cache LRU |

**Providers supportés** : `brave`, `tavily`, `duckduckgo`, `serpdive`, `google`

**Cache** : LRU 128 entrées, TTL 300s (gain ~95% sur requêtes répétées)

## Comptes OAuth

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/accounts/providers` | Liste des 7 providers + statut de connexion |
| GET | `/api/accounts/list` | Comptes actuellement connectés |
| POST | `/api/accounts/connect/{provider_id}` | Démarre le flow OAuth |
| GET | `/api/accounts/callback/{provider_id}` | Callback OAuth |
| DELETE | `/api/accounts/{provider_id}` | Déconnecte |

## Missions & approbations

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/master/missions` | Liste des missions |
| GET | `/master/approvals/pending` | Approbations en attente |
| POST | `/master/approvals/{id}/decide` | Décision (`{decision, decided_by}`) |

## Mémoire

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/memory/recent?limit=30` | Mémoire récente |
| POST | `/memory/search` | Recherche (`{query, limit}`) |

## Chat

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/master/chat` | Chat LLM (`{text, session_id}`) |

---

*Dernière mise à jour : session d''optimisation complète (cache LRU, ErrorBoundary, AbortController, thèmes).*