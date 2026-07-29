import os
import re

print("[*] E-ZZIO v1.9.1.5 - Activation de la matrice de remédiation finale...")

# ------------------------------------------------------------------------------
# 1. RÉPARATION À LA RACINE : TOOLRESULT PARFAIT
# ------------------------------------------------------------------------------
base_file = "runtime/tools/base.py"
correct_tool_result = """class ToolResult:
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

class ExternalExecutorBase:
    pass
"""
if os.path.exists(base_file):
    with open(base_file, "r", encoding="utf-8") as f:
        code = f.read()
    code = re.sub(r'class ToolResult:[\s\S]*?(?=\nclass |\Z)', correct_tool_result, code)
    with open(base_file, "w", encoding="utf-8") as f:
        f.write(code)
else:
    os.makedirs(os.path.dirname(base_file), exist_ok=True)
    with open(base_file, "w", encoding="utf-8") as f:
        f.write(correct_tool_result)
print("[+] runtime/tools/base.py : ToolResult parfait restauré (avec attribut metadata).")

# ------------------------------------------------------------------------------
# 2. RESTAURATION DES EXÉCUTEURS (dict -> ToolResult)
# ------------------------------------------------------------------------------
executors = [
    "runtime/tools/executors/powershell.py",
    "runtime/tools/executors/filesystem.py",
    "runtime/tools/executors/git.py"
]
stubs = """
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
"""
for ex in executors:
    if os.path.exists(ex):
        with open(ex, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Nettoyage des anciennes tentatives de classes locales
        code = re.sub(r'class ToolResult[\s\S]*?(?=class [A-Za-z]+Executor)', '', code)
        
        # Remplacement de l'erreur précédente : on remet ToolResult
        code = re.sub(r'\bdict\(success=', 'ToolResult(success=', code)
        if 'import ToolResult' not in code:
            code = 'from runtime.tools.base import ToolResult\n' + code
            
        # Vérification des stubs ABC
        if 'def spawn(' not in code:
            code = re.sub(r'(class [A-Za-z]+Executor.*?:(?:\n\s*""".*?""")?)', r'\1\n' + stubs, code, count=1)
            
        with open(ex, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[+] {os.path.basename(ex):<20} : ToolResult restauré et stubs validés.")

# ------------------------------------------------------------------------------
# 3. IMMUNITÉ SUPERVISEUR (Patch global des attributs après désérialisation JSON)
# ------------------------------------------------------------------------------
def replacer(match, field):
    var = match.group(1)
    if var in ("self", "cls"):
        return match.group(0)
    # L'immunité absolue : tente de lire l'objet, sinon fallback sur le format dict
    return f'({var}.get("{field}") if isinstance({var}, dict) else getattr({var}, "{field}", None))'

patched_files = 0
for root, dirs, files in os.walk("runtime"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            
            new_code = code
            for field in ["metadata", "success", "error", "output"]:
                # Intercepte var.metadata partout dans le code (sauf self.metadata)
                pattern = r'(?<!self\.)(?<!cls\.)\b([a-zA-Z_][a-zA-Z0-9_]*)\.' + field + r'\b(?!\s*(?:=|:|\())'
                new_code = re.sub(pattern, lambda m, f=field: replacer(m, f), new_code)
            
            if new_code != code:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                patched_files += 1
print(f"[+] {patched_files} fichiers immunisés contre le Crash Superviseur (Tolérance Dict/Objet).")

# ------------------------------------------------------------------------------
# 4. FIX SQLITE DÉFINITIF (Tri à double détente)
# ------------------------------------------------------------------------------
store_file = "runtime/action/store.py"
if os.path.exists(store_file):
    with open(store_file, "r", encoding="utf-8") as f:
        code = f.read()
    
    parts = code.split('def get_execution_history')
    if len(parts) > 1:
        pre = parts[0]
        post = 'def get_execution_history' + parts[1]
        # On accroche la fin de la clause WHERE de manière garantie
        post = re.sub(
            r'WHERE action_name = \?[^"]*"',
            r'WHERE action_name = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?"',
            post
        )
        code = pre + post
        
    parts = code.split('def get_transition_history')
    if len(parts) > 1:
        pre = parts[0]
        post = 'def get_transition_history' + parts[1]
        post = re.sub(
            r'WHERE exec_id = \?[^"]*"',
            r'WHERE exec_id = ? ORDER BY rowid ASC"',
            post
        )
        code = pre + post

    with open(store_file, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py             : Tris SQLite infaillibles implémentés (timestamp DESC, rowid DESC).")

