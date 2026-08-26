"""
E-ZZIO V7.50 — Discord Process Watcher
Surveille l'exécution de Discord.exe pour lancer automatiquement l'agent souverain.
"""

import time
import psutil
import subprocess
from pathlib import Path


def watch_discord():
    print("[E-ZZIO WATCHER] Surveillance de Discord.exe active...")
    started = False
    script_path = Path(r"G:\AI\E-zzio\runtime\launcher\start_discord_agent.ps1")

    while True:
        try:
            discord_running = any(p.info["name"].lower() == "discord.exe" for p in psutil.process_iter(["name"]))

            if discord_running and not started:
                print("[*] Discord.exe détecté. Lancement de l'agent E-ZZIO...")
                subprocess.Popen(["pwsh.exe", "-File", str(script_path)])
                started = True

            if not discord_running:
                started = False
        except Exception as e:
            print(f"[!] Erreur watcher: {e}")

        time.sleep(5)


if __name__ == "__main__":
    watch_discord()
