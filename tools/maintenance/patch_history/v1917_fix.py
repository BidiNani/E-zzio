import os
import re

print("[*] E-ZZIO v1.9.1.7 - Application des derniers correctifs d'interface...")

# ------------------------------------------------------------------------------
# 1. ENRICHISSEMENT DE OUTPUTGUARD (Méthodes d'alias de compatibilité)
# ------------------------------------------------------------------------------
guard_path = "runtime/external/output_guard.py"
if os.path.exists(guard_path):
    with open(guard_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Si les méthodes attendues par le superviseur manquent, on les ajoute sous forme d'alias
    aliases = """
    def get_output(self):
        if hasattr(self, 'output'): return self.output
        if hasattr(self, 'get_buffer'): return self.get_buffer()
        return getattr(self, '_buffer', '')

    def get_error(self):
        if hasattr(self, 'error'): return self.error
        return getattr(self, '_error', '')

    def is_success(self):
        if hasattr(self, 'success'): return self.success
        return True
"""
    if "def get_output" not in code:
        code = re.sub(r'(class OutputGuard.*?:[\s\S]*?def __init__[\s\S]*?\n)', r'\1' + aliases, code, count=1)
        with open(guard_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("[+] OutputGuard : Méthodes d'alias de compatibilité injectées.")

# ------------------------------------------------------------------------------
# 2. CORRECTION EXACTE DU SQLITE STORE (ORDER BY rowid DESC)
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # On cible explicitement la méthode get_execution_history et on force le rowid DESC
    def fix_history_query(match):
        func_text = match.group(0)
        # Supprimer tout ORDER BY existant dans cette fonction pour éviter les conflits
        func_text = re.sub(r'ORDER BY\s+[^"\']+', '', func_text, flags=re.IGNORECASE)
        # Injecter proprement le tri par rowid DESC juste avant le LIMIT ?
        func_text = re.sub(r'LIMIT\s+\?', 'ORDER BY rowid DESC LIMIT ?', func_text, flags=re.IGNORECASE)
        return func_text

    code = re.sub(r'def get_execution_history[\s\S]*?(?=\n    def |\nclass |\Z)', fix_history_query, code)

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py : get_execution_history calé sur ORDER BY rowid DESC.")

print("[*] Réparations v1.9.1.7 terminées.")
