# E-ZZIO — PLAN DE REPRISE APRÈS SINISTRE (DISASTER RECOVERY)
================================================================================
VERSION : 16.0.0
RPO     : < 1 minute (Journalisation WAL en continu)
RTO     : < 3 minutes
================================================================================

1. PROCÉDURE DE RECONSTRUCTION SUR NOUVELLE MACHINE
---------------------------------------------------
1. Cloner le dépôt :
   `git clone <repository_url> G:\AI\E-zzio`
2. Créer l'environnement virtuel Python :
   `python -m venv G:\AI\E-zzio\.venv`
   `G:\AI\E-zzio\.venv\Scripts\pip install -r requirements.txt cryptography`
3. Restaurer les secrets :
   Créer `G:\AI\E-zzio\secrets\.env` avec les clés d'API (Discord, Gemini, Groq, Tavily).
4. Restaurer la dernière sauvegarde :
   `python scripts/backup_ezzio.py`
5. Démarrer Docker et Open WebUI :
   `docker compose up -d`
6. Démarrer E-ZZIO :
   `python scripts/start_ezzio.py`
7. Vérifier la conformité :
   `python scripts/status_production.py`
