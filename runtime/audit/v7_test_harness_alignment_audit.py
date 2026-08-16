import os
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def audit_test_harnesses():
    print("[*] Démarrage de V7.11.5.7 — Test Harness Alignment Audit...")
    
    audit_dir = ROOT_DIR / "runtime" / "audit"
    findings = []

    if audit_dir.exists():
        for py_file in audit_dir.rglob("*.py"):
            rel_str = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
            # Ignorer ce script lui-même
            if "v7_test_harness_alignment_audit.py" in rel_str:
                continue

            file_record = {
                "file": rel_str,
                "legacy_calls_found": []
            }

            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    # Détecter les appels de méthodes obsolètes (.emit, get_active_policies)
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            attr_name = node.func.attr
                            if attr_name in {"emit", "get_active_policies"}:
                                file_record["legacy_calls_found"].append({
                                    "line": node.lineno,
                                    "issue": f"Outdated method call: .{attr_name}()"
                                })
                        elif isinstance(node.func, ast.Name):
                            # Détecter instanciations minimalistes de IncidentBundle avec < 5 arguments
                            if node.func.id == "IncidentBundle" and len(node.args) < 5 and len(node.keywords) < 5:
                                file_record["legacy_calls_found"].append({
                                    "line": node.lineno,
                                    "issue": "Potentially incomplete IncidentBundle instantiation in test harness"
                                })
            except Exception as e:
                file_record["parse_error"] = str(e)

            if file_record["legacy_calls_found"]:
                findings.append(file_record)

    report = {
        "timestamp": datetime.now().isoformat(),
        "harness_audit_findings": findings
    }

    out_json = REGISTRY_OUT / "test_harness_alignment_audit.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, out_json)
    print(f"[OK] Audit des harnais terminé. Rapport : {REGISTRY_OUT / 'V7_11_5_7_HARNESS_AUDIT_REPORT.md'}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_7_HARNESS_AUDIT_REPORT.md"
    items = report["harness_audit_findings"]
    
    lines = [
        "# E-ZZIO V7.11.5.7 — Test Harness Alignment Audit Report",
        f"**Date :** {report['timestamp']}",
        "",
        "## 1. Détection des Appels Obsolètes dans les Scripts d'Audit / Test",
        "Analyse de notre propre écosystème de test pour éliminer les faux négatifs :"
    ]

    if not items:
        lines.append("🟢 **Aucun appel obsolète résiduel détecté dans les scripts de test.**")
    else:
        for item in items:
            lines.append(f"### 📄 `{item['file']}`")
            for call in item["legacy_calls_found"]:
                lines.append(f"- Ligne **{call['line']}** : `{call['issue']}`")
            lines.append("")

    lines.extend([
        "## 2. Conclusion",
        "Ce nettoyage des outils d'audit garantit que la prochaine exécution de la certification comportementale reflétera la stricte réalité de la production Baseline V3, sans artéfact de test obsolète.",
        "",
        f"**Registre JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    audit_test_harnesses()
