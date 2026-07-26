import os
import shutil
import socket
import subprocess
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None

PROJECT_ROOT = Path("G:/AI/E-zzio")
REGISTRY_ROOT = PROJECT_ROOT / "registry"
LOG_ROOT = PROJECT_ROOT / "logs"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"

def check_port(host="127.0.0.1", port=8000):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex((host, port))
        return result == 0
    finally:
        s.close()

def check_ollama():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-2000:],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def disk_status(path="G:/"):
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "free_percent": round((usage.free / usage.total) * 100, 2),
        }
    except Exception as exc:
        return {"error": str(exc)}

def process_status():
    if psutil is None:
        return {"available": False}

    current = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or [])
            if "uvicorn" in cmd or "web_server:app" in cmd or "ollama" in cmd.lower():
                mem = proc.info.get("memory_info")
                current.append({
                    "pid": proc.info.get("pid"),
                    "name": proc.info.get("name"),
                    "cmdline": cmd[:500],
                    "rss_mb": round(mem.rss / (1024**2), 1) if mem else None,
                })
        except Exception:
            pass

    return {"available": True, "items": current}

def project_status():
    required = [
        PROJECT_ROOT / "web_server.py",
        PROJECT_ROOT / "core" / "dispatcher.py",
        PROJECT_ROOT / "core" / "llm_engine.py",
        PROJECT_ROOT / "core" / "memory.py",
        PROJECT_ROOT / "core" / "actions.py",
        PROJECT_ROOT / "routers" / "chat.py",
        PROJECT_ROOT / "routers" / "system.py",
    ]

    files = {}
    for item in required:
        files[str(item)] = item.exists()

    return {
        "project_root": str(PROJECT_ROOT),
        "files": files,
        "registry_exists": REGISTRY_ROOT.exists(),
        "logs_exists": LOG_ROOT.exists(),
        "workspace_exists": WORKSPACE_ROOT.exists(),
    }

def doctor():
    disk = disk_status("G:/")
    ollama = check_ollama()
    port = check_port()
    project = project_status()
    processes = process_status()

    warnings = []
    recommendations = []

    if disk.get("free_gb", 999) < 20:
        warnings.append("Espace disque bas sur G:.")
        recommendations.append("Nettoyer caches, anciens backups et modèles Ollama inutiles.")

    if not ollama.get("ok"):
        warnings.append("Ollama ne répond pas correctement.")
        recommendations.append("Vérifier le service Ollama avant de lancer E-ZZIO.")

    if not all(project["files"].values()):
        warnings.append("Des fichiers critiques E-ZZIO manquent.")
        recommendations.append("Restaurer depuis backups ou relancer le patch global.")

    if not port:
        warnings.append("L'API E-ZZIO ne semble pas écouter sur 127.0.0.1:8000.")
        recommendations.append("Relancer scripts/start_ezzio.ps1.")

    return {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "recommendations": recommendations,
        "disk": disk,
        "ollama": ollama,
        "api_port_8000_listening": port,
        "project": project,
        "processes": processes,
    }
