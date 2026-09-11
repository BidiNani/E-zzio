from __future__ import annotations
import ast
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 1. Périmètre opérationnel strict (exclusion des scripts annexes/tests/archives)
OPERATIONAL_FILES = {
    "discord": [
        PROJECT_ROOT / "core" / "integrations" / "discord" / "discord_client.py",
        PROJECT_ROOT / "runtime" / "bidi" / "presence.py",
        PROJECT_ROOT / "core" / "agent" / "coding_agent_loop.py",
        PROJECT_ROOT / "core" / "ezzio_master.py",
    ],
    "fastapi": [
        PROJECT_ROOT / "runtime" / "external" / "ezzio_app.py",
        PROJECT_ROOT / "web_server.py",
    ],
    "cli": [
        PROJECT_ROOT / "ezzio_cli.py",
        PROJECT_ROOT / "run_ezzio.py",
    ],
    "fabric_core": [
        PROJECT_ROOT / "core" / "models" / "fabric.py",
        PROJECT_ROOT / "core" / "intents" / "fabric_connector.py",
        PROJECT_ROOT / "core" / "cognition" / "cognitive_gateway.py",
        PROJECT_ROOT / "core" / "agent" / "agent_provider.py",
    ]
}

def analyze_file_chain(path: Path, label: str):
    if not path.exists():
        print(f"  [ABSENT] {path.relative_to(PROJECT_ROOT)}")
        return

    rel = path.relative_to(PROJECT_ROOT)
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except Exception as e:
        print(f"  [ERREUR PARSING] {rel}: {e}")
        return

    print(f"\n--- [{label.upper()}] {rel} ---")
    
    # Inspection des instanciations et assignations clés
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            target_str = ast.unparse(node.targets[0])
            val_str = ast.unparse(node.value)
            
            # Module-level assignments of critical components
            if any(k in val_str for k in ("CognitiveGateway", "AgentProviderAdapter", "EzzioMaster", "build_fabric", "AutonomousModelFabric")):
                print(f"  Ligne {node.lineno:3d} | ASSIGNATION : {target_str} = {val_str}")
                
        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                
            if func_name in {"add_cog", "setup_hook", "lifespan", "run", "start"}:
                print(f"  Ligne {node.lineno:3d} | POINT D'ATTACHE / HOOK : {ast.unparse(node)}")

def main():
    print("=" * 80)
    print(" E-ZZIO — OPERATIONAL BOOTSTRAP TRACE & INJECTION POINTS (GATE v6.45.29)")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    for domain, paths in OPERATIONAL_FILES.items():
        print(f"\n{'#' * 30} DOMAINE : {domain.upper()} {'#' * 30}")
        for p in paths:
            analyze_file_chain(p, domain)

    print("\n" + "=" * 80)
    print(" AUDIT v6.45.29 TERMINÉ — EXTRACTION DES CHAINES OPÉRATIONNELLES")
    print("=" * 80)

if __name__ == "__main__":
    main()
