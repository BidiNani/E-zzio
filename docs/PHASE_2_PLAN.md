# Phase 2 — Plan détaillé (autonomie coder_worker)

> **Statut** : ouvert
> **Créé** : 2026-09-22
> **Référence** : `docs/EVOLUTION_ROADMAP.md` Phase 2
> **Prérequis** : Phase 0 close, Phase 1 close (pas de migration GSD/Ralph)

---

## Objectif

**Ne plus dépendre d'Antigravity** (service externe, quota épuisé).

Rendre `coder_worker` (agent interne déjà enregistré) capable de
**porter le développement de manière autonome**, en boucle :
`plan → build → verify`.

---

## Découverte clé — Antigravity est un BRIDGE externe

**`antigravity` = IDE/agent de Google DeepMind (Gemini 3.7 Pro).**

Intégration existante dans `core/cognition/antigravity/` :

- `capabilities.py` (48 lignes) — types Python
- `client.py` (318 lignes) — client Python
- `policy.py` (83 lignes) — gouvernance locale
- `desktop_bridge.py` (217 lignes) — bridge Python
- `desktop_bridge/ezzio_antigravity_bridge.js` (298 lignes) — bridge Node.js
- `desktop_bridge/package.json` — dépendance `antigravity-client` (GitHub externe)

**Flux actuel** :
```
Python (client.py)
  → Python (desktop_bridge.py)
  → Node.js (ezzio_antigravity_bridge.js)
  → antigravity-client (GitHub: jkfujinami/antigravity-client)
  → Antigravity Desktop Language Server (Google)
```

**État actuel** : agent `antigravity_agent` enregistré dans
`core/agents/registry.py:376-391` avec `status=ERROR` et
`current_action='Standing by: BLOCKED_BY_EXTERNAL_QUOTA'`.

---

## Carte des agents

| Agent | Source | État | Rôle |
|---|---|---|---|
| `antigravity_agent` | Externe (Google) | `ERROR` / `BLOCKED` | Deep Refactor Specialist |
| `coder_worker` | Interne (`registry.py:154`) | Actif | Coder agent |
| `qa_tester` | Interne | Actif | QA |
| `researcher` | Interne | Actif | Recherche |

**Objectif Phase 2** : transférer les capacités d'`antigravity_agent` vers
`coder_worker`, en s'appuyant sur les briques existantes.

---

## Sous-tâches du roadmap (ST.1, ST.2, ST.3)

Le roadmap définit **3 sous-tâches précises** :

### ST.1 — Brancher `coder_worker` sur la boucle interne

> Brancher `coder_worker` sur GSD/Ralph Loop en interne (sous réserve Phase 1
> concluante) : E-zzio pilote sa propre boucle `plan → build → verify` sur
> son propre repo.

**Note** : Phase 1 a conclu de **ne pas migrer** vers GSD/Ralph.
La boucle doit être **construite en interne**.

### ST.2 — Implémenter le routage de fédération de modèles

> Implémenter le routage de fédération de modèles déjà conçu
> (task classifier -> ModelRouter -> CircuitBreaker, catégories
> CODING_STANDARD / COMPLEX / FAST / CONTEXT) avec les clés existantes
> (NVIDIA, OpenRouter, Groq, Gemini Pro, Ollama local).
> Le dossier de conception existe ; l'implémentation reste à faire.

**Briques existantes** :

- `core/cognition/model_router.py`
- `core/config/active_model.py`
- `core/generators/generation_router.py`
- `core/models/discovery/{gemini,litellm,ollama,openrouter}.py`
- `core/cognition/model_federation/` (base_provider.py, antigravity_provider.py)

### ST.3 — Tracer chaque bascule dans l'Audit Ledger

> Chaque bascule de provider tracée dans l'`Audit Ledger` existant
> (`audit_ledger.py`). Rien de neuf à construire, juste brancher.

**Fichier cible** : `core/security/audit_ledger.py` (à vérifier).

---

## Tâches détaillées Phase 2

### P2.1 — Audit approfondi `coder_worker`

- [ ] Localiser le code source (probablement `core/agent/` ou `core/agents/`)
- [ ] Lister les capacités actuelles
- [ ] Lister les capacités manquantes (vs `antigravity_agent`)

### P2.2 — Implémenter ST.2 (fédération de modèles)

- [ ] Auditer `core/cognition/model_federation/`
- [ ] Implémenter `task classifier`
- [ ] Brancher `ModelRouter`
- [ ] Ajouter `CircuitBreaker`
- [ ] Catégories : CODING_STANDARD / COMPLEX / FAST / CONTEXT

### P2.3 — Implémenter ST.3 (traçage Audit Ledger)

- [ ] Auditer `audit_ledger.py`
- [ ] Brancher chaque bascule de provider
- [ ] Vérifier la traçabilité bout-en-bout

### P2.4 — Implémenter ST.1 (boucle interne)

- [ ] Définir les états de la boucle (Plan, Build, Verify)
- [ ] Implémenter la transition Plan → Build
- [ ] Implémenter la transition Build → Verify
- [ ] Implémenter la boucle (Verify → Plan si échec)

### P2.5 — Décommissionner le bridge Antigravity

- [ ] Désactiver `antigravity_agent` dans `registry.py`
- [ ] Retirer `core/cognition/antigravity/` (après transfert)
- [ ] Retirer `antigravity-client` de `package.json`
- [ ] Mettre à jour la documentation

### P2.6 — Premier cas d'usage réel

- [ ] Choisir une tâche simple (ex: ajouter des tests)
- [ ] Laisser `coder_worker` la traiter seul
- [ ] Vérifier le résultat (commit, CI)

---

## Ordre d'exécution

1. **P2.1** — Audit `coder_worker` (1h)
2. **P2.2** — ST.2 : fédération de modèles (4h)
3. **P2.3** — ST.3 : traçage Audit Ledger (1h)
4. **P2.4** — ST.1 : boucle interne (4h)
5. **P2.5** — Décommissionnement Antigravity (2h)
6. **P2.6** — Premier cas d'usage (2h)

**Total estimé** : ~14h (sur plusieurs sessions)

---

## Risques

| Risque | Mitigation |
|---|---|
| Boucle infinie | Limite d'itérations + timeout |
| Régression | Verify obligatoire + rollback auto |
| Modification non tracée | Snapshot avant chaque action |
| Perte de capacités Antigravity | Transfert progressif + tests comparatifs |
| Complexité excessive | Commencer petit (1 tâche) |

---

## Définition de done

- [ ] `coder_worker` traite une tâche simple sans intervention
- [ ] Fédération de modèles opérationnelle (ST.2)
- [ ] Traçage Audit Ledger opérationnel (ST.3)
- [ ] Bridge Antigravity décommissionné
- [ ] 0 régression, 0 rollback manuel
- [ ] CI verte sur les 3 derniers runs

---

## Historique

- **2026-09-22** : création initiale (plan générique)
- **2026-09-22** : révision après découverte `antigravity` = bridge externe

