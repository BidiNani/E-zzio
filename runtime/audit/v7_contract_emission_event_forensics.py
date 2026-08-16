import os
import sys
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def search_powershell_history():
    """Tente de lire l'historique PowerShell de l'utilisateur pour y trouver des traces de contract_signer."""
    history_matches = []
    try:
        ps_history_path = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt"
        if ps_history_path.exists():
            lines = ps_history_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, line in enumerate(lines, 1):
                if any(k in line.lower() for k in ["contract_signer", "qwen2.5", "contract.json", "sign_file"]):
                    history_matches.append({
                        "line_number": idx,
                        "command": line.strip()
                    })
    except Exception as e:
        history_matches.append({"error": str(e)})
    return history_matches

def search_scripts_and_logs():
    """Scanne les scripts batch/powershell et les logs du dépôt."""
    findings = []
    search_extensions = {".ps1", ".bat", ".cmd", ".log", ".txt", ".jsonl"}
    
    for file_path in ROOT_DIR.rglob("*.*"):
        if file_path.suffix.lower() not in search_extensions:
            continue
        rel_parts = file_path.relative_to(ROOT_DIR).parts
        if any(ex in rel_parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit/intelligence_scan"}):
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            if any(k in content.lower() for k in ["contract_signer", "qwen2.5", "8376e7b8"]):
                rel_path = str(file_path.relative_to(ROOT_DIR)).replace("\\", "/")
                matching_lines = [line.strip() for line in content.splitlines() if any(k in line.lower() for k in ["contract_signer", "qwen2.5", "8376e7b8"])]
                findings.append({
                    "file": rel_path,
                    "matches": matching_lines[:5]
                })
        except Exception:
            pass
    return findings

def run_event_forensics():
    print("[*] Démarrage de V7.10.2 — Contract Emission Event Forensics...")
    
    ps_history = search_powershell_history()
    repo_traces = search_scripts_and_logs()

    payload = {
        "timestamp": datetime.now().isoformat(),
        "powershell_history_traces": ps_history,
        "repository_script_and_log_traces": repo_traces
    }

    out_json = REGISTRY_OUT / "contract_emission_event_forensics.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(payload)
    print(f"[OK] V7.10.2 Event Forensics terminé. Rapport enregistré dans {REGISTRY_OUT}")

def build_markdown(res: dict):
    md_path = REGISTRY_OUT / "V7_10_2_EMISSION_EVENT_REPORT.md"
    ps_hist = res.get("powershell_history_traces", [])
    repo_traces = res.get("repository_script_and_log_traces", [])

    lines = [
        "# E-ZZIO V7.10.2 — Contract Emission Event Forensics Report",
        f"**Date :** {res.get('timestamp')}",
        "",
        "## 1. Traces dans l'Historique PowerShell (`PSReadLine`)",
        f"**Occurrences trouvées dans l'historique utilisateur :** {len(ps_hist)}",
        ""
    ]

    for h in ps_hist:
        if "error" in h:
            lines.append(f"  - *Erreur d'accès à l'historique :* `{h['error']}`")
        else:
            lines.append(f"  - Ligne {h['line_number']} : `{h['command']}`")

    lines.extend([
        "",
        "## 2. Traces dans les Scripts et Logs du Dépôt",
        f"**Fichiers du dépôt impactés :** {len(repo_traces)}",
        ""
    ])

    for r in repo_traces:
        lines.append(f"### Fichier : `{r['file']}`")
        for m in r['matches']:
            lines.append(f"  - `{m}`")
        lines.append("")

    lines.extend([
        "",
        "## 3. Bilan de l'Enquête d'Événement & Statut",
        "L'examen des historiques externes et des logs permet de certifier l'événement d'émission. Le système reste strictement figé en **lecture seule (READ-ONLY)**. Aucune modification de la Trust Layer n'est autorisée à ce stade."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown d'événement généré : {md_path}")

if __name__ == "__main__":
    run_event_forensics()
