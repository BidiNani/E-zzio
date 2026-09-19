# Archive PowerShell - 20260919_115204

Ce dossier contient 107 fichiers PowerShell archives lors des lots 1 a 5b du nettoyage E-zzio.

## Conventions de nommage

- tools_scripts_infra_<nom>.ps1 : provenance tools/scripts_infra/ (lot 1)
- tools_<nom>.ps1              : provenance tools/ (lots 1 et 5)
- scripts_<nom>.ps1            : provenance scripts/ (lots 2, 3, 4b)

## Lots d'archivage

| Lot | Contenu |
|---|---|
| 1   | tools/scripts_infra + tools/ + core/evolution_* |
| 2   | scripts/ lot 1 (tests, audits, monitoring, helpers PC) |
| 3   | scripts/ lot 2 (filtre strict + liste blanche) |
| 4b  | scripts/ orphelins par reference (ref uniquement dans _archive/ ou docs) |
| 5   | tools/ racine + tools/scripts_infra restants |

## Restauration

    git mv _archive/ps_versions/scripts_<nom>.ps1 scripts/<nom>.ps1

## Raison des archivages

Tous ces scripts etaient orphelins : aucune reference statique detectee par git grep (ni par nom de fichier, ni par nom sans extension, ni dans les sources Python/JSON/YAML). Ce sont pour l'essentiel :

- des scripts de migration/diagnostic/reparation one-shot
- des tests manuels (*_test.ps1)
- du monitoring mort (*_status.ps1, *_once.ps1, watchdog_*)
- des helpers PC obsoletes

Les raccourcis utilisateur (open_*, start_*, stop_*, show_*) et les scripts actifs references (forge_*, ci_check.ps1, routes_audit.ps1) ont ete conserves en place.
