# E-ZZIO — OPERATIONAL GOVERNANCE & GOLDEN RULES

=========================================================
## WORKPLACE PRESERVATION & GIT SAFETY
=========================================================

Aucune opération destructive sur le working tree n'est autorisée sans snapshot préalable.

Interditions formelles :
- `git checkout -f`
- `git reset --hard`
- `git clean`
- `git filter-repo`
- `git filter-branch`

Toute modification validée doit être :
1. commitée ;
2. OU exportée dans un snapshot hashé ;
3. OU sauvegardée dans un artefact de récupération vérifié.
