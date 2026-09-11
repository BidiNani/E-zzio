"""
E-ZZIO V7.49 — Sovereign Discord Supervisor & Watchdog
Surveille l'agent Discord, gère les crashs avec redémarrage automatique et journalise le boot.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
BOOT_LOG = ROOT_DIR / "runtime" / "audit" / "discord" / "boot_history.jsonl"
BOT_SCRIPT = ROOT_DIR / "core" / "integrations" / "discord" / "discord_client.py"


def log_boot_event(event: str, details: dict = None):
    BOOT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "details": details or {}}
    import json

    with open(BOOT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_supervisor():
    print("[E-ZZIO SUPERVISOR] Démarrage du daemon de supervision V7.49...")
    log_boot_event("SUPERVISOR_START", {"status": "ONLINE"})

    restart_count = 0
    max_restarts_per_hour = 5
    window_start = time.time()

    while True:
        if time.time() - window_start > 3600:
            window_start = time.time()
            restart_count = 0

        print(f"[*] Lancement de l'Agent Discord (Tentative {restart_count + 1})...")
        log_boot_event("AGENT_LAUNCH", {"attempt": restart_count + 1})

        process = subprocess.Popen([sys.executable, str(BOT_SCRIPT)])

        # Surveillance active du processus
        while process.poll() is None:
            time.sleep(5.0)

        exit_code = process.returncode
        print(f"[!] Agent Discord arrêté (Code de sortie: {exit_code})")
        log_boot_event("AGENT_CRASH_OR_STOP", {"exit_code": exit_code})

        restart_count += 1
        if restart_count > max_restarts_per_hour:
            print("[X] ERREUR CRITIQUE : Trop de redémarrages consécutifs en moins d'une heure. Pause de sécurité.")
            log_boot_event("SUPERVISOR_LOCKOUT", {"reason": "TOO_MANY_RESTARTS"})
            time.sleep(300)  # Pause de 5 minutes
            restart_count = 0
        else:
            print("[*] Redémarrage automatique de l'agent dans 5 secondes...")
            time.sleep(5.0)


if __name__ == "__main__":
    run_supervisor()
