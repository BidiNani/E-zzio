from __future__ import annotations

import os
import sys
import json
import time
import socket
from pathlib import Path
from typing import Any, Dict

import psutil
import requests

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
SNAPSHOT_ROOT = STATE_ROOT / "snapshots"

STATE_ROOT.mkdir(parents=True, exist_ok=True)
SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def _safe_call(name: str, fn):
    try:
        return {"ok": True, "name": name, "data": fn()}
    except Exception as exc:
        return {"ok": False, "name": name, "error": str(exc)}

def lan_ips():
    ips = []
    try:
        host = socket.gethostname()
        for item in socket.getaddrinfo(host, None):
            ip = item[4][0]
            if "." in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and ip not in ips:
            ips.append(ip)
    except Exception:
        pass

    return ips

def system_status():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(PROJECT_ROOT.anchor or "G:/"))

    return {
        "time": _now(),
        "python": sys.version,
        "project_root": str(PROJECT_ROOT),
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=0.2),
        },
        "ram": {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_percent": mem.percent,
        },
        "disk": {
            "root": str(PROJECT_ROOT.anchor or "G:/"),
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "used_percent": disk.percent,
        },
        "lan_ips": lan_ips(),
        "env_policy": {
            "OLLAMA_NUM_GPU": os.environ.get("OLLAMA_NUM_GPU"),
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "GGML_CUDA": os.environ.get("GGML_CUDA"),
            "EZZIO_GPU_POLICY": os.environ.get("EZZIO_GPU_POLICY"),
            "EZZIO_NO_ADS": os.environ.get("EZZIO_NO_ADS"),
            "EZZIO_NO_TRACKING": os.environ.get("EZZIO_NO_TRACKING"),
            "EZZIO_NO_SPONSORS": os.environ.get("EZZIO_NO_SPONSORS"),
        },
    }

def router_status():
    try:
        web_server = sys.modules.get("web_server")
        report = getattr(web_server, "router_load_report", None)
        if report:
            return {
                "loaded_count": len(report.get("loaded", [])),
                "failed_count": len(report.get("failed", {})),
                "loaded": report.get("loaded", []),
                "failed": report.get("failed", {}),
            }
    except Exception as exc:
        return {"error": str(exc)}

    return {"error": "router_load_report indisponible"}

def forge_status():
    try:
        from core.creative_forge import status
        return status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def vision_status():
    try:
        from core.vision_bridge import status
        return status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def omni_status():
    try:
        from core.omni_brain import bridge_status
        return bridge_status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def model_status():
    try:
        from core.model_registry import status as registry_status
        return registry_status()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def no_ads_policy():
    return {
        "ok": True,
        "ads": "forbidden",
        "tracking": "forbidden",
        "sponsors": "forbidden",
        "paid_recommendations": "forbidden",
        "data_sale": "forbidden",
        "policy": "E-ZZIO est local-first, sans pub ni tracking.",
    }

def supervisor_status():
    checks = {
        "system": _safe_call("system", system_status),
        "routers": _safe_call("routers", router_status),
        "forge": _safe_call("forge", forge_status),
        "vision": _safe_call("vision", vision_status),
        "omni": _safe_call("omni", omni_status),
        "models": _safe_call("models", model_status),
        "no_ads": _safe_call("no_ads", no_ads_policy),
    }

    failed = {k: v for k, v in checks.items() if not v.get("ok")}

    return {
        "ok": len(failed) == 0,
        "version": "v2.12-supervisor-watchdog-mobile-home",
        "created_at": _now(),
        "summary": {
            "checks_total": len(checks),
            "checks_failed": len(failed),
            "cpu_ram_only": True,
            "no_ads": True,
        },
        "checks": checks,
    }

def write_snapshot():
    data = supervisor_status()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = SNAPSHOT_ROOT / f"ezzio_snapshot_{stamp}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "path": str(path),
        "snapshot": data,
    }

def recent_snapshots(limit: int = 20):
    files = sorted(SNAPSHOT_ROOT.glob("ezzio_snapshot_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:max(1, min(limit, 100))]:
        out.append({
            "name": p.name,
            "path": str(p),
            "modified": p.stat().st_mtime,
            "mb": round(p.stat().st_size / (1024 ** 2), 3),
        })
    return {"ok": True, "snapshots": out}

def watchdog_once():
    data = supervisor_status()
    actions = []

    routers = data["checks"].get("routers", {}).get("data", {})
    if routers.get("failed_count", 0) > 0:
        actions.append("Routers échoués détectés : consulter /router-status.")

    system = data["checks"].get("system", {}).get("data", {})
    ram = system.get("ram", {})
    disk = system.get("disk", {})

    if ram.get("available_gb", 99) < 4:
        actions.append("RAM disponible basse : fermer ComfyUI, génération image ou gros modèle Ollama.")

    if disk.get("free_gb", 999) < 20:
        actions.append("Disque libre bas : nettoyer logs, outputs, caches ou snapshots.")

    if not data["checks"].get("no_ads", {}).get("ok", False):
        actions.append("Policy no-ads indisponible : vérifier web_server/supervisor.")

    if not actions:
        actions.append("Aucune action critique. E-ZZIO est stable.")

    report = {
        "ok": data.get("ok", False),
        "created_at": _now(),
        "actions": actions,
        "status": data,
    }

    path = STATE_ROOT / "watchdog_last.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report

def mobile_home_html():
    ips = lan_ips()
    local_urls = "".join(
        f"<li><a href='http://{ip}:8000/status'>http://{ip}:8000/status</a></li>"
        f"<li><a href='http://{ip}:8000/omni-bridge/mobile/config'>Mobile config {ip}</a></li>"
        f"<li><a href='http://{ip}:8000/supervisor/mobile-home'>Mobile home {ip}</a></li>"
        for ip in ips
    )

    return f"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E-ZZIO Mobile Home</title>
<style>
body {{
  font-family: system-ui, Arial, sans-serif;
  background: #111;
  color: #f2f2f2;
  padding: 20px;
  line-height: 1.45;
}}
.card {{
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 16px;
  padding: 16px;
  margin: 12px 0;
}}
a {{ color: #9ad7ff; }}
.badge {{
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  background: #263;
  margin: 3px;
}}
code {{
  background: #222;
  padding: 2px 5px;
  border-radius: 6px;
}}
</style>
</head>
<body>
<h1>🤖 E-ZZIO</h1>
<div class="card">
  <span class="badge">CPU/RAM only</span>
  <span class="badge">No ads</span>
  <span class="badge">No tracking</span>
  <span class="badge">Local-first</span>
</div>

<div class="card">
  <h2>État réel</h2>
  <p>PC actif. Bridge smartphone LAN prêt. Discord/Messenger prêts côté API mais non configurés tant que les tokens ne sont pas renseignés.</p>
</div>

<div class="card">
  <h2>Commandes utiles</h2>
  <p><code>/help</code> <code>/truth</code> <code>/everywhere</code> <code>/mobile</code> <code>/forge</code> <code>/vision</code> <code>/noads</code></p>
</div>

<div class="card">
  <h2>Liens LAN</h2>
  <ul>{local_urls}</ul>
</div>

<div class="card">
  <h2>Endpoints</h2>
  <ul>
    <li><a href="/supervisor/status">Supervisor status</a></li>
    <li><a href="/supervisor/watchdog">Watchdog</a></li>
    <li><a href="/router-status">Routers</a></li>
    <li><a href="/omni-bridge/truth">Truth</a></li>
    <li><a href="/no-ads-policy">No ads policy</a></li>
  </ul>
</div>
</body>
</html>
""".strip()
