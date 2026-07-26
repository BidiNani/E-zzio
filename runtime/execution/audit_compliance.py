import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import importlib
import pkgutil
import inspect
import runtime.tools.executors
from runtime.contracts.tool_result import ToolResult
from runtime.contracts import tool_result as canonical

print("[*] Scan de sys.modules à la recherche de classes ToolResult fantômes...")
for name, module in sys.modules.items():
    if "tool_result" in name:
        print(f"  -> Module chargé en mémoire : {name} ({module})")

# 1. Vérification stricte du module
tr_module = ToolResult.__module__
print(f"[*] Vérification du module ToolResult chargé : {tr_module}")
if tr_module != "runtime.contracts.tool_result":
    print(f"FAIL: Collision critique ! ToolResult pointe vers '{tr_module}' au lieu de 'runtime.contracts.tool_result'")
    sys.exit(10)

# 2. Vérification de l'identité mémoire (anti-doublon cache)
if ToolResult is not canonical.ToolResult:
    print("FAIL: Multiple ToolResult class objects detected in memory space.")
    sys.exit(11)

def run_audit():
    package = runtime.tools.executors
    print("\n=============================================")
    print("    CONTRACT FORTRESS COMPLIANCE REPORT      ")
    print("=============================================\n")

    all_compliant = True
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                
                if isinstance(obj, type) and hasattr(obj, "TOOL_NAME"):
                    tool_name = getattr(obj, "TOOL_NAME", "UNKNOWN")
                    issues = []

                    # A. Décorateur
                    if not getattr(obj, "__is_executor__", False):
                        issues.append("Missing @executor decorator")
                    
                    # B. Signature execute()
                    if hasattr(obj, "execute"):
                        sig = inspect.signature(obj.execute)
                        param_names = list(sig.parameters.keys())
                        if "context" not in param_names:
                            issues.append("execute() missing 'context' parameter in signature")
                    else:
                        issues.append("Missing execute() method")

                    # C. Contrat bi-directionnel et métadonnées
                    meta = getattr(obj, "__executor_metadata__", {})
                    if not meta.get("contract_version"):
                        issues.append("Missing contract_version metadata")

                    contract = getattr(obj, "__executor_contract__", {})
                    if contract.get("input") != "ExecutionContext":
                        issues.append("Invalid or missing input contract ('ExecutionContext' expected)")
                    if contract.get("output") != "ToolResult":
                        issues.append("Invalid or missing output contract ('ToolResult' expected)")

                    if issues:
                        print(f"{tool_name:<30} [FAIL]")
                        for issue in issues:
                            print(f"  -> {issue}")
                        all_compliant = False
                    else:
                        print(f"{tool_name:<30} [PASS]")
                        
        except Exception as e:
            print(f"{module_name:<30} [CRASH] : {e}")
            all_compliant = False

    print("\n=============================================")
    if all_compliant:
        print("RESULT : 100% COMPLIANT. SYSTEM READY.")
        sys.exit(0)
    else:
        print("RESULT : COMPLIANCE FAILURES DETECTED.")
        sys.exit(1)

if __name__ == '__main__':
    run_audit()