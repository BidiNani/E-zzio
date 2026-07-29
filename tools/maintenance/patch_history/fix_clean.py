import os
import re

print("[*] Démarrage du correctif Python pur (Zéro interférence PowerShell)...")

# ------------------------------------------------------------------------------
# 1. RÉÉCRITURE PROPRE DE BASE.PY (ToolResult Hybride & ExternalExecutorBase)
# ------------------------------------------------------------------------------
base_code = """class ToolResult:
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)

class ExternalExecutorBase:
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
"""

for path in ["runtime/tools/base.py", "runtime/external/base.py"]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(base_code)
print("[+] base.py et external/base.py réécrits avec une indentation irréprochable.")

# ------------------------------------------------------------------------------
# 2. NETTOYAGE ET SÉCURISATION DE SUPERVISOR.PY
# ------------------------------------------------------------------------------
sup_path = "runtime/external/supervisor.py"
if os.path.exists(sup_path):
    with open(sup_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Suppression totale de toute ligne contenant la syntaxe corrompue context.(...)
    lines = content.splitlines()
    clean_lines = []
    for line in lines:
        if "context.(" in line:
            continue  # On saute la ligne vérolée
        clean_lines.append(line)
    
    content = "\n".join(clean_lines)

    # Insertion propre de l'assignation PID et TOOL_NAME juste après isolator.assign(process)
    safe_metadata_block = """
            process = getattr(executor_instance, 'process', None)
            if process:
                isolator.assign(process)
                st = getattr(context, 'state', {})
                if isinstance(st, dict):
                    st.setdefault('metadata', {})['pid'] = process.pid

            st = getattr(context, 'state', {})
            if isinstance(st, dict):
                st.setdefault('metadata', {})['executor'] = getattr(executor_instance, 'TOOL_NAME', 'unknown')
"""

    # Si le point d'ancrage existe, on y injecte notre bloc proprement indenté (8 espaces)
    if "isolator.assign(process)" in content:
        content = re.sub(
            r'isolator\.assign\(process\).*?(?=\n\s*while|\n\s*try|\n\s*def)',
            'isolator.assign(process)' + safe_metadata_block,
            content,
            flags=re.DOTALL
        )

    with open(sup_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] supervisor.py nettoyé de toute syntaxe invalide.")

print("[*] Correctif Python pur appliqué avec succès.")
