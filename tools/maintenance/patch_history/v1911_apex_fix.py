import os
import re

print("[*] E-ZZIO v1.9.1.1 - Déploiement du correctif Apex (Zéro Défaut)...")

# ------------------------------------------------------------------------------
# 1. SQLITE STORE FIX (Timestamp Sort & RowID Sort Infaillible)
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Get Execution History: Ordre STRICT par timestamp le plus récent
    code = re.sub(
        r'"SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = \?.*?"',
        '"SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp FROM execution_ledger WHERE action_name = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?"',
        code, flags=re.DOTALL | re.IGNORECASE
    )

    # Get Transition History: Ordre STRICT chronologique
    code = re.sub(
        r'"SELECT from_state, to_state, timestamp, signature FROM state_transitions WHERE exec_id = \?.*?"',
        '"SELECT from_state, to_state, timestamp, signature FROM state_transitions WHERE exec_id = ? ORDER BY rowid ASC"',
        code, flags=re.DOTALL | re.IGNORECASE
    )

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py : Tris SQL infaillibles appliqués (timestamp DESC, rowid ASC).")

# ------------------------------------------------------------------------------
# 2. UNIVERSAL RESULT POUR LES EXÉCUTEURS (Anti-crash Superviseur)
# ------------------------------------------------------------------------------
# Ce composant caméléon agit à la fois comme un dictionnaire et comme un objet
# avec des attributs. Il immunise contre l'erreur "dict object has no attribute metadata"
UNIVERSAL_RESULT_CODE = """
class ToolResult(dict):
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        super().__init__()
        self["success"] = success
        self["output"] = output
        self["error"] = error
        self["metadata"] = metadata or {}
        self.update(kwargs)
        
    def __getattr__(self, key):
        if key in self:
            return self[key]
        if key == "metadata":
            return {}
        raise AttributeError(f"'ToolResult' object has no attribute '{key}'")
        
    def __setattr__(self, key, value):
        self[key] = value
"""

executors = [
    "runtime/tools/executors/powershell.py",
    "runtime/tools/executors/filesystem.py",
    "runtime/tools/executors/git.py"
]

for path in executors:
    if not os.path.exists(path): continue
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # Nettoyage chirurgical des anciens faux stubs (try/except ou class ToolResult basiques)
    exec_match = re.search(r'class\s+[A-Za-z]+Executor', code)
    if exec_match:
        exec_pos = exec_match.start()
        mock_start = code.find('try:\n    from runtime.tools.base import ToolResult')
        if mock_start == -1:
            mock_start = code.find('try:\n    from runtime.external.base import ToolResult')
        if mock_start == -1:
            mock_start = code.find('class ToolResult:')
            
        if mock_start != -1 and mock_start < exec_pos:
            code = code[:mock_start] + code[exec_pos:]
    
    # Injection propre de la classe Caméléon
    if "class ToolResult(dict):" not in code:
        match = re.search(r'from runtime\.external\.base import ExternalExecutorBase\n', code)
        if match:
            pos = match.end()
            code = code[:pos] + "\n" + UNIVERSAL_RESULT_CODE + "\n" + code[pos:]
        else:
            code = UNIVERSAL_RESULT_CODE + "\n" + code

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[+] {os.path.basename(path):<20} : ToolResult Universel injecté (Anti-Crash Superviseur).")

