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

