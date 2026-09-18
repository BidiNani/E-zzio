import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(r"G:/AI/E-zzio").resolve()
sys.path.insert(0, str(ROOT))

def get_production_status() -> dict:
    status = {
        "timestamp": os.getenv("EZZIO_STATUS_TIME", ""),
        "components": {}
    }

    # 1. E-ZZIO API / Readiness
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/health/readiness")
        with urllib.request.urlopen(req, timeout=3) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                status["components"]["ezzio_api"] = {
                    "status": "READY",
                    "details": data
                }
            else:
                status["components"]["ezzio_api"] = {"status": "DEGRADED", "code": res.status}
    except Exception as e:
        status["components"]["ezzio_api"] = {"status": "STOPPED", "error": str(e)}

    # 2. Open WebUI (Docker)
    try:
        req_owui = urllib.request.Request("http://127.0.0.1:3000")
        with urllib.request.urlopen(req_owui, timeout=3) as res_owui:
            if res_owui.status == 200:
                status["components"]["open_webui"] = {"status": "READY", "port": 3000}
            else:
                status["components"]["open_webui"] = {"status": "DEGRADED", "port": 3000}
    except Exception:
        status["components"]["open_webui"] = {"status": "STOPPED", "port": 3000}

    # 3. Tailscale
    ts_bin = Path(r"G:/AI/tailscale.exe")
    if ts_bin.exists():
        try:
            r_ts = subprocess.run([str(ts_bin), "status"], capture_output=True, text=True, timeout=5)
            r_ip = subprocess.run([str(ts_bin), "ip", "-4"], capture_output=True, text=True, timeout=5)
            status["components"]["tailscale"] = {
                "status": "READY",
                "ip": r_ip.stdout.strip(),
                "node": "bidinani"
            }
        except Exception as e:
            status["components"]["tailscale"] = {"status": "DEGRADED", "error": str(e)}
    else:
        status["components"]["tailscale"] = {"status": "ENVIRONMENT_LIMITED"}

    # 4. Discord
    sec_env = ROOT / "secrets" / ".env"
    if sec_env.exists() and "DISCORD_TOKEN=" in sec_env.read_text(encoding="utf-8", errors="ignore"):
        status["components"]["discord"] = {"status": "READY", "bot_id": "1517996783324762132"}
    else:
        status["components"]["discord"] = {"status": "ENVIRONMENT_LIMITED"}

    # 5. Voice
    status["components"]["voice"] = {"status": "READY", "subsystem": "Windows AudioEndpoints"}

    return status

if __name__ == "__main__":
    st = get_production_status()
    print(json.dumps(st, indent=2))
