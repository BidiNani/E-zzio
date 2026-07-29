import os
import re
import sys

print("[*] Lancement de la réparation chirurgicale v1.9.1.6-R...")

# ------------------------------------------------------------------------------
# A. NETTOYAGE DES CORRUPTIONS SYNTAXIKES ("context.(...")
# ------------------------------------------------------------------------------
for root, dirs, files in os.walk("runtime"):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            with open(p, "r", encoding="utf-8") as file:
                content = file.read()
            
            if "context.(" in content or ".(" in content:
                # Restauration propre de la syntaxe d'accès
                clean_content = re.sub(r'context\.\(state\.get\("metadata"\)[^\)]+\)', 'context.state.metadata', content)
                clean_content = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.\(([a-zA-Z0-9_\.]+)\.get\("[^"]+"\)[^\)]+\)', r'\1.\2', clean_content)
                with open(p, "w", encoding="utf-8") as file:
                    file.write(clean_content)
                print(f"[+] Restauration syntaxique effectuée : {p}")

# ------------------------------------------------------------------------------
# B. INJECTION SÉCURISÉE DU TOOLRESULT HYBRIDE DANS BASE.PY (SANS ÉCRASEMENT)
# ------------------------------------------------------------------------------
def patch_base_file(base_path):
    if not os.path.exists(base_path):
        return
    with open(base_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Si ToolResult n'a pas encore de support dict (__getitem__)
    if "class ToolResult" in code and "__getitem__" not in code:
        hybrid_methods = """
    def __getitem__(self, key):
        return getattr(self, key, None)
    def __setitem__(self, key, value):
        setattr(self, key, value)
        if hasattr(self, 'metadata') and isinstance(self.metadata, dict):
            self.metadata[key] = value
    def get(self, key, default=None):
        return getattr(self, key, default)
    def __contains__(self, key):
        return hasattr(self, key)
"""
        # Insertion des méthodes d'accès hybrides directement dans la classe existante
        code = re.sub(
            r'(class ToolResult.*?:[\s\S]*?def __init__[\s\S]*?\n)(\s*)(def |\Z)',
            r'\1' + hybrid_methods + r'\n\2\3',
            code,
            count=1
        )
        with open(base_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[+] ToolResult hybride injecté sans perte dans : {base_path}")

patch_base_file("runtime/tools/base.py")
patch_base_file("runtime/external/base.py")

# ------------------------------------------------------------------------------
# C. NORMALISATION SQLITE NON-DESTRUCTIVE DANS STORE.PY
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # On remplace proprement les requêtes d'historique ciblées sans toucher au reste
    # 1. execution_ledger : doit garantir timestamp DESC, rowid DESC
    code = re.sub(
        r'FROM\s+execution_ledger\s+WHERE\s+action_name\s+=\s+\?[^"]*?"',
        'FROM execution_ledger WHERE action_name = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?"',
        code, flags=re.IGNORECASE
    )
    
    # 2. state_transitions : doit conserver l'ordre chronologique natif
    code = re.sub(
        r'FROM\s+state_transitions\s+WHERE\s+exec_id\s+=\s+\?[^"]*?"',
        'FROM state_transitions WHERE exec_id = ? ORDER BY rowid ASC"',
        code, flags=re.IGNORECASE
    )

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py : Reconstitution ciblée des clauses SQL effectuée.")

