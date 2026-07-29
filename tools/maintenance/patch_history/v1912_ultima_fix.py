import os
import re

print("[*] E-ZZIO v1.9.1.2 - Déploiement de la solution définitive...")

# ------------------------------------------------------------------------------
# 1. TOOLRESULT HYBRIDE (Pur Objet avec accès Dict, sans héritage dict)
# ------------------------------------------------------------------------------
PURE_TOOL_RESULT = """
class ToolResult:
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        for k, v in kwargs.items():
            setattr(self, k, v)
            
    def __getitem__(self, key):
        if hasattr(self, key): return getattr(self, key)
        raise KeyError(key)
        
    def get(self, key, default=None):
        return getattr(self, key, default)
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

    # Purge complète de l'ancien ToolResult (qu'il hérite de dict ou non)
    code = re.sub(r'class ToolResult[\s\S]*?(?=\nclass [A-Za-z]+Executor)', PURE_TOOL_RESULT + "\n", code)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[+] {os.path.basename(path):<20} : ToolResult converti en Pur Objet (Anti-crash Superviseur).")

# ------------------------------------------------------------------------------
# 2. SQLITE STORE : PURGE ET RÉÉCRITURE DU TRI
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Isolation parfaite de la méthode get_execution_history
    parts = code.split('def get_execution_history')
    if len(parts) > 1:
        pre = parts[0]
        post = 'def get_execution_history' + parts[1]
        
        # Trouver la fin de la méthode
        next_func = re.search(r'\n(?:def|class) ', post[len('def get_execution_history'):])
        if next_func:
            end_idx = len('def get_execution_history') + next_func.start()
            func_body = post[:end_idx]
            rest = post[end_idx:]
        else:
            func_body = post
            rest = ""
            
        # Purge agressive de tous les ORDER BY dans le bloc
        func_body = re.sub(r'\s*ORDER BY\s+[a-z0-9_,\s]+?(?=LIMIT|"|\')', ' ', func_body, flags=re.IGNORECASE)
        
        # Ajout du seul et unique ORDER BY autorisé
        func_body = re.sub(r'\s*LIMIT\b', ' ORDER BY rowid DESC LIMIT', func_body, flags=re.IGNORECASE)
        
        code = pre + func_body + rest
        
        with open(store_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[+] {'store.py':<20} : Tri SQLite verrouillé sur 'ORDER BY rowid DESC'.")

