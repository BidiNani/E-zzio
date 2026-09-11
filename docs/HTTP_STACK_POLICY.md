# E-ZZIO V9.0 — HTTP STACK POLICY

**Date de Validation** : 29 août 2026

---

## 1. CLIENT HTTP REST CANONIQUE UNIQUE : HTTPX
- **Classe** : `httpx.AsyncClient` via [`core/utils/http_pool.py`](file:///G:/AI/E-zzio/core/utils/http_pool.py)
- **Portée** : 100% des requêtes REST sortantes du système :
  - Inférence Cloud Google (`GeminiProvider`)
  - Connecteurs SaaS directs (`GitHubProvider`, `GoogleWorkspaceProvider`, `SlackProvider`)
  - Perception Web & Ingestion (`SafeFetcher`, `YouTubeAdapter`, `Crawl4AI`)
  - Watchdog de santé (`DiscordWatchdog`)
- **Caractéristiques** : Pool de connexions partagé, keep-alive HTTP/2, timeouts stricts configurables, protection anti-SSRF.

---

## 2. CLIENT WEBSOCKET ISOLÉ : AIOHTTP
- **Classe** : `aiohttp.ClientSession` dans [`core/integrations/discord/discord_client.py`](file:///G:/AI/E-zzio/core/integrations/discord/discord_client.py)
- **Portée** : Confiné exclusivement au protocole bidirectionnel WebSocket Gateway de Discord.
- **Règle** : Aucun appel REST général ne doit être effectué via `aiohttp`.

---

## 3. PROSCRIPTION TOTALE : REQUESTS
- **Statut** : **0 import actif dans tout le code de production, optionnel et de test**.
- **Règle** : Tout nouvel import de `requests` est bloqué par le test anti-régression `tests/test_architecture_freeze.py`.
