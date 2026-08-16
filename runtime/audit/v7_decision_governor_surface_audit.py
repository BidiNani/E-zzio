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

def inspect_governor():
    print("[*] Démarrage de V7.11.5.9 — Decision Governor Surface Audit...")
    
    result = {"target": "runtime.recovery.decision.governor.DecisionGovernor", "status": "FAILED", "init_params": {}, "methods": {}}
    
    try:
        mod = __import__("runtime.recovery.decision.governor", fromlist=["DecisionGovernor"])
        cls = getattr(mod, "DecisionGovernor")
        
        # 1. Introspection du constructeur
        try:
            sig = inspect.signature(cls.__init__)
            for name, param in sig.parameters.items():
                if name == "self": continue
                result["init_params"][name] = {
                    "default": str(param.default) if param.default is not inspect.Parameter.empty else "REQUIRED",
                    "annotation": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "Any"
                }
        except Exception as e:
            result["init_params_error"] = str(e)

        # 2. Introspection des méthodes publiques
        for m_name, m_func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if m_name.startswith("_"): continue
            try:
                m_sig = inspect.signature(m_func)
                m_params = []
                for p_name, p_param in m_sig.parameters.items():
                    if p_name == "self": continue
                    default_val = f"={p_param.default}" if p_param.default is not inspect.Parameter.empty else ""
                    m_params.append(f"{p_name}{default_val}")
                result["methods"][m_name] = m_params
            except Exception as me:
                result["methods"][m_name] = f"error: {str(me)}"

        result["status"] = "SUCCESS"
    except Exception as e:
        result["error"] = str(e)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "decision_governor_inspection": result
    }

    out_json = REGISTRY_OUT / "decision_governor_surface.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown_report(payload, out_json)
    print(f"[OK] Audit de surface du gouverneur terminé. Rapport : {REGISTRY_OUT / 'V7_11_5_9_GOVERNOR_SURFACE_REPORT.md'}")

def build_markdown_report(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_5_9_GOVERNOR_SURFACE_REPORT.md"
    item = payload["decision_governor_inspection"]
    
    lines = [
        "# E-ZZIO V7.11.5.9 — Decision Governor Surface Report",
        f"**Date :** {payload['timestamp']}",
        f"**Cible inspectée :** `{item['target']}`",
        f"**Statut :** `{item['status']}`",
        "",
        "## 1. Paramètres du Constructeur (`__init__`)"
    ]

    if item["status"] == "SUCCESS":
        if item["init_params"]:
            for p_name, p_meta in item["init_params"].items():
                lines.append(f"- ` {p_name} ` (Défaut: `{p_meta['default']}`)")
        else:
            lines.append("- *Aucun paramètre requis (constructeur vide).*")

        lines.extend([
            "",
            "## 2. Méthodes Publiques et Signatures Exactes",
            "Voici les véritables points d'entrée exposés par le DecisionGovernor :"
        ])

        if item["methods"]:
            for m_name, m_args in item["methods"].items():
                args_str = ", ".join(m_args)
                lines.append(f"- `{m_name}({args_str})`")
        else:
            lines.append("- *(Aucune méthode publique détectée)*")
    else:
        lines.append(f"❌ **Erreur d'introspection :** `{item.get('error')}`")

    lines.extend([
        "",
        "## 3. Conclusion de l'Inspecteur",
        "Ce rapport lève l'ambiguïté sur la manière d'interagir avec le DecisionGovernor, permettant d'aligner définitivement le harnais de test V7.11.5.x.",
        "",
        f"**Registre JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path.name}")

if __name__ == "__main__":
    inspect_governor()
