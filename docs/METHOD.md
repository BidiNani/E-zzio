# Methode E-ZZIO

## Regles de modification (non-negociables)

1. **Lire avant d'ecrire** - jamais de patch sur un fichier non lu dans la session en cours
2. **Un chantier logique par commit** - chaque fichier modifie doit etre liste et justifie dans le message ; jamais de `git add -A` sans revue du diff complet
3. **Garde-fous qui bloquent vraiment** - un warning n'est pas un blocage ; un garde-fou qui n'empeche pas l'action n'est pas un garde-fou
4. **Rapports honnetes** - `[WARN]`/`[STOP]` si non verifie, jamais `[OK]` par defaut
5. **Rollback disponible** - snapshot ou commit de securite avant toute modification risquee

## Format de rapport obligatoire

Tout rapport de session doit contenir :

- Commit hash
- Fichier + ligne exacte concernee
- Commande de reproduction (copiable-collable)
- Resultat attendu, pas juste "OK"
- Section explicite : **ce qui n'a PAS ete verifie**

## Verification tierce

Toute affirmation de statut (CERTIFIED, PASS, RESOLU) doit etre verifiable independamment par relecture du commit et execution de la commande de reproduction - sans ca, elle reste `[NON VERIFIE]`.

## Historique

- 2026-09-21 : creation initiale (commits `64417d3` et `5e91e47`).
- 2026-09-21 : reformulation de la regle 2 apres retour de Claude : la regle "1 fichier = 1 commit" etait trop stricte et aurait bloque la purge legitime `2b2f308` (35 fichiers).

## Semantique .gitignore (regle apprise 2026-09-22)

- `dossier/` -> ignore le dossier ET empeche Git de descendre.
  Les regles suivantes ne s'appliquent PAS a l'interieur.
- `dossier/*` -> ignore le contenu MAIS Git descend pour evaluer
  les sous-regles. Permet les exceptions `!dossier/sous-dossier/`.
- Un doublon de regle en fin de fichier peut annuler une exception
  placee au debut. Toujours verifier l'unicite.
- Verification obligatoire : `git check-ignore -v <chemin>`
  (pas seulement `git status --porcelain`).


## Verifier l'historique avant de planifier un git mv (regle apprise 2026-09-22)

Une tache "deplacer N fichiers de X vers Y" doit etre precedee d'une
verification factuelle sur l'etat courant, pas sur une premisse chiffree
heritee d'une session precedente.

- Etape 1 : inventorier les fichiers candidats (`Get-ChildItem`, `git ls-files`)
- Etape 2 : croiser avec l'historique (`git log --diff-filter=D --name-only`)
- Etape 3 : seulement si les deux concordent, planifier le `git mv`

Cas vecu : une tache "git mv de 16 fichiers CERTIFIED" a ete planifiee,
puis abandonnee apres inventaire — les fichiers avaient deja ete archives
(commit `27294d6`) ou supprimes (commit `628d390`) dans des sessions
anterieures. Le chiffre "16" n'etait verifie par aucune source.




## Hooks, pytest et surcharges (regles apprises 2026-09-22)

### A. `pytest -m` en ligne de commande ecrase `addopts`

Dans `pyproject.toml` :
```
addopts = "-q --strict-markers --tb=short -m 'not visual and not hardware'"
```

Un appel `pytest -m "not slow"` remplace entierement le `-m`
d'`addopts`. Le filtre `not visual and not hardware` est alors
silencieusement desactive : les tests marques `hardware` sont collectes
et executes, ce qui casse la suite si le materiel est absent.

**Regle** : quand un hook ou un script passe `-m`, il doit inclure
**tous** les filtres necessaires :

```
pytest -m "not slow and not visual and not hardware"
```

**Contrepartie verifiable** : `git commit` doit afficher
`[pre-commit] OK` (derniere ligne du hook) et non s'arreter sur un
test `hardware`.

### B. Verifier `core.hooksPath` avant de diagnostiquer un hook

Le dossier `.git/hooks/` peut etre vide et le hook actif se trouver
ailleurs si `core.hooksPath` est configure :

```
git config --get core.hooksPath
# .githooks   (au lieu du defaut .git/hooks)
```

**Regle** : avant tout diagnostic de hook, faire :

```
git config --get core.hooksPath
git ls-files ".githooks/"
```

Ne pas supposer `.git/hooks/pre-commit` ni `.pre-commit-config.yaml`
comme source unique. Un `.githooks/` versionne est une source legitime.

**Contrepartie verifiable** : `git ls-files ".githooks/"` retourne
les scripts reellement actifs.

### C. Verifier que `git`, `pytest`, `ruff` sont des executables

Une fonction PowerShell du profil peut surcharger `git commit` et
lancer des commandes avant `git.exe`. Le symptome : un message
`[pre-commit]` qui n'apparait ni dans `.git/hooks/` ni dans
`.githooks/` ni dans `.pre-commit-config.yaml`.

**Regle** : avant tout diagnostic de hook, faire :

```
Get-Command git, pytest, ruff | Select Name, CommandType, Source
```

Tous doivent etre `Application` (ou `ExternalScript`). Si l'un est
`Function`, c'est une surcharge PowerShell.

**Contrepartie verifiable** : `(Get-Command git).CommandType -eq
"Application"` est `True`.


## Règle — Édition de fichiers Markdown contenant de l'Unicode

**Contexte** : observé 2 fois dans les sessions de nettoyage E-zzio.
Utiliser `String.Replace` avec des chaînes littérales longues sur des
fichiers Markdown contenant des emojis (`✅`, `❌`, `⚠`) provoque du
mojibake ou échoue silencieusement.

**Règle** : pour les fichiers Markdown contenant de l'Unicode, utiliser :

1. **Splice par index** (recommandé) : lire le fichier ligne par ligne,
   remplacer les lignes par index (`$before + $new + $after`), réécrire.
   Robuste à tout caractère Unicode.

2. **OU** `-replace` avec regex explicitement Unicode.

**Ne jamais** utiliser `String.Replace` avec une chaîne littérale longue
sur un fichier Markdown.

**Vérification** : après édition, lire le fichier en UTF-8 strict
(`[System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)`)
et vérifier la présence des codepoints attendus (U+2705, U+274C, U+26A0),
pas via la console PowerShell qui peut afficher en CP1252.

**Note console** : `git diff` et la console PowerShell peuvent afficher du
"mojibake" (`Ô£à`, `ÔØî`) alors que le fichier est correct en UTF-8. Toujours
vérifier avec `[System.IO.File]::ReadAllText(..., UTF8)` avant de corriger.

## Règle — Vérification avant d'écrire un test

**Contexte** : observé 2 fois dans la session V4 (core/telemetry et tests unit).

**Règle 1 — Vérifier le conflit module/package**

Avant d'écrire un test pour core/X.py, vérifier qu'il n'existe pas un
package core/X/ qui masquerait le fichier :

    Test-Path "core\X.py"              # -> fichier
    Test-Path "core\X\__init__.py"     # -> package

Si les deux existent, Python charge le package (le dossier gagne).
Dans ce cas, soit renommer le fichier (X_events.py), soit tester le
package, soit supprimer le code mort.

**Règle 2 — Jamais 'l' comme variable de comprehension**

Ruff E741 interdit 'l' (ambigu avec 1). Utiliser 'line', 'item', 'entry'.

    # Interdit
    lines = [l for l in content.split("\n") if l]

    # Correct
    lines = [line for line in content.split("\n") if line]

**Règle 3 — Lire le code avant d'écrire un test**

Les tests V3-b2 (human_loop) et V3-b3 (omni_brain) ont échoué sur des
suppositions : event_type/data au lieu de type/payload, write_json_event
supposé créer le dossier (il ne le crée pas). Toujours lire 100-200 lignes
de la fonction cible avant d'écrire un test qui asserte sur sa structure.

**Règle 4 — Exclure les fonctions fail-closed des tests unitaires**

Les fonctions qui appellent un mécanisme de sécurité en cascade
(CanonicalIdentity, runtime/identity/persona.hash) sont des tests
d'intégration, pas unitaires. Les mettre en TODO, pas en test.

## Règle — asyncio : utiliser get_running_loop(), pas get_event_loop()

**Contexte** : découvert dans signal_bus.py (session V5-d).

syncio.get_event_loop() est **deprecated depuis Python 3.12** et
**crashe** (RuntimeError) en dehors d'un contexte async quand aucune
loop n'est enregistrée. Il émet aussi un DeprecationWarning.

**Règle** : ne jamais utiliser syncio.get_event_loop().

**Utiliser** :

    # Pour récupérer la loop courante (obligatoirement active)
    try:
        loop = asyncio.get_running_loop()
        # ...
    except RuntimeError:
        # pas de loop active -> fallback
        pass

    # Pour un timestamp safe depuis un dataclass
    def _now_timestamp() -> float:
        try:
            return asyncio.get_running_loop().time()
        except RuntimeError:
            return 0.0

**Ne pas utiliser** :

    # Deprecated et dangereux hors contexte async
    loop = asyncio.get_event_loop()

**Contexte** : get_running_loop() lève RuntimeError si pas de loop,
c'est explicite. get_event_loop() crée implicitement une loop ou
warning.


## Règle — skipif pour les tests OS-specific

**Contexte** : découvert en session V5-fix (commit 1d76c10). Un test qui mock
ctypes.windll a cassé la CI Linux car ctypes.windll n'existe pas sur Linux.

monkeypatch.setattr(ctypes, "windll", mock) lance AttributeError sur Linux
car l'attribut n'existe pas.

**Règle** : tout test qui dépend d'une API OS-specific (Windows, macOS, Linux)
DOIT être décoré avec @pytest.mark.skipif.

**Utiliser** :

    import ctypes

    @pytest.mark.skipif(
        not hasattr(ctypes, "windll"),
        reason="DPAPI Windows only — ctypes.windll absent sur cette plateforme",
    )
    def test_dpapi_windows_only():
        monkeypatch.setattr(ctypes, "windll", mock, raising=False)
        ...

**Ne pas utiliser** :

    # Casse sur Linux/macOS
    def test_dpapi():
        monkeypatch.setattr(ctypes, "windll", mock)  # AttributeError sur Linux

**Patterns courants** :

    # Windows-only
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")

    # Linux-only
    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")

    # Attribut OS-specific
    @pytest.mark.skipif(not hasattr(ctypes, "windll"), reason="Windows only")

**Toujours ajouter aising=False** dans monkeypatch.setattr pour les
attributs qui peuvent ne pas exister sur la plateforme de CI.


---

## Règle — `git check-ignore` et exceptions `!`

**Contexte** : découvert en session V6-fix (commit `13a18ee`). Le test
`if (git check-ignore ...) { fail }` produit un **faux positif** quand la
dernière règle qui matche est une **exception `!`**.

**Comportement Git** : `git check-ignore -v <path>` retourne exit code **0**
même quand la dernière règle est une exception `!`, MAIS la sortie commence
par `.gitignore:<N>:!` au lieu de `.gitignore:<N>:`.

**Preuve** :
    $ git check-ignore -v "_archive/README.md"
    .gitignore:110:!_archive/README.md  _archive/README.md  (exit=0)
    $ echo $?
    0

Alors que le fichier **n'est pas ignoré** (il peut être `git add`).

**Règle** : ne JAMAIS utiliser `git check-ignore` **seul** (avec exit code)
pour détecter si un fichier est ignoré. **Toujours vérifier** :

1. Le **code de sortie** (0 = match, 1 = pas de match)
2. **ET** le **contenu** de la ligne (commence par `!` = exception = NON ignoré)

**Utiliser** :
    $out = git check-ignore -v "chemin" 2>&1
    $exitCode = $LASTEXITCODE
    $isIgnored = ($exitCode -eq 0) -and (-not ($out -match ':\s*!'))

    if ($isIgnored) {
        Write-Host "IGNORÉ : $out"
    } else {
        Write-Host "NON IGNORÉ"
    }

**Ne pas utiliser** :
    if (git check-ignore -v "chemin") { ... }  # faux positif si exception !

**Alternative robuste** : utiliser `git ls-files --error-unmatch <path>` :
- exit 0 = fichier suivi
- exit 1 = fichier non suivi (donc ajoutable)


---

## Règle — Un commit = une intention

**Contexte** : découvert en session V6-fix (commit `13a18ee`). Un commit
intitulé `test(secrets_vault): +6 tests` a inclus **11 renommages**
`docs/ → _archive/` parce qu'ils étaient **déjà dans l'index** (staged par
`git mv`).

**Cause** : `git mv` met les fichiers en **stage automatiquement**. Un
`git commit` ultérieur (même avec un message ciblé) committe **tout** ce qui
est staged.

**Preuve** :
    [main 13a18ee] test(secrets_vault): +6 tests fallback crypto
     rename {docs => _archive/docs_certified_20260922_112042}/V9.4_SHOWCASE.md (100%)
     ... (11 renommages non mentionnés dans le message)

**Règle** : AVANT tout `git commit`, **toujours vérifier** ce qui est staged :

    git diff --cached --stat
    git status --short

**Utiliser** :
    # 1. Vérifier ce qui est staged
    git status --short
    # 2. Si trop de choses : unstage ce qu'on ne veut pas
    git reset HEAD -- <fichiers à ne pas committer>
    # 3. Committer
    git commit -m "message ciblé"

**OU** (pour des cas simples) : `git commit -m "..." -- <fichier1> <fichier2>`
mais ce n'est **pas recommandé** pour les renommages (`git mv`).

**Ne pas utiliser** :
    git mv doc1.md archive/
    git mv doc2.md archive/
    git add test.py
    git commit -m "test: ajout tests"  # inclut les 2 renommages !

**Si un commit contient déjà 2 intentions** : ne **pas** réécrire l'historique
(risqué sur branche poussée). Documenter dans le prochain commit ou dans
`TODO.md`.

**Règle METHOD.md associée** : vérifier `git diff --cached --stat` avant
chaque `git commit`. Si plus d'une intention → séparer en commits distincts.

---

## Règle — Tester la CI avant de clore une phase

**Contexte** : découvert en session V6-fix (Phase 0 close). Le roadmap dit
« Rien de nouveau ne doit demarrer tant que ceci traine ». Fermer une
phase sans verifier la CI revient a cocher une case sans preuve.

**Regle** : avant de marquer une phase du roadmap comme **close** :

1. **Working tree PROPRE** (`git status --porcelain` vide)
2. **Commits pousses** (`git rev-parse HEAD` == `git rev-parse origin/main`)
3. **CI verte sur les 3 derniers runs** (`gh run list --limit 3`)
4. **Aucune branche snapshot residuelle** (`git branch` = `main` uniquement)
5. **Documentation a jour** (METHOD.md + TODO.md)

**Sans ces 5 preuves, la phase n'est PAS close.** Cocher une case sans
preuve est exactement le travers que le projet combat (KNOWN_FALSE_CLAIMS.md).

**Preuve a consigner** : le commit qui ferme la phase doit contenir dans son
message la **reference aux runs CI verts** (SHA + date).

**Exemple** :
    docs(roadmap): close Phase 0 — CI verte (c5f54bf, f308cee, c1444af)

