# E-ZZIO — MATRICE DES ACTIONS HUMAINES RESTANTES
================================================================================
VERSION : 16.0.0
================================================================================

| ACTION | REQUISE ? | JUSTIFICATION | AUTOMATISABLE SANS RISQUE ? | RISQUE SÉCURITÉ | COMMANDE / PROCÉDURE EXACTE | RÉSULTAT ATTENDU |
|---|---|---|---|---|---|---|
| Activation Tailscale Serve | OUI | Contrôle d'accès ACL & console web distante Tailscale | NON (Requiert login navigateur admin) | FAIBLE (Réseau privé chiffré) | Visiter https://login.tailscale.com/f/serve?node=nBCi4p3Ms111CNTRL puis `G:\AI\tailscale.exe serve --bg http://127.0.0.1:3000` | Open WebUI exposé en HTTPS sur le Tailnet |
| Rotation Tokens LLM / Discord | NON (Optionnel) | Clés déjà présentes et validées dans secrets/.env | NON (Responsabilité propriétaire) | CRITIQUE si exposé | Édition manuelle de `secrets/.env` | Prise en compte immédiate par GoogleIdentityBridge |
| Démarrage Quotidien | NON | Automatisé via scripts d'exploitation | OUI (`scripts/start_ezzio.py`) | NUL | `python scripts/start_ezzio.py` | Serveur E-ZZIO opérationnel sur port 8000 |
