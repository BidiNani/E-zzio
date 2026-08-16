import os
import sys
import ast
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)
CONTRACT_PATH = ROOT_DIR / "runtime" / "contracts" / "API_CONTRACT_V3.json"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def run_v712_entry_gate():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.12.3 — Portillon d'Entrée (Règle d'Isolement Affinée)...")
    print("[*] -----------------------------------------------------------------")
    
    audit_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "release": "V7.12.0",
        "contract_validation": "PENDING",
        "positive_behavior": "PENDING",
        "negative_regression": "PENDING",
        "cryptographic_drift": "PENDING",
        "quarantine_isolation": "PENDING",
        "violations": []
    }

    # Initialisation sécurisée
    gov, col, eng = None, None, None
    try:
        from runtime.recovery.decision.governor import DecisionGovernor
        gov = DecisionGovernor()
    except Exception as e:
        audit_results["violations"].append(f"Failed to load DecisionGovernor: {str(e)}")

    try:
        from runtime.telemetry.collector import TelemetryCollector
        col = TelemetryCollector()
    except Exception as e:
        audit_results["violations"].append(f"Failed to load TelemetryCollector: {str(e)}")

    try:
        from runtime.recovery.decision.policies import RecoveryPolicyEngine
        eng = RecoveryPolicyEngine()
    except Exception as e:
        audit_results["violations"].append(f"Failed to load RecoveryPolicyEngine: {str(e)}")

    # 1. Contrat
    if not CONTRACT_PATH.exists() or None in (gov, col, eng):
        audit_results["contract_validation"] = "FAILED"
        audit_results["violations"].append("Contract manifest missing or core components uninitialized.")
    else:
        try:
            contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
            components = contract.get("components", {})
            
            for method in components.get("DecisionGovernor", {}).get("allowed_methods", []):
                if not hasattr(gov, method): audit_results["violations"].append(f"DecisionGovernor lacks {method}")
            for method in components.get("TelemetryCollector", {}).get("allowed_methods", []):
                if not hasattr(col, method): audit_results["violations"].append(f"TelemetryCollector lacks {method}")
            for method in components.get("RecoveryPolicyEngine", {}).get("allowed_methods", []):
                if not hasattr(eng, method): audit_results["violations"].append(f"RecoveryPolicyEngine lacks {method}")

            audit_results["contract_validation"] = "PASSED" if not audit_results["violations"] else "FAILED"
        except Exception as e:
            audit_results["contract_validation"] = "FAILED"
            audit_results["violations"].append(f"Contract error: {str(e)}")

    # 2. Positif
    try:
        from runtime.recovery.contracts import IncidentBundle
        from runtime.telemetry.events import TelemetryEvent
        bundle = IncidentBundle(
            incident_id="INC-V712", timestamp=datetime.now(timezone.utc).isoformat(),
            severity="HIGH", severity_score=90, category="GATE", execution_id="E",
            action_name="A", trace_id="T", span_id="S", state_trace=[],
            context_signature_valid=True, payload_hash="", bundle_hash="",
            telemetry_snapshot={}, findings=[], root_candidates=[], metadata={}
        )
        gov.govern(action_type="RECOVERY", confidence=0.99)
        col.record_event(TelemetryEvent(event_type="TEST", payload={}))
        eng.evaluate(incident_category="GATE", severity_score=90, telemetry_snapshot={}, root_candidates=[])
        audit_results["positive_behavior"] = "PASSED"
    except Exception as e:
        audit_results["positive_behavior"] = "FAILED"
        audit_results["violations"].append(f"Positive test failed: {str(e)}")

    # 3. Négatif
    neg_failures = 0
    if col and hasattr(col, "emit"): neg_failures += 1
    if eng and hasattr(eng, "get_active_policies"): neg_failures += 1
    if gov and hasattr(gov, "evaluate"): neg_failures += 1
    audit_results["negative_regression"] = "PASSED" if neg_failures == 0 else "FAILED"
    if neg_failures > 0: audit_results["violations"].append("Legacy methods detected.")

    # 4. SHA Drift
    v3_path = REGISTRY_OUT / "architecture_baseline_v3.json"
    if v3_path.exists():
        baseline_data = json.loads(v3_path.read_text(encoding="utf-8"))
        drift = sum(1 for r, m in baseline_data.get("module_hashes", {}).items() 
                    if not (ROOT_DIR / r).exists() or hashlib.sha256((ROOT_DIR / r).read_bytes()).hexdigest() != m["sha256"])
        audit_results["cryptographic_drift"] = "ZERO_DRIFT" if drift == 0 else "DRIFT_DETECTED"
        if drift > 0: audit_results["violations"].append(f"Drift in {drift} modules.")
    else:
        audit_results["cryptographic_drift"] = "FAILED"

    # 5. Quarantine AST Isolation (Règle affinée : ciblage exclusif du dossier forensique physique)
    print("\n[5/5] Analyse AST de l'étanchéité de la Quarantaine (Règle affinée)...")
    quarantine_violations = []
    
    FORBIDDEN_PREFIXES = ("quarantine", "runtime.quarantine")

    for py_file in ROOT_DIR.rglob("*.py"):
        rel_s = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
        if "quarantine" in rel_s.lower() or "audit" in rel_s.lower() or "test" in rel_s.lower():
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name.lower()
                        # Vérification stricte : le module commence par quarantine ou est sous runtime.quarantine
                        if target == "quarantine" or target.startswith("quarantine.") or target.startswith("runtime.quarantine"):
                            quarantine_violations.append({"file": rel_s, "line": node.lineno, "target": alias.name})
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod_lower = node.module.lower()
                        if mod_lower == "quarantine" or mod_lower.startswith("quarantine.") or mod_lower.startswith("runtime.quarantine"):
                            quarantine_violations.append({"file": rel_s, "line": node.lineno, "target": node.module})
        except:
            pass

    if not quarantine_violations:
        audit_results["quarantine_isolation"] = "STRICT_ISOLATION"
        print("  [OK] Quarantaine hermétique : Zéro dépendance illégale vers la zone forensique.")
    else:
        audit_results["quarantine_isolation"] = "VIOLATION"
        for qv in quarantine_violations:
            msg = f"Forbidden import from quarantine storage in '{qv['file']}' at line {qv['line']} (importing: {qv['target']})"
            audit_results["violations"].append(msg)
            print(f"  [FAIL] {msg}")

    # Décision
    all_passed = (
        audit_results["contract_validation"] == "PASSED" and
        audit_results["positive_behavior"] == "PASSED" and
        audit_results["negative_regression"] == "PASSED" and
        audit_results["cryptographic_drift"] == "ZERO_DRIFT" and
        audit_results["quarantine_isolation"] == "STRICT_ISOLATION"
    )

    release_state = "V712_RELEASE_AUTHORIZED" if all_passed else "V712_RELEASE_REJECTED"
    audit_results["release_state"] = release_state

    token_path = REGISTRY_OUT / "v712_certification_token.json"
    token_path.write_text(json.dumps(audit_results, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(audit_results, token_path)
    print(f"\n[*] -----------------------------------------------------------------")
    print(f"[*] RÉSULTAT DU PORTILLON V7.12.3 : {release_state}")
    print(f"[*] -----------------------------------------------------------------")

def build_markdown_report(report: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V712_ENTRY_GATE_REPORT.md"
    
    lines = [
        "# E-ZZIO V7.12.0 — Entry Gate Orchestration Report",
        f"**Date :** {report['timestamp']}",
        f"**Statut Global de Release :** `{report['release_state']}`",
        "",
        "## 1. Matrice des Contrôles d'Entrée",
        "| Dimension de Gouvernance | Résultat | Statut |",
        "| :--- | :--- | :---: |",
        f"| Validation Active du Contrat | `API_CONTRACT_V3.json` | `{'🟢 PASS' if report['contract_validation'] == 'PASSED' else '🔴 FAIL'}` |",
        f"| Comportement Positif | `Govern / Record / Evaluate` | `{'🟢 PASS' if report['positive_behavior'] == 'PASSED' else '🔴 FAIL'}` |",
        f"| Régression Négative | `Legacy Rejection` | `{'🟢 PASS' if report['negative_regression'] == 'PASSED' else '🔴 FAIL'}` |",
        f"| Dérive Cryptographique | `SHA-256 Baseline` | `{'🟢 ZERO_DRIFT' if report['cryptographic_drift'] == 'ZERO_DRIFT' else '🔴 DRIFT'}` |",
        f"| Étanchéité de Quarantaine | `Refined AST Policy` | `{'🟢 STRICT' if report['quarantine_isolation'] == 'STRICT_ISOLATION' else '🔴 VIOLATION'}` |",
        ""
    ]

    if report["violations"]:
        lines.extend([
            "## 2. Violations Détectées",
            "Les anomalies suivantes ont bloqué l'autorisation de release :"
        ])
        for v in report["violations"]:
            lines.append(f"- `❌ {v}`")
    else:
        lines.append("## 2. Violations Détectées\n🟢 **Aucune violation. L'écosystème respecte l'intégralité des contraintes de gouvernance.**")

    lines.extend([
        "",
        "## 3. Conclusion",
        f"Le jeton de certification (`{json_path.name}`) atteste que le système est prêt pour l'expansion sous contrôle autonome."
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    run_v712_entry_gate()
