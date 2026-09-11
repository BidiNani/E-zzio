# Hermes — Agents codeurs E-zZIO

## Lancer un agent

```powershell
& G:\AI\E-zZIO\scripts\hermes-architect.ps1 "Conçois le module de mémoire locale E-zZIO."
& G:\AI\E-zZIO\scripts\hermes-lua-godot.ps1 "Analyse les scripts Lua de ce dossier et corrige les erreurs."
& G:\AI\E-zZIO\scripts\hermes-powershell.ps1 "Crée un script sûr de sauvegarde des configurations Hermes."
& G:\AI\E-zZIO\scripts\hermes-review.ps1 "Relis les fichiers modifiés et propose un patch minimal."
& G:\AI\E-zZIO\scripts\hermes-debug.ps1 "Diagnostique l'erreur actuelle à partir des logs."
```

## Réduire les tokens

- Une session Hermes par sujet.
- Demander une réponse courte et un patch minimal.
- Demander d'abord un plan, puis autoriser les changements.
- Lire uniquement les fichiers concernés.
- Utiliser le modèle local de compression déjà configuré.
- Éviter browser/computer-use sauf nécessité réelle.
- Ne jamais transmettre les contenus de `.env` au modèle.
