# E-ZZIO V10.0 — INSTAGRAM INGESTION TRUTH REPORT V1

---

## 1. ROOT CAUSE ANALYSÉE
- **Comportement Antérieur Défaillant :**
  Lors d'une requête sur un Reel Instagram (`https://www.instagram.com/reels/DcdsiP9iHX8/`), `UnifiedPerceptionPipeline` appelait directement `SafeWebFetcher.fetch_url()`. La requête HTTP statique obtenait une coquille JavaScript minimale (9 caractères : `Instagram`) avec un code HTTP 200. Le fetcher retournait `ok=True`, masquant l'échec d'extraction réel.

- **Correctif Appliqué :**
  1. `SocialMediaExtractor` classifie les URLs Instagram (`/p/`, `/reel/`, `/reels/`, `/tv/`) et extrait les flux via `yt-dlp` et OpenGraph.
  2. `SafeWebFetcher` intègre une garde constitutionnelle rejetant les coquilles HTML vides (`EMPTY_OR_BLOCKED_SHELL`).
  3. `UnifiedPerceptionPipeline` route les plateformes sociales vers `SocialMediaExtractor` en amont du fetcher générique.
  4. En cas de blocage d'accès (login wall, anti-bot), le pipeline retourne explicitement `ok=False` avec le statut précis (`LOGIN_REQUIRED`, `ANTI_BOT`) sans halluciner le contenu.
