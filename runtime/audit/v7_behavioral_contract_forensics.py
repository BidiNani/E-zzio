import os
import sys
import json
import inspect
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def inspect_target(module_path: str, class_name: str) -> dict:
    result = {"target": f"{module_path}.{class_name}", "status": "FAILED", "signature": {}, "public_methods": []}
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        
        # Inspection de la signature du constructeur
        sig = inspect.signature(cls.__init__)
        params = {}
        for name, param in sig.parameters.items():
            if name == "self": continue
            params[name] = {
                "kind": str(param.kind),
                "default": str(param.default) if param.default is not inspect.Parameter.empty else "REQUIRED"
            }
        result["signature"] = params

        # Extraction des méthodes publiques
        methods = [m[0] for m in inspect.getmembers(cls, predicate=inspect.isfunction) if not m[0].startswith("_")]
        result["public_methods"] = methods
        result["status"] = "SUCCESS"
    except Exception as e:
        result["error"] = str(e)
    return result

def run_contract_forensics():
    print("[*] Démarrage de V7.11.5.1 — Behavioral Contract Forensics...")

    targets = [
        ("runtime.recovery.contracts", "IncidentBundle"),
        ("runtime.telemetry.events", "TelemetryEvent"),
        ("runtime.recovery.decision.policies", "RecoveryPolicyEngine")
    ]

    forensics_data = []
    for mod_name, cls_name in targets:
        forensics_data.append(inspect_target(mod_name, cls_name))

    payload = {
        "timestamp": datetime.now().isoformat(),
        "forensics_analysis": forensics_data
    }

    out_json = REGISTRY_OUT / "behavioral_symbols.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(payload, out_json)
    print(f"[OK] Forensique des contrats terminée. Rapport : {REGISTRY_OUT / 'V7_11_5_1_CONTRACT_DIFF_REPORT.md'}")

def build_markdown_report(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_1_CONTRACT_DIFF_REPORT.md"
    analyses = payload["forensics_analysis"]
    
    lines = [
        "# E-ZZIO V7.11.5.1 — Behavioral Contract Diff & Forensics Report",
        f"**Date :** {payload['timestamp']}",
        "",
        "## 1. Vérité des Signatures des Classes Cibles",
        "Analyse par introspection des contrats réels exposés par le code de production :"
    ]

    for item in analyses:
        lines.append(f"### 📌 `{item['target']}` *(Statut: {item['status']})*")
        if item["status"] == "SUCCESS":
            lines.append("**Paramètres du constructeur (`__init__`) :**")
            for p_name, p_meta in item["signature"].items():
                lines.append(f"- ` {p_name} ` (Défaut: `{p_meta['default']}`)")
            
            lines.append("\n**Méthodes publiques disponibles :**")
            if item["public_methods"]:
                for m in item["public_methods"]:
                    lines.append(f"- `{m}()`")
            else:
                lines.append("- *(Aucune méthode publique explicite hors constructeur)*")
        else:
            lines.append(f"❌ **Erreur d'inspection :** `{item.get('error')}`")
        lines.append("")

    lines.extend([
        "## 2. Conclusion de l'Analyse Forensique",
        "Ce rapport expose la signature exacte attendue par chaque composant. Il servira de base de référence pour aligner proprement les tests comportementaux ou adapter les adaptateurs d'API sans toucher au cœur fonctionnel.",
        "",
        f"**Registre JSON brut :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de forensique généré : {md_path.name}")

if __name__ == "__main__":
    run_contract_forensics()
