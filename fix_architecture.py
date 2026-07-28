import os
import re
import sys

print("[*] Démarrage de l'analyse dynamique du code...")

# A. Trouver le VRAI module qui contient ExternalExecutorBase
real_module = None
for root, dirs, files in os.walk('runtime'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                if 'class ExternalExecutorBase' in file.read():
                    real_module = path.replace('.py', '').replace(os.sep, '.')
                    break
    if real_module:
        break

# Fallback : création du module s'il n'existe vraiment nulle part
if not real_module:
    print("[-] ExternalExecutorBase introuvable. Création de runtime.tools.base...")
    os.makedirs('runtime/tools', exist_ok=True)
    with open('runtime/tools/base.py', 'w', encoding='utf-8') as f:
        f.write("class ToolResult:\n    def __init__(self, success, output='', error=''):\n        self.success = success\n        self.output = output\n        self.error = error\n\nclass ExternalExecutorBase:\n    pass\n")
    real_module = 'runtime.tools.base'

print(f"[*] Module parent identifié : {real_module}")

# Vérifier si ToolResult est également fourni par ce module
has_tool_result = False
module_path = real_module.replace('.', os.sep) + '.py'
if os.path.exists(module_path):
    with open(module_path, 'r', encoding='utf-8') as f:
        if 'class ToolResult' in f.read():
            has_tool_result = True

# B. Corriger les exécuteurs avec le bon import
executors = [
    'runtime/tools/executors/filesystem.py',
    'runtime/tools/executors/powershell.py',
    'runtime/tools/executors/git.py'
]

for ex in executors:
    if os.path.exists(ex):
        with open(ex, 'r', encoding='utf-8') as f:
            content = f.read()

        # Nettoyage des imports ratés des itérations précédentes
        content = re.sub(r'from runtime\.tools\.base import.*?\n', '', content)
        content = re.sub(r'try:\s*from.*?\nexcept ImportError:.*?class ExternalExecutorBase:\s*pass\n?', '', content, flags=re.DOTALL)
        
        # Préparation du bon import
        imports = ["ExternalExecutorBase"]
        if 'ToolResult' in content and has_tool_result:
            imports.append("ToolResult")
            
        import_stmt = f"from {real_module} import {', '.join(imports)}\n"
        
        # Injection
        if f"from {real_module} import" not in content:
            content = import_stmt + content.lstrip()

        # Fallback local de ToolResult si absent du base module
        if 'ToolResult' in content and not has_tool_result and 'class ToolResult' not in content:
            content = "class ToolResult:\n    def __init__(self, success, output='', error=''): self.success = success; self.output = output; self.error = error\n\n" + content

        # Sécurisation stricte de l'héritage
        content = re.sub(r'class (\w+Executor)\(ExternalExecutorBase\):', r'class \1:', content)
        content = re.sub(r'class (\w+Executor):', r'class \1(ExternalExecutorBase):', content)

        with open(ex, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[+] {ex} -> héritage et imports corrigés.")

# C. Patch strict du SQLite Store
store_path = 'runtime/action/store.py'
if os.path.exists(store_path):
    with open(store_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    mode = None
    for i, line in enumerate(lines):
        if 'def get_execution_history' in line:
            mode = 'EXEC'
        elif 'def get_transition_history' in line:
            mode = 'TRANS'
        elif 'def ' in line and not line.strip().startswith('#'):
            mode = None

        if mode == 'EXEC' and 'ORDER BY' in line.upper():
            lines[i] = re.sub(r'ORDER BY (\w+)(?:\s+(?:ASC|DESC))?', r'ORDER BY \1 DESC', line, flags=re.IGNORECASE)
        elif mode == 'TRANS' and 'ORDER BY' in line.upper():
            lines[i] = re.sub(r'ORDER BY (\w+)(?:\s+(?:ASC|DESC))?', r'ORDER BY \1 ASC', line, flags=re.IGNORECASE)

    with open(store_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("[+] ActionStore -> Tris SQL (DESC / ASC) parfaitement verrouillés.")
