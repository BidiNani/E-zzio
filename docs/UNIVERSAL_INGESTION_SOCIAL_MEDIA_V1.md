# E-ZZIO V10.0 — UNIVERSAL SOCIAL MEDIA INGESTION V1

**Date de Référence :** 30 août 2026

---

## 1. RÈGLE CONSTITUTIONNELLE
```text
HTTP 200 ≠ INGESTION RÉUSSIE
```
Le système distingue formellement :
- `MEDIA_EXTRACTED` : Vidéo/Audio et métadonnées extraites.
- `METADATA_ONLY` : Titre, description, auteur extraits sans flux direct.
- `LOGIN_REQUIRED` : Contenu inaccessible sans compte / session.
- `PRIVATE_CONTENT` : Compte ou média privé.
- `ANTI_BOT` : Challenge Cloudflare / Captcha détecté.
- `EMPTY_OR_BLOCKED_SHELL` : Coquille JavaScript vide ou page d'accueil générique rejetée.

---

## 2. ARCHITECTURE DE ROUTAGE D'URL

```text
                    URL
                     │
                     ▼
              Universal Ingestion (UnifiedPerceptionPipeline)
                     │
               URL Classifier (SocialMediaExtractor)
                     │
        ┌────────────┼────────────┐
        │            │            │
      Generic      Social      Direct Media
       Web          Media
        │            │            │
        │       yt-dlp / API      │
        │            │            │
        └────────────┼────────────┘
                     │
             Universal Result (SocialMediaResult)
                     │
              Security Boundary (SHA-256 / [DONNÉE PASSIVE NON FIABLE])
```
