import os
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

TARGET_FILES = [
    "runtime/gateway/adapter.py",
    "runtime/recovery/incident_bundle.py",
    "runtime/recovery/queue/bus.py",
    "runtime/recovery/decision/engine.py"
]

def audit_consumer_contexts():
    print("[*] Démarrage de V7.11.5.5 — Consumer Contract Migration Planner...")
    
    audit_findings = []

    for rel_path in TARGET_FILES:
        full_path = ROOT_DIR / rel_path
        file_record = {
            "file": rel_path,
            "exists": full_path.exists(),
            "legacy_patterns_found": []
        }

        if full_path.exists():
            try:
                lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
                for idx, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    # Détection des patterns obsolètes ciblés
                    matches = []
                    if "source_component" in line_lower: matches.append("source_component")
                    if "level=" in line_lower or "'level'" in line_lower or '"level"' in line_lower: matches.append("level_arg")
                    if ".emit(" in line_lower: matches.append("collector_emit")
                    if "get_active_policies" in line_lower: matches.append("get_active_policies")

                    if matches:
                        file_record["legacy_patterns_found"].append({
                            "line_number": idx,
                            "content": line.strip(),
                            "patterns": matches
                        })
            except Exception as e:
                file_record["error"] = str(e)

        audit_findings.append(file_record)

    report = {
        "timestamp": datetime.now().isoformat(),
        "migration_targets": audit_findings
    }

    out_json = REGISTRY_OUT / "consumer_migration_plan.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, out_json)
    print(f"[OK] Planificateur de migration terminé. Rapport : {REGISTRY_OUT / 'V7_11_5_5_MIGRATION_PLAN_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_5_MIGRATION_PLAN_REPORT.md"
    targets = report["migration_targets"]
    
    lines = [
        "# E-ZZIO V7.11.5.5 — Consumer Contract Migration Plan Report",
        f"**Date :** {report['timestamp']}",
        "",
        "## 1. Contexte et Localisation des Patterns Obsolètes",
        "Analyse ciblée des 4 points d'entrée du noyau identifiés pour la migration des contrats :"
    ]

    for t in targets:
        lines.append(f"### 📄 `{t['file']}` *(Présent: {t['exists']})*")
        if t.get("legacy_patterns_found"):
            for p in t["legacy_patterns_found"]:
                lines.append(f"- **Ligne {p['line_number']}** `[{', '.join(p['patterns'])}]` : `{p['content']}`")
        else:
            lines.append("- *Aucun pattern obsolète direct détecté par correspondance textuelle (analyse fine requise).*")
        lines.append("")

    lines.extend([
        "## 2. Prochaine Étape (V7.11.5.6)",
        "Ce plan fournit la cartographie exacte pour rédiger les correctifs ciblés sans altérer les fondations de la Baseline V3.",
        "",
        f"**Registre JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    audit_consumer_contexts()
