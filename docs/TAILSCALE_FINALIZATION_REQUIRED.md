# TAILSCALE SERVE — AUTORISATION ADMINISTRATIVE REQUISE
================================================================================
STATUS : ENVIRONMENT_LIMITED (Action Administrateur Requise)
NOEUD  : bidinani (Windows)
IP     : 100.66.235.50
================================================================================

1. ÉTAT ACTUEL DU SERVICE
-------------------------
- Service Tailscale : ACTIF & OPÉRATIONNEL sur l'hôte Windows.
- Binaire : `G:\AI\tailscaled.exe` et `G:\AI\tailscale.exe`.
- IP Tailnet : `100.66.235.50`.
- Conteneur Open WebUI : ACTIF sur `http://127.0.0.1:3000`.

2. CAUSE DE LA LIMITATION ENVIRONNEMENTALE
------------------------------------------
La fonctionnalité 'Tailscale Serve' permet d'exposer de manière chiffrée (HTTPS)
l'interface locale d'Open WebUI sur le Tailnet privé. Cette fonctionnalité
est désactivée par défaut sur la console d'administration Tailscale et exige
une activation explicite par le propriétaire du compte.

3. PROCÉDURE D'ACTIVATION (Action Humaine Unique)
------------------------------------------------
1. Ouvrir le lien officiel de validation :
   👉 https://login.tailscale.com/f/serve?node=nBCi4p3Ms111CNTRL
2. Cliquer sur "Enable Serve" pour autoriser le nœud 'bidinani'.
3. Une fois validé, exécuter la commande suivante sur la machine hôte :
   `G:\AI\tailscale.exe serve --bg http://127.0.0.1:3000`

4. VÉRIFICATION POST-ACTIVATION
-------------------------------
Tester l'accès depuis n'importe quel appareil du Tailnet :
- HTTPS : `https://bidinani.tailnet-name.ts.net` (ou via l'IP 100.66.235.50)
