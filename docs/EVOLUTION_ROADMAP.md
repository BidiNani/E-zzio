# E-zzio — Roadmap d'evolution (7 phases)

Statut : reference vivante
Cree : 2026-09-22
Derniere revision : 2026-09-22

---

## Preambule — Regles actives

Cette roadmap est soumise aux regles capitalisees dans `docs/METHOD.md`.
Trois regles particulierement applicables :

1. **Semantique .gitignore** (2026-09-22) :
   `dossier/` empeche Git de descendre ; `dossier/*` permet les exceptions.

2. **Verifier l'historique avant de planifier un `git mv`** (2026-09-22) :
   une tache "deplacer N fichiers" doit etre precedee d'un inventaire factuel
   croise avec l'historique Git, pas d'une premisse chiffree heritee.

3. **Toute affirmation de statut (CERTIFIED, PASS, RESOLU) doit etre
   verifiable independamment** (regle fondatrice de `docs/METHOD.md`).

Consequence pratique : **aucune phase de cette roadmap ne peut etre planifiee
sur une premisse non verifiee**. Les premisses non confirmees sont listees
explicitement en fin de document (section "Premisses a verifier").

---

## Premisses a verifier (bloquantes avant execution)

Ces affirmations sont citees dans les phases ci-dessous mais **n'ont pas
encore ete confirmees** par un inventaire factuel :

| # | Affirmation | A verifier par | Statut |
|---|---|---|---|
| P1 | GSD existe, est activement maintenu (1800+ commits annonces), licence compatible | `npx get-shit-done-cc@latest` + inspection repo upstream | Non verifie |
| P2 | Ralph Loop existe, actif, compatible avec E-zzio | recherche + inspection | Non verifie |
| P3 | Interface ezzio-desktop a 60% (Chat/Pairing/Reglages en placeholder) | inspection `ezzio-desktop/` (comptage routes + composants) | Non verifie |
| P4 | `core/models/router.py` fait 810 lignes | `(Get-Content).Count` | Non verifie |
| P5 | `registry/personality/` n'est pas charge au runtime | `grep -r "registry/personality" --include="*.py"` | Non verifie |
| P6 | `web_server.py` vs `src/ezzio/api.py` : blocage architectural cite dans TODO.md | relecture `docs/TODO.md` | Non verifie |

**Regle** : avant d'entamer une phase, verifier les premisses dont elle depend.
Documenter le resultat dans le commit qui ouvre la phase.

---

## Phase 0 — Fermer les chantiers ouverts

Rien de nouveau ne doit demarrer tant que ceci traine.

1. **Corriger le hook pre-commit** qui echoue sur
   `test_android_artifact.py::test_dist_android_apk_is_compiled_binary`
   (voir `docs/TODO.md`).
   Fix propose : `@pytest.mark.skipif(not Path("dist/android").exists(), ...)`.
   *Sans ce fix, chaque commit doc legitime force `--no-verify`, ce qui erode la methode.*

2. **Trancher `web_server.py` vs `src/ezzio/api.py`**
   (premisse P6 a verifier d'abord).
   Verdict recommande : garder `web_server.py` comme point d'entree production
   tant que `src/ezzio/api.py` (LangGraph) n'a pas de tests equivalents ;
   documenter `api.py` comme branche experimentale isolee explicitement,
   pas un remplacement silencieux.

3. **Splitter `core/models/router.py`** (premisse P4 a verifier)
   en dernier, seulement une fois 1 et 2 faits.

Note 2026-09-22 : le `git mv` des "16 fichiers CERTIFIED" precedemment
liste ici a ete **clos le 2026-09-22**. Inventaire croise avec l'historique :
les fichiers etaient deja archives (commit `27294d6`) ou supprimes
(commit `628d390`). Aucun `git mv` a faire. Le dossier
`_archive/docs_certified_20260922_112042/` reste en place comme receptacle.

---

## Phase 1 — Evaluer le remplacement de la mecanique manuelle

La session precedente a montre la limite : scripts PowerShell/Python
jetables, plusieurs tentatives echouees avant de trouver la bonne syntaxe
`.gitignore`, `--no-verify` repete.

**Etape prealable obligatoire : verifier P1 et P2** avant toute decision.

- **GSD** (`npx get-shit-done-cc@latest`) : si P1 est confirmee, evaluer
  la migration de `docs/METHOD.md` / `docs/TODO.md` vers une config GSD.
  Les 5 regles de `docs/METHOD.md` deviendraient la `CONSTITUTION.md` GSD.
- **Ralph Loop** : si P2 est confirmee, evaluer le remplacement des scripts
  `_docs_setup.py` / `_fix_github_test.py` par une boucle autonome
  plan + build + backpressure (tests + ruff).

**Decision** : migrer ou non — documentee dans un commit dedie, avec
resultat de P1/P2 en preambule.

---

## Phase 2 — Autonomie de developpement (coder_worker)

Objectif : ne plus dependre d'Antigravity (quota epuise, fiabilite douteuse).
Rendre `coder_worker/Alpha Coder` capable de porter le developpement.

1. Brancher `coder_worker` sur GSD/Ralph Loop en interne (sous reserve Phase 1
   concluante) : E-zzio pilote sa propre boucle plan -> build -> verify sur
   son propre repo.

2. Implementer le routage de federation de modeles deja concu
   (task classifier -> ModelRouter -> CircuitBreaker, categories
   CODING_STANDARD / COMPLEX / FAST / CONTEXT) avec les cles existantes
   (NVIDIA, OpenRouter, Groq, Gemini Pro, Ollama local).
   Le dossier de conception existe ; l'implementation reste a faire.

3. Chaque bascule de provider tracee dans l'`Audit Ledger` existant
   (`audit_ledger.py`). Rien de neuf a construire, juste brancher.

---

## Phase 3 — Couche "vivante" proprement dite

Trois briques a activer, dans cet ordre.

1. **Memoire continue reelle** : verifier que `Memory gateway`
   (`unified_gateway.py`, SQLite WAL+FTS5) est bien alimente a chaque mission,
   pas seulement en session courante. Un systeme "vivant" se souvient entre
   les redemarrages.

2. **Registry de personnalite actif** : `registry/personality/` existe mais
   rien ne prouve qu'il est charge au runtime (premisse P5 a verifier via
   `grep -r "registry/personality" --include="*.py"`). Brancher si absent.

3. **Missions asynchrones visibles** : le cycle
   CREATED -> QUEUED -> RUNNING -> COMPLETED doit tourner meme sans interface
   ouverte. Un agent "vivant" continue de travailler en arriere-plan,
   notifie, ne meurt pas quand la fenetre se ferme.

---

## Phase 4 — Finir l'interface

`ezzio-desktop` : Missions/Detail/Approbations/Objectifs/Sante implementes,
Chat/Pairing/Reglages en placeholder (premisse P3 a verifier).

1. **Brancher le Chat** sur les vraies routes (`chat.py`), sortir du mode
   mock (`MOCK_MODE` dans `useEzzioApi.ts`).
   *Priorite haute : sans Chat fonctionnel, "vivant" reste abstrait.*

2. **Finir le Pairing** (QR/mDNS/Tailscale deja decide) pour l'acces mobile.

3. **Completer Reglages** (LOCAL_ONLY, budget, notifications).
   Rend la gouvernance visible et controlable, pas juste theorique dans le code.

---

## Phase 5 — Capacites externes (pont vers le monde)

Reprendre la sequence actee mais jamais finalisee :
API Eigent seule -> test de statefulness -> OpenClaw -> Eigent -> E-zzio audit.

Sans ca, E-zzio reste isole. Un agent "vivant" doit pouvoir agir dehors
(fichiers, web, GitHub), pas seulement s'auditer lui-meme.

---

## Phase 6 — Boucle de gouvernance permanente

Une fois 0-5 posees, le vrai signe de vie est que le cycle se repete
sans intervention constante.

1. GSD/Ralph (sous reserve Phase 1) tournent en autonomie sur les chantiers
   restants (fichiers > 500 lignes, un par un).

2. Chaque session produit un rapport verifiable (commit + preuve), jamais
   un `[OK]` par defaut. Regle fondatrice de `docs/METHOD.md` appliquee
   en continu.

3. CodeRabbit ou equivalent sur les PR pour attraper les regressions avant
   qu'elles s'accumulent, en complement du hook pre-commit (repare en Phase 0).

---

## Ordre de priorite

Si une seule chose maintenant :

1. **Phase 0, point 1** : reparer le hook pre-commit.
2. **Phase 4, point 1** : Chat fonctionnel.

Sans ces deux elements, tout le reste est invisible — "vivant" reste un mot
dans la doc plutot qu'une experience reelle.

---

## Revision

| Date | Changement |
|---|---|
| 2026-09-22 | Creation. Phase 0 reduite a 3 items (le `git mv` des 16 fichiers est clos). Phase 1 transformee en "evaluer avant decider". Section "Premisses a verifier" ajoutee. |