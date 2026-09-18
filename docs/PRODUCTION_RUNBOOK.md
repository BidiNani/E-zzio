# E-ZZIO — PRODUCTION RUNBOOK
================================================================================
VERSION : 13.0.0
ENV     : WINDOWS (G:\AI\E-zzio)
================================================================================

1. COMMANDES D'EXPLOITATION
---------------------------
- Démarrage complet :
  `python scripts/start_ezzio.py`
  (ou `powershell start_docker.ps1` pour l'interface Open WebUI)

- Arrêt complet :
  `python scripts/stop_ezzio.py`

- État du système et des composants :
  `python scripts/status_production.py`

- Surveillance et auto-guérison :
  `python scripts/watchdog_ezzio.py`

- Sauvegarde non destructive :
  `python scripts/backup_ezzio.py`

2. POINTS D'ACCÈS DU PRODUIT
----------------------------
- Open WebUI Dashboard : http://127.0.0.1:3000
- E-ZZIO REST API      : http://127.0.0.1:8000
- E-ZZIO Live HUD      : http://127.0.0.1:8000/hud
- Tailscale IP locale  : 100.66.235.50 (Nœud: bidinani)
- Discord Bot          : E-zzio (ID: 1517996783324762132)

3. GESTION DES SECRETS & SÉCURITÉ
---------------------------------
- Les tokens et clés API résident exclusivement dans `secrets/.env` et `.env`.
- Aucun secret n'est exposé dans les logs, traces, artefacts ou sorties HTTP.
- Le moteur de sécurité (PolicyEngine, CapabilityGuard, ConstitutionGuard, PromptGuard) est actif en mode fail-closed.

4. PROCÉDURE DE REPRISE APRÈS INCIDENT
--------------------------------------
1. Vérifier l'état avec `python scripts/status_production.py`.
2. Relancer le serveur avec `python scripts/start_ezzio.py`.
3. Les tâches interrompues reprennent automatiquement leur checkpoint sous SQLite WAL (`agent_task_checkpoints`).
4. L'historique et la mémoire cognitive FTS5 sont préservés à 100%.
