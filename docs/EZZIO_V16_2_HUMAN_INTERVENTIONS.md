# E-ZZIO — MATRICE DES ACTIONS HUMAINES RESTANTES (V16.2)
================================================================================
VERSION : 16.2.0
DATE    : 2026-08-22
================================================================================

| ACTION | REQUISE ? | JUSTIFICATION | AUTOMATISABLE SANS RISQUE ? | RISQUE SÉCURITÉ | COMMANDE / PROCÉDURE EXACTE | RÉSULTAT ATTENDU |
|---|---|---|---|---|---|---|
| Validation Web Tailscale Serve | OUI | Consentement propriétaire compte Tailscale (Admin Console) | NON (Nécessite session navigateur) | FAIBLE (Chiffrement TLS MagicDNS de bout en bout) | Ouvrir https://login.tailscale.com/f/serve?node=nBCi4p3Ms111CNTRL et cliquer sur 'Enable Serve' puis exécuter `G:\AI\tailscale.exe serve --bg http://127.0.0.1:3000` | Open WebUI exposé de façon chiffrée et sécurisée sur le Tailnet |
