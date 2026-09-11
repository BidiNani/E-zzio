from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

def scan_file_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def main():
    print("=" * 80)
    print(" GATE v6.45.39 — CANONICAL AUTHORITY & CONTRACT RECONCILIATION")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report: Dict[str, Any] = {
        "normative_contracts": [],
        "fabric_candidates": [],
        "runtime_execution_paths": []
    }

    constitution_dir = PROJECT_ROOT / "core" / "constitution"
    identity_dir = PROJECT_ROOT / "core" / "identity"
    config_dir = PROJECT_ROOT / "config"

    if constitution_dir.exists():
        for p in constitution_dir.glob("**/*"):
            if p.is_file():
                report["normative_contracts"].append({"path": str(p.relative_to(PROJECT_ROOT)), "type": "constitution"})

    if identity_dir.exists():
        for p in identity_dir.glob("**/*"):
            if p.is_file():
                report["normative_contracts"].append({"path": str(p.relative_to(PROJECT_ROOT)), "type": "identity_spec"})

    if config_dir.exists():
        for p in config_dir.glob("**/*"):
            if p.is_file():
                report["normative_contracts"].append({"path": str(p.relative_to(PROJECT_ROOT)), "type": "config"})

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    for p in py_files:
        rel = str(p.relative_to(PROJECT_ROOT))
        content = scan_file_safely(p)
        if "AutonomousModelFabric" in content or "ModelRegistry" in content or "IntentRouter" in content:
            report["fabric_candidates"].append({
                "path": rel,
                "has_fabric": "AutonomousModelFabric" in content,
                "has_registry": "ModelRegistry" in content,
                "has_router": "IntentRouter" in content
            })

    print(f"[1] CONTRATS NORMATIFS DÉTECTÉS ({len(report['normative_contracts'])} fichiers)")
    for c in report["normative_contracts"][:10]:
        print(f"  • [{c['type']}] {c['path']}")

    print(f"\n[2] COMPOSANTS FABRIC CANDIDATS DÉTECTÉS ({len(report['fabric_candidates'])} fichiers)")
    for f in report["fabric_candidates"][:10]:
        print(f"  • {f['path']} (Fabric: {f['has_fabric']}, Registry: {f['has_registry']}, Router: {f['has_router']})")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_39_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()