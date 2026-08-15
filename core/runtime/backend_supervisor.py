"""
E-ZZIO V7.54.2 — Backend API Supervisor (Persistent & Observable)
Surveille web_server.py, capture les flux, et maintient un état de crash persistant.
"""
import time
import subprocess
import sys
import signal
import json
import threading
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
AUDIT_FILE = ROOT_DIR / "runtime" / "audit" / "system" / "boot_chain.jsonl"
STATE_FILE = ROOT_DIR / "runtime" / "state" / "backend_crash_state.json"
LOG_FILE = ROOT_DIR / "runtime" / "logs" / "backend" / "server.log"
PYTHON_EXE = str(ROOT_DIR / ".venv" / "Scripts" / "python.exe")

CRASH_LIMIT = 5
TIME_WINDOW_SEC = 600

process = None

def load_crash_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                if data.get("locked", False):
                    print("[X] COUPE-CIRCUIT ACTIF : Le système est verrouillé suite à de multiples crashs.")
                    sys.exit(1)
                return data.get("crashes", [])
        except json.JSONDecodeError:
            return []
    return []

def save_crash_state(crashes, locked=False):
    with open(STATE_FILE, "w") as f:
        json.dump({"crashes": crashes, "locked": locked}, f, indent=2)

def log_event(event, status, details=None):
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
        "details": details or {}
    }
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def stream_logger(pipe, prefix=""):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for line in iter(pipe.readline, ''):
            msg = f"{datetime.now(timezone.utc).isoformat()} {prefix} {line}"
            f.write(msg)
            sys.stdout.write(msg)

def graceful_shutdown(signum, frame):
    log_event("BACKEND_SHUTDOWN", "INITIATED", {"signal": signum})
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

def run_supervisor():
    global process
    crash_history = load_crash_state()
    log_event("BACKEND_SUPERVISOR_START", "OK")
    
    while True:
        log_event("BACKEND_PROCESS", "STARTING")
        process = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "web_server:app", "--host", "127.0.0.1", "--port", "8001"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Thread pour vider stdout vers le fichier log en temps réel
        t = threading.Thread(target=stream_logger, args=(process.stdout, "[API]"))
        t.daemon = True
        t.start()
        
        process.wait()
        exit_code = process.returncode
        now = time.time()
        
        crash_history.append(now)
        crash_history = [t for t in crash_history if now - t <= TIME_WINDOW_SEC]
        
        log_event("BACKEND_CRASH", "DETECTED", {"exit_code": exit_code})
        print(f"[!] Crash détecté (Code: {exit_code}). Sauvegarde de l'état...")
        
        if len(crash_history) >= CRASH_LIMIT:
            save_crash_state(crash_history, locked=True)
            log_event("CIRCUIT_BREAKER", "TRIPPED", {"reason": "TOO_MANY_CRASHES"})
            print("[X] VERROUILLAGE PERSISTANT : Limite de crash atteinte.")
            sys.exit(1)
            
        save_crash_state(crash_history, locked=False)
        time.sleep(5)

if __name__ == "__main__":
    run_supervisor()
