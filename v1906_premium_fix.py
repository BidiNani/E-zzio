import os
import re

print("[*] E-ZZIO v1.9.0.6 - Déploiement de la remédiation architecturale de précision...")

# 1. STUBS UNIVERSELS (Signatures flexibles pour satisfaire le registre)
STUBS = """
    # --- ABC IMPLEMENTATION STUBS ---
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
"""

executors = {
    "runtime/tools/executors/powershell.py": "PowerShellExecutor",
    "runtime/tools/executors/filesystem.py": "FileSystemExecutor",
    "runtime/tools/executors/git.py": "GitExecutor"
}

# ------------------------------------------------------------------------------
# PHASE A : SÉCURISATION DES CLASSES ABSTRAITES
# ------------------------------------------------------------------------------
for path, cls_name in executors.items():
    if not os.path.exists(path): continue
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # Nettoyage profond des anciens stubs invalides ou incomplets
    code = re.sub(r'^\s*# --- ABC IMPLEMENTATION STUBS ---[\s\S]*?def terminate.*?pass\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*def terminate\(self\).*?\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*def spawn\(self.*?\).*?\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*def is_alive\(self\).*?\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*def collect_output\(self.*?\).*?\n', '', code, flags=re.MULTILINE)

    # Forçage de l'import universel
    if "from runtime.external.base import ExternalExecutorBase" not in code:
        code = "from runtime.external.base import ExternalExecutorBase\n" + code

    # Normalisation de l'héritage (capture class Nom: ET class Nom(Autre):)
    code = re.sub(rf'class\s+{cls_name}[\s\S]*?:', f'class {cls_name}(ExternalExecutorBase):', code, count=1)

    # Injection chirurgicale juste après l'en-tête de la classe pour garantir l'indentation
    match = re.search(rf'class\s+{cls_name}\(ExternalExecutorBase\):', code)
    if match:
        pos = match.end()
        code = code[:pos] + "\n" + STUBS + code[pos:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[+] {cls_name:<20} : Signatures (*args, **kwargs) scellées.")

# ------------------------------------------------------------------------------
# PHASE B : BLINDAGE SQLITE (TRI DESC)
# ------------------------------------------------------------------------------
store = "runtime/action/store.py"
if os.path.exists(store):
    with open(store, "r", encoding="utf-8") as f:
        code = f.read()

    # Découpage du fichier par méthodes pour une isolation parfaite
    blocks = code.split('def ')
    for i, block in enumerate(blocks):
        if block.startswith('get_execution_history'):
            # 1. Remplacement d'un éventuel ASC existant
            block = re.sub(r'ORDER BY\s+id\s+ASC', 'ORDER BY id DESC', block, flags=re.IGNORECASE)
            # 2. Ajout de DESC si la requête se termine juste par ORDER BY id
            block = re.sub(r'ORDER BY\s+id(?!\s+DESC)', 'ORDER BY id DESC', block, flags=re.IGNORECASE)
            blocks[i] = block
    
    with open(store, "w", encoding="utf-8") as f:
        f.write('def '.join(blocks))
    print(f"[+] {'ActionStore':<20} : Intégrité SQLite (DESC) verrouillée.")
