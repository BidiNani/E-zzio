import os
import sys
import ast
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def run_compatibility_audit():
    print("[*] Démarrage de V7.11.5.3 — API Contract Compatibility & Consumer Audit...")
    
    # 1. Exécution des tests avec application de la Règle d'Échec Stricte
    test_results = []
    
    # Test Recovery
    try:
        from runtime.recovery.contracts import IncidentBundle
        from runtime.recovery.decision.governor import DecisionGovernor
        governor = DecisionGovernor()
        bundle = IncidentBundle(
            incident_id="INC-V7.11.5.3-STRICT",
            severity="CRITICAL",
            category="RUNTIME_CORE"
        )
        decision = governor.evaluate(bundle)
        test_results.append({"test_name": "Aligned Recovery Lifecycle", "status": "SUCCESS", "details": "Evaluated successfully."})
    except Exception as e:
        test_results.append({"test_name": "Aligned Recovery Lifecycle", "status": "FAILED", "details": str(e)})

    # Test Telemetry
    try:
        from runtime.telemetry.collector import TelemetryCollector
        from runtime.telemetry.events import TelemetryEvent
        collector = TelemetryCollector()
        event = TelemetryEvent(event_type="COMPATIBILITY_CHECK", payload={"status": "ok"})
        collector.emit(event)
        test_results.append({"test_name": "Aligned Telemetry Pipeline", "status": "SUCCESS", "details": "Emitted successfully."})
    except Exception as e:
        test_results.append({"test_name": "Aligned Telemetry Pipeline", "status": "FAILED", "details": str(e)})

    # Test Policy Engine
    try:
        from runtime.recovery.decision.policies import RecoveryPolicyEngine
        from runtime.recovery.contracts import IncidentBundle
        engine = RecoveryPolicyEngine()
        test_bundle = IncidentBundle(incident_id="INC-POL", severity="MEDIUM", category="TEST")
        res = engine.evaluate(test_bundle)
        test_results.append({"test_name": "Aligned Policy Evaluation", "status": "SUCCESS", "details": f"Evaluated: {res}"})
    except Exception as e:
        test_results.append({"test_name": "Aligned Policy Evaluation", "status": "FAILED", "details": str(e)})

    # Règle d'échec stricte : si un seul test échoue, certification = FAILED
    any_failed = any(t["status"] == "FAILED" for t in test_results)
    certification_status = "FAILED" if any_failed else "PASSED"

    # 2. Consumer Scan (AST Scan des instanciations dans le noyau actif)
    consumers = []
    for py_file in ROOT_DIR.rglob("*.py"):
        rel_str = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
        if any(noise in rel_str.lower() for noise in {"quarantine", "archive", "legacy", "audit", "test"}):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in {"IncidentBundle", "TelemetryEvent", "RecoveryPolicyEngine"}:
                        consumers.append({
                            "file": rel_str,
                            "class": node.func.id,
                            "lineno": node.lineno
                        })
        except:
            pass

    report = {
        "timestamp": datetime.now().isoformat(),
        "certification_status": certification_status,
        "strict_test_suite": test_results,
        "consumers_scanned_count": len(consumers),
        "consumer_usages": consumers
    }

    report_json = REGISTRY_OUT / "api_compatibility_audit.json"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, report_json)
    print(f"[OK] Audit de compatibilité terminé. Statut global : {certification_status}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_3_API_COMPATIBILITY_REPORT.md"
    tests = report["strict_test_suite"]
    consumers = report["consumer_usages"]

    lines = [
        "# E-ZZIO V7.11.5.3 — API Contract Compatibility & Strict Certification Report",
        f"**Date :** {report['timestamp']}",
        f"**Statut de Certification Strict :** `{report['certification_status']}`",
        "",
        "## 1. Résultats de la Suite de Tests (Règle d'échec stricte appliquée)",
        "| Composant Testé | Statut | Diagnostics |",
        "| :--- | :---: | :--- |"
    ]

    for t in tests:
        st_icon = "🟢 SUCCÈS" if t["status"] == "SUCCESS" else "🔴 ÉCHEC"
        lines.append(f"| `{t['test_name']}` | {st_icon} | `{t['details']}` |")

    lines.extend([
        "",
        "## 2. Matrice de Compatibilité & Consommateurs Actifs",
        f"**Total des instanciations détectées dans le noyau actif :** `{len(consumers)}`",
        "| Fichier Consommateur | Classe Instanciée | Ligne |",
        "| :--- | :--- | :---: |"
    ])

    for c in consumers[:30]:
        lines.append(f"| `{c['file']}` | `{c['class']}` | {c['lineno']} |")

    lines.extend([
        "",
        "## 3. Conclusion de l'Audit V7.11.5.3",
        "La règle d'échec stricte est désormais active. Ce rapport trace les consommateurs réels et certifie l'état de conformité des flux dynamiques sans artifice narratif.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    run_compatibility_audit()
