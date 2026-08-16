import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"

def run_drift_monitor():
    print("[*] Démarrage de V7.11.4 — Baseline Drift Monitor...")
    
    v3_path = REGISTRY_OUT / "architecture_baseline_v3.json"
    if not v3_path.exists():
        print("[!] Erreur : architecture_baseline_v3.json introuvable. Exécutez d'abord la V7.11.3.")
        return

    baseline_data = json.loads(v3_path.read_text(encoding="utf-8"))
    frozen_modules = baseline_data.get("module_hashes", {})

    # Scanner l'état actuel de la production active
    current_modules = {}
    total_current_bytes = 0

    for py_file in ROOT_DIR.rglob("*.py"):
        rel_str = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
        
        # Application du même filtre strict que la V7.11.3
        if any(noise in rel_str.lower() for noise in {"quarantine", "archive", "legacy", "audit", "test"}):
            continue

        try:
            file_size = py_file.stat().st_size
            file_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
            current_modules[rel_str] = {
                "sha256": file_hash,
                "size_bytes": file_size
            }
            total_current_bytes += file_size
        except Exception:
            pass

    # Analyse comparative (Drift Analysis)
    frozen_keys = set(frozen_modules.keys())
    current_keys = set(current_modules.keys())

    added_files = sorted(list(current_keys - frozen_keys))
    deleted_files = sorted(list(frozen_keys - current_keys))
    common_files = frozen_keys.intersection(current_keys)

    modified_files = []
    unchanged_count = 0

    for f in common_files:
        frozen_hash = frozen_modules[f]["sha256"]
        current_hash = current_modules[f]["sha256"]
        if frozen_hash != current_hash:
            modified_files.append({
                "file": f,
                "frozen_sha256": frozen_hash,
                "current_sha256": current_hash
            })
        else:
            unchanged_count += 1

    drift_detected = bool(added_files or deleted_files or modified_files)
    status_label = "DRIFT_DETECTED" if drift_detected else "PERFECT_SYNCHRONIZATION"

    drift_report = {
        "timestamp": datetime.now().isoformat(),
        "monitor_status": status_label,
        "metrics": {
            "frozen_total": len(frozen_keys),
            "current_total": len(current_keys),
            "unchanged": unchanged_count,
            "added": len(added_files),
            "deleted": len(deleted_files),
            "modified": len(modified_files)
        },
        "details": {
            "added": added_files,
            "deleted": deleted_files,
            "modified": modified_files
        }
    }

    report_json = REGISTRY_OUT / "baseline_drift_report.json"
    report_json.write_text(json.dumps(drift_report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(drift_report, report_json)
    print(f"[OK] Moniteur de dérive terminé. Statut : {status_label}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_4_BASELINE_DRIFT_REPORT.md"
    m = report["metrics"]
    details = report["details"]
    
    lines = [
        "# E-ZZIO V7.11.4 — Baseline Drift Monitor Report",
        f"**Date :** {report['timestamp']}",
        f"**Statut de l'Intégrité :** `{report['monitor_status']}`",
        "",
        "## 1. Métriques de Dérive (Drift Metrics)",
        "| Indicateur | Valeur |",
        "| :--- | :---: |",
        f"| Modules Baseline V3 (Référence) | `{m['frozen_total']}` |",
        f"| Modules Actuels (Scannés) | `{m['current_total']}` |",
        f"| Intacts (`UNCHANGED`) | `{m['unchanged']}` |",
        f"| Ajoutés (`ADDED`) | `{m['added']}` |",
        f"| Supprimés (`DELETED`) | `{m['deleted']}` |",
        f"| Modifiés (`MODIFIED`) | `{m['modified']}` |",
        "",
        "## 2. Analyse Détaillée des Écarts"
    ]

    if not report["monitor_status"] == "DRIFT_DETECTED":
        lines.append("🟢 **Aucune dérive détectée. L'état actuel du dépôt correspond exactement au sceau cryptographique de la Baseline V3.**")
    else:
        if details["added"]:
            lines.append("### Fichiers Ajoutés :")
            for f in details["added"]: lines.append(f"- `{f}`")
        if details["deleted"]:
            lines.append("### Fichiers Supprimés :")
            for f in details["deleted"]: lines.append(f"- `{f}`")
        if details["modified"]:
            lines.append("### Fichiers Modifiés (Divergence de hash) :")
            for mod in details["modified"]:
                lines.append(f"- `{mod['file']}` *(Ancien: `{mod['frozen_sha256'][:8]}...` -> Nouveau: `{mod['current_sha256'][:8]}...`)*")

    lines.extend([
        "",
        "## 3. Conclusion du Moniteur Continu",
        "Le système dispose désormais d'un mécanisme de surveillance d'intégrité capable de valider à tout moment la conformité de son architecture active.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de dérive généré : {md_path.name}")

if __name__ == "__main__":
    run_drift_monitor()
