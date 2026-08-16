import os
import sys
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def run_negative_regression_gate():
    print("[*] Démarrage du Test Négatif Anti-Régression (Negative Gate)...")
    
    violations = []
    tests_performed = 0

    # Test 1 : TelemetryCollector ne doit PAS posséder de méthode .emit()
    tests_performed += 1
    try:
        from runtime.telemetry.collector import TelemetryCollector
        collector = TelemetryCollector()
        if hasattr(collector, "emit"):
            violations.append("FAIL: TelemetryCollector expose encore .emit() (Mémoire legacy active).")
        else:
            print("  [PASS] TelemetryCollector.emit() est correctement absent.")
    except Exception as e:
        violations.append(f"ERROR: Impossible d'instancier TelemetryCollector : {str(e)}")

    # Test 2 : RecoveryPolicyEngine ne doit PAS posséder de méthode .get_active_policies()
    tests_performed += 1
    try:
        from runtime.recovery.decision.policies import RecoveryPolicyEngine
        engine = RecoveryPolicyEngine()
        if hasattr(engine, "get_active_policies"):
            violations.append("FAIL: RecoveryPolicyEngine expose encore .get_active_policies().")
        else:
            print("  [PASS] RecoveryPolicyEngine.get_active_policies() est correctement absent.")
    except Exception as e:
        violations.append(f"ERROR: Impossible d'instancier RecoveryPolicyEngine : {str(e)}")

    # Test 3 : DecisionGovernor ne doit PAS posséder de méthode .evaluate()
    tests_performed += 1
    try:
        from runtime.recovery.decision.governor import DecisionGovernor
        gov = DecisionGovernor()
        if hasattr(gov, "evaluate"):
            violations.append("FAIL: DecisionGovernor expose encore .evaluate().")
        else:
            print("  [PASS] DecisionGovernor.evaluate() est correctement absent (obligation de passer par .govern).")
    except Exception as e:
        violations.append(f"ERROR: Impossible d'instancier DecisionGovernor : {str(e)}")

    gate_status = "NEGATIVE_GATE_PASSED" if not violations else "NEGATIVE_GATE_VIOLATED"

    report = {
        "timestamp": datetime.now().isoformat(),
        "gate_status": gate_status,
        "tests_executed": tests_performed,
        "violations_detected": violations
    }

    out_json = REGISTRY_OUT / "negative_regression_gate_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(report, out_json)
    print(f"[OK] Test négatif terminé. Statut de la barrière : {gate_status}")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_6_NEGATIVE_GATE_REPORT.md"
    violations = report["violations_detected"]
    
    lines = [
        "# E-ZZIO V7.11.6 — Negative Regression Gate Report",
        f"**Date :** {report['timestamp']}",
        f"**Statut de la Barrière :** `{report['gate_status']}`",
        f"**Tests négatifs exécutés :** `{report['tests_executed']}`",
        "",
        "## 1. Vérification du Rejet des Anciennes Interfaces (Legacy Rejection)",
        "Ce portillon prouve que les méthodes obsolètes (`emit`, `get_active_policies`, `DecisionGovernor.evaluate`) ne peuvent plus revenir silencieusement dans le noyau de production :"
    ]

    if not violations:
        lines.append("🟢 **SUCCÈS ABSOLU : Toutes les anciennes interfaces ont été rejetées ou sont absentes du noyau. Le portillon anti-régression est hermétique.**")
    else:
        lines.append("🔴 **VIOLATION DÉTECTÉE :**")
        for v in violations:
            lines.append(f"- `{v}`")

    lines.extend([
        "",
        "## 2. Conclusion",
        "L'écosystème E-ZZIO dispose désormais d'un mécanisme de défense actif interdisant la résurgence de dettes contractuelles.",
        "",
        f"**Registre JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de la barrière généré : {md_path.name}")

if __name__ == "__main__":
    run_negative_regression_gate()
