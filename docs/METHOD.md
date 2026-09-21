# Methode E-ZZIO

> Ce document grave les regles de modification du projet.
> Il est verifiable par un tiers : chaque regle a une contrepartie concrete.

## Regles non-negociables

### 1. Lire avant d'ecrire

Aucune modification d'un fichier sans avoir lu son contenu **dans la session courante**.
Pas de pattern suppose. Pas de regex devinee. Lire les lignes exactes.

**Contrepartie verifiable** : un patch qui echoue doit afficher `[STOP]`, jamais `[OK]`.

### 2. Un fichier par commit

`git add <chemin>` explicite. **Jamais `git add -A`**. Jamais de wildcard dangereux.

**Contrepartie verifiable** : `git diff --cached --name-only` doit retourner 1 seul fichier
avant tout commit de modification.

### 3. Garde-fous obligatoires

Avant tout commit, verifier :

- Le nombre de fichiers modifies est exactement celui attendu
- Ruff passe sur le fichier modifie
- Les imports du fichier modifie fonctionnent
- Le fichier temporaire eventuel a ete nettoye

**Contrepartie verifiable** : si une verification echoue, `git reset --hard <snapshot>` est
affiche et le script s'arrete.

### 4. Rapports honnetes

Un rapport doit dire :

- `[OK]` **seulement** si verifie dans cette session
- `[WARN]` si non verifie ou partiellement verifie
- `[STOP]` si un garde-fou a bloque
- `[INFO]` pour une information sans enjeu

**Jamais** `[OK]` par defaut.

### 5. Rollback disponible

Tout bloc de modification doit creer un snapshot avant d'agir :

    git branch <snapshot>-<timestamp>

**Contrepartie verifiable** : le message final d'un bloc doit toujours afficher
`Rollback : git reset --hard <snapshot>`.

## Format de rapport

Tout rapport doit contenir :

1. **Contexte** : HEAD avant, branche, working tree
2. **Action** : fichier par fichier
3. **Verification** : commande + resultat attendu + resultat reel
4. **Non-verifie** : ce qui n'a PAS ete confirme
5. **Rollback** : commande exacte

## Ce qui est interdit

- Wildcard `_*.py` avec `-Recurse`
- `git add -A` dans un bloc automatise
- Commit sans verification Ruff + import
- Rapport `[OK]` sur une action non verifiee
- Pattern regex suppose sans lecture prealable
- Bloc "maitre" qui enchaine plus de 3 modifications independantes

## Historique

- 2026-09-21 : creation apres incident (commit destructeur `81798d8`)
  et une session qui a etabli ces regles par la pratique.
- Verification independante par un tiers (Claude) : commit `291592f` et 6 autres points
  confirmes factuellement.
