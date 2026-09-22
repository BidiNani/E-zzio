# Antigravity — DÉCOMMISSIONNÉ

**Date** : 2026-09-22
**Raison** : Ne plus dépendre d'un service externe (Google Antigravity, quota épuisé).

## Contenu archivé

- `capabilities.py` (48 lignes) — types Python
- `client.py` (318 lignes) — client Python
- `policy.py` (83 lignes) — gouvernance locale
- `desktop_bridge.py` (217 lignes) — bridge Python
- `desktop_bridge/ezzio_antigravity_bridge.js` (298 lignes) — bridge Node.js
- `desktop_bridge/package.json` — dépendance `antigravity-client`

## Remplacement

Le rôle d'`antigravity_agent` (Deep Refactor Specialist) est transféré à
`coder_worker` (agent interne).

- Protocole capturé : `core/coding/protocol.py`
- Gouvernance capturée : `core/coding/policy.py`

Voir `docs/PHASE_2_PLAN.md` pour les détails du transfert.

## Référence Git

Commit de décommissionnement : voir `git log` (à compléter après push).