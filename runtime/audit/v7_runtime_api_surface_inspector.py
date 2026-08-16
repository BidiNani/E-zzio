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

def inspect_class_full(module_path: str, class_name: str) -> dict:
    data = {"target": f"{module_path}.{class_name}", "status": "FAILED", "init_params": {}, "methods": {}}
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        
        # 1. Paramètres du constructeur
        try:
            sig = inspect.signature(cls.__init__)
            for name, param in sig.parameters.items():
                if name == "self": continue
                data["init_params"][name] = {
                    "default": str(param.default) if param.default is not inspect.Parameter.empty else "REQUIRED",
                    "annotation": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "Any"
                }
        except Exception as e:
            data["init_params_error"] = str(e)

        # 2. Méthodes publiques et leurs signatures
        for m_name, m_func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if m_name.startswith("_"): continue
            try:
                m_sig = inspect.signature(m_func)
                m_params = [p.name for p in m_sig.parameters.values() if p.name != "self"]
                data["methods"][m_name] = m_params
            except:
                data["methods"][m_name] = "signature_error"

        data["status"] = "SUCCESS"
    except Exception as e:
        data["error"] = str(e)
    return data

def run_api_surface_inspection():
    print("[*] Démarrage de V7.11.5.4 — Runtime API Surface Inspector...")

    targets = [
        ("runtime.telemetry.collector", "TelemetryCollector"),
        ("runtime.telemetry.events", "TelemetryEvent"),
        ("runtime.recovery.contracts", "IncidentBundle"),
        ("runtime.recovery.decision.policies", "RecoveryPolicyEngine")
    ]

    inspection_results = []
    for mod_name, cls_name in targets:
        inspection_results.append(inspect_class_full(mod_name, cls_name))

    payload = {
        "timestamp": datetime.now().isoformat(),
        "api_surface": inspection_results
    }

    out_json = REGISTRY_OUT / "api_surface_inspection.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(payload, out_json)
    print(f"[OK] Inspection de surface terminée. Rapport : {REGISTRY_OUT / 'V7_11_5_4_API_SURFACE_REPORT.md'}")

def build_markdown_report(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_4_API_SURFACE_REPORT.md"
    surfaces = payload["api_surface"]
    
    lines = [
        "# E-ZZIO V7.11.5.4 — Runtime API Surface Inspection Report",
        f"**Date :** {payload['timestamp']}",
        "",
        "## 1. Cartographie des API de Production (Baseline V3)",
        "Inspection exacte des méthodes et signatures disponibles pour concevoir les adaptateurs de compatibilité :"
    ]

    for item in surfaces:
        lines.append(f"### 📌 `{item['target']}` *(Statut: {item['status']})*")
        if item["status"] == "SUCCESS":
            lines.append("**Paramètres du Constructeur (`__init__`) :**")
            for p_name, p_meta in item["init_params"].items():
                lines.append(f"- ` {p_name} ` (Défaut: `{p_meta['default']}`)")
            
            lines.append("\n**Méthodes Publiques et Arguments :**")
            if item["methods"]:
                for m_name, m_args in item["methods"].items():
                    args_str = ", ".join(m_args)
                    lines.append(f"- `{m_name}({args_str})`")
            else:
                lines.append("- *(Aucune méthode publique)*")
        else:
            lines.append(f"❌ **Erreur d'inspection :** `{item.get('error')}`")
        lines.append("")

    lines.extend([
        "## 2. Conclusion de l'Inspecteur de Surface",
        "Ce rapport fournit la vérité absolue des signatures exposées par le noyau. Il permet de bâtir la couche d'adaptation (`runtime/adapters/`) avec un alignement mathématique parfait, protégeant ainsi l'intégrité de la Baseline V3.",
        "",
        f"**Registre JSON brut :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown de surface API généré : {md_path.name}")

if __name__ == "__main__":
    run_api_surface_inspection()
