import os
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

TARGET_CONSUMERS = [
    "runtime/gateway/adapter.py",
    "runtime/recovery/incident_bundle.py",
    "runtime/recovery/queue/bus.py",
    "runtime/recovery/decision/engine.py"
]

def run_alignment_audit():
    print("[*] Démarrage de V7.11.5.6 — Consumer Contract Alignment Audit...")
    
    findings = []

    for rel_path in TARGET_CONSUMERS:
        full_path = ROOT_DIR / rel_path
        file_record = {
            "file": rel_path,
            "exists": full_path.exists(),
            "calls_inspected": []
        }

        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=str(full_path))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in {"IncidentBundle", "TelemetryEvent", "TelemetryCollector", "RecoveryPolicyEngine"}:
                            # Extraire les arguments fournis par le consommateur
                            keyword_args = [kw.arg for kw in node.keywords if kw.arg is not None]
                            positional_count = len(node.args)
                            
                            file_record["calls_inspected"].append({
                                "target_class": func_name,
                                "lineno": node.lineno,
                                "positional_args_count": positional_count,
                                "provided_keyword_args": keyword_args
                            })
            except Exception as e:
                file_record["error"] = str(e)

        findings.append(file_record)

    report = {
        "timestamp": datetime.now().isoformat(),
        "alignment_audit": findings
    }

    out_json = REGISTRY_OUT / "consumer_alignment_audit.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, out_json)
    print(f"[OK] Audit d'alignement terminé. Rapport : {REGISTRY_OUT / 'V7_11_5_6_ALIGNMENT_AUDIT_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_6_ALIGNMENT_AUDIT_REPORT.md"
    items = report["alignment_audit"]
    
    lines = [
        "# E-ZZIO V7.11.5.6 — Consumer Contract Alignment Audit Report",
        f"**Date :** {report['timestamp']}",
        "",
        "## 1. Inspection des Appels Consommateurs (Arguments Fournis vs V3)",
        "Analyse AST détaillée des paramètres passés aux classes du noyau par les points d'entrée actifs :"
    ]

    for item in items:
        lines.append(f"### 📄 `{item['file']}` *(Présent: {item['exists']})*")
        if item.get("calls_inspected"):
            for call in item["calls_inspected"]:
                kws = ", ".join(call["provided_keyword_args"]) if call["provided_keyword_args"] else "Aucun (appel positionnel pur)"
                lines.append(f"- Ligne **{call['lineno']}** : ` {call['target_class']} ` | Args positionnels: `{call['positional_args_count']}` | Mots-clés fournis: `[{kws}]`")
        else:
            lines.append("- *Aucun appel direct intercepté dans ce fichier.*")
        lines.append("")

    lines.extend([
        "## 2. Conclusion de l'Audit d'Alignement",
        "Ce rapport fournit la cartographie exacte des divergences d'arguments, permettant de rédiger les correctifs ciblés (mise à jour des appels vers les contrats V3 sans altérer la baseline).",
        "",
        f"**Registre JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    run_alignment_audit()
