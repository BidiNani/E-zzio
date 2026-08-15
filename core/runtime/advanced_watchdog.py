# ==============================================================================
# E-ZZIO — Advanced Multi-Signal Watchdog (Hardened v2.0)
# File: G:\AI\E-zzio\core\runtime\advanced_watchdog.py
# ==============================================================================
import json
import time
import urllib.request
from pathlib import Path
import psutil

ROOT_PATH = Path(r"G:\AI\E-zzio")
STATE_DIR = ROOT_PATH / "runtime" / "state" / "backend"
PID_FILE = STATE_DIR / "pid.json"
HEALTH_FILE = STATE_DIR / "health.json"

def diagnose_runtime_state() -> dict:
    checks = {
        "pid": False,
        "cmdline": False,
        "tcp": False,
        "http": False,
        "semantic": False
    }
    
    diagnosis = {
        "status": "UNKNOWN",
        "reason": "NONE",
        "checks": checks
    }

    if not PID_FILE.exists():
        diagnosis["status"] = "DEAD"
        diagnosis["reason"] = "MISSING_PID_MANIFEST"
        return diagnosis

    try:
        manifest = json.loads(PID_FILE.read_text(encoding="utf-8"))
        pid = manifest.get("pid")
    except Exception as e:
        diagnosis["status"] = "CORRUPTED"
        diagnosis["reason"] = f"INVALID_PID_JSON: {e}"
        return diagnosis

    if not isinstance(pid, int):
        diagnosis["status"] = "CORRUPTED"
        diagnosis["reason"] = f"INVALID_PID_TYPE_{type(pid).__name__}"
        return diagnosis

    if not psutil.pid_exists(pid):
        diagnosis["status"] = "PROCESS_DEAD"
        diagnosis["reason"] = f"PID_{pid}_NOT_IN_RAM"
        return diagnosis
    checks["pid"] = True

    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline())
        if "web_server.py" not in cmdline:
            diagnosis["status"] = "STATE_INCONSISTENT"
            diagnosis["reason"] = "PID_HIJACKED_OR_MISMATCH"
            return diagnosis
        checks["cmdline"] = True
    except Exception:
        diagnosis["status"] = "PROCESS_DEGRADED"
        diagnosis["reason"] = "UNABLE_TO_INSPECT_PROCESS"
        return diagnosis

    port_active = any(
        conn.laddr.port == 8001 and conn.status == psutil.CONN_LISTEN
        for conn in psutil.net_connections(kind='inet')
        if conn.pid == pid
    )
    if port_active:
        checks["tcp"] = True

    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=3) as req:
            if req.status == 200:
                checks["http"] = True
                payload = json.loads(req.read().decode("utf-8"))
                if payload.get("status") == "ONLINE" or payload.get("ok") is True:
                    checks["semantic"] = True
                    diagnosis["status"] = "ONLINE"
                    diagnosis["reason"] = "HEALTHY"
                else:
                    diagnosis["status"] = "API_DEGRADED"
                    diagnosis["reason"] = "HEALTH_PAYLOAD_INVALID"
            else:
                diagnosis["status"] = "API_DEGRADED"
                diagnosis["reason"] = f"HTTP_STATUS_{req.status}"
    except Exception as e:
        diagnosis["status"] = "API_UNRESPONSIVE"
        diagnosis["reason"] = f"HTTP_CONNECTION_FAILED: {e}"

    return diagnosis

def update_health_manifest(diagnosis: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat = {
        "service": "ezzio-api",
        "pid": json.loads(PID_FILE.read_text()).get("pid"),
        "status": diagnosis["status"],
        "reason": diagnosis["reason"],
        "checks": diagnosis["checks"],
        "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    HEALTH_FILE.write_text(json.dumps(heartbeat, indent=2), encoding="utf-8")

if __name__ == "__main__":
    diag = diagnose_runtime_state()
    update_health_manifest(diag)
    print(f"[*] Diagnostic Watchdog : {diag['status']} ({diag['reason']}) | Checks: {diag['checks']}")
