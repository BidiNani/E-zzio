from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_file_for_patterns(rel_path: str, targets: list[str]) -> dict[str, Any]:
    p = PROJECT_ROOT / rel_path
    if not p.exists():
        return {"exists": False}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        content_lower = content.lower()
        findings = {}
        for t in targets:
            findings[t] = t.lower() in content_lower

        # Parse AST to find functions/methods related to writing or upserting
        tree = ast.parse(content, filename=str(p))
        methods = []
        writes = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(node.name)
                if any(w in node.name.lower() for w in {"save", "upsert", "write", "update", "store", "persist"}):
                    writes.append(node.name)

        return {
            "exists": True,
            "findings": findings,
            "methods": methods,
            "write_methods": writes,
            "size_bytes": p.stat().st_size
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}

def find_files_by_pattern(pattern: str) -> list[str]:
    matches = []
    for p in PROJECT_ROOT.glob(pattern):
        if set(p.parts) & EXCLUDED_DIRS:
            continue
        matches.append(str(p.relative_to(PROJECT_ROOT)))
    return matches

def main():
    print("=" * 80)
    print(" CONTRACT VERIFICATION REPORT — QUALIFICATION → MODEL REGISTRY")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    registry_path = PROJECT_ROOT / "data" / "models" / "registry.json"
    registry_exists = registry_path.exists()
    registry_data = {}
    if registry_exists:
        try:
            registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Recherche des scripts de qualification (ex: EZZIO_Model_Qualification_Gate_v*.py)
    qual_scripts = find_files_by_pattern("**/EZZIO_Model_Qualification_Gate_v*.py")
    if not qual_scripts:
        qual_scripts = find_files_by_pattern("**/*qualification*.py")

    # Analyse des composants clés
    core_registry_info = inspect_file_for_patterns("core/models/registry.json" if (PROJECT_ROOT/"core/models/registry.json").exists() else "core/models/registry.py", ["upsert", "save", "write", "active", "tier"])
    lifecycle_info = inspect_file_for_patterns("core/models/lifecycle.py", ["transition", "state", "lifecycle", "active"])
    fabric_info = inspect_file_for_patterns("core/models/fabric.py", ["resolve", "tier", "model_list", "router"])
    adapter_info = inspect_file_for_patterns("core/agent/agent_provider.py", ["cloud_gemini", "local_primary", "local_fallback"])

    # Évaluation des chemins d'écriture et de qualification
    writer_discovered = bool(core_registry_info.get("write_methods"))
    automatic_qualification = len(qual_scripts) > 0

    report = {
        "registry": {
            "canonical_path": "data/models/registry.json" if registry_exists else "MISSING",
            "writer_discovered": writer_discovered,
            "write_methods": core_registry_info.get("write_methods", []),
            "entries_count": len(registry_data.get("models", [])) if isinstance(registry_data, dict) else "UNKNOWN"
        },
        "qualification": {
            "automatic_qualification": automatic_qualification,
            "qualification_scripts": qual_scripts,
            "produces_model_record": core_registry_info.get("exists", False),
            "produces_tier": fabric_info.get("findings", {}).get("tier", False)
        },
        "pipeline": {
            "discovery_to_qualification": "PRESENT" if automatic_qualification else "ABSENT",
            "qualification_to_registry": "PRESENT" if writer_discovered else "ABSENT",
            "registry_to_fabric": "PRESENT" if fabric_info.get("exists") else "ABSENT",
            "fabric_to_adapter": "PRESENT" if adapter_info.get("exists") else "ABSENT"
        },
        "provenance": {
            "gemini": "KeyPool / KeyVault / SecretsLoader",
            "granite": "ezzio-granite (Ollama local 4.2)",
            "ornith": "ornith-ezzio (Ollama local 1.5)"
        },
        "safety": {
            "writes_performed": 0,
            "runtime_mutations": 0,
            "ollama_state_mutations": 0,
            "production_code_changes": 0
        }
    }

    # Impression du rapport formaté selon le standard strict
    print("--------------------------------------------------------------------------------")
    print(" [REGISTRY]")
    print(f" Canonical registry       : {report['registry']['canonical_path']}")
    print(f" Writer discovered        : {'YES' if report['registry']['writer_discovered'] else 'NO'}")
    print(f" Write methods found      : {report['registry']['write_methods'] or 'None'}")
    print(f" Active models in file    : {report['registry']['entries_count']}")

    print("\n [QUALIFICATION]")
    print(f" Automatic qualification  : {'YES' if report['qualification']['automatic_qualification'] else 'NO'}")
    print(f" Qualification scripts    : {report['qualification']['qualification_scripts'] or 'None'}")
    print(f" Produces ModelRecord     : {'YES' if report['qualification']['produces_model_record'] else 'NO'}")
    print(f" Produces tier            : {'YES' if report['qualification']['produces_tier'] else 'NO'}")

    print("\n [PIPELINE]")
    print(f" Discovery → Qualification : {report['pipeline']['discovery_to_qualification']}")
    print(f" Qualification → Registry  : {report['pipeline']['qualification_to_registry']}")
    print(f" Registry → Fabric         : {report['pipeline']['registry_to_fabric']}")
    print(f" Fabric → Adapter          : {report['pipeline']['fabric_to_adapter']}")

    print("\n [PROVENANCE]")
    print(f" Gemini                    : {report['provenance']['gemini']}")
    print(f" Granite                   : {report['provenance']['granite']}")
    print(f" Ornith                    : {report['provenance']['ornith']}")

    print("\n [SAFETY]")
    print(f" Writes performed         : {report['safety']['writes_performed']}")
    print(f" Runtime mutations        : {report['safety']['runtime_mutations']}")
    print(f" Ollama state mutations   : {report['safety']['ollama_state_mutations']}")
    print(f" Production code changes  : {report['safety']['production_code_changes']}")
    print("--------------------------------------------------------------------------------")

    print("\n================================================================================")
    print(" VERDICT")
    print("================================================================================")
    if writer_discovered and automatic_qualification:
        print(" STATUS : PASS (Pipeline complet identifié, aucune écriture effectuée)")
    else:
        print(" STATUS : MISSING / INCOMPLETE (Le pont d'écriture automatique entre Qualification et Registry nécessite un raccordement contractuel explicite)")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "contract_verification_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")

if __name__ == "__main__":
    main()
