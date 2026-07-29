import os
import re

print("[*] Début du patch Python sécurisé...")

# A. Nettoyage de la syntaxe corrompue context.(...)
for root, dirs, files in os.walk("runtime"):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try:
                with open(p, "r", encoding="utf-8") as file:
                    content = file.read()
                
                if "context.(" in content or ".(" in content:
                    content = re.sub(r'context\.\(state\.get\("metadata"\)[^\)]+\)', 'context.state.metadata', content)
                    with open(p, "w", encoding="utf-8") as file:
                        file.write(content)
                    print(f"[+] Correction syntaxique appliquée sur : {p}")
            except Exception as e:
                print(f"[-] Erreur de lecture/écriture sur {p}: {e}")

# B. Enrichissement non destructif de ToolResult dans base.py (si présent)
for base_path in ["runtime/tools/base.py", "runtime/external/base.py"]:
    if os.path.exists(base_path):
        try:
            with open(base_path, "r", encoding="utf-8") as f:
                code = f.read()
            
            if "class ToolResult" in code and "__getitem__" not in code:
                # Injection propre des méthodes dict-like
                hybrid_methods = "\n    def __getitem__(self, key):\n        return getattr(self, key, None)\n    def __setitem__(self, key, value):\n        setattr(self, key, value)\n    def get(self, key, default=None):\n        return getattr(self, key, default)\n    def __contains__(self, key):\n        return hasattr(self, key)\n"
                code = re.sub(
                    r'(class ToolResult.*?:[\s\S]*?def __init__[\s\S]*?\n)',
                    r'\1' + hybrid_methods,
                    code,
                    count=1
                )
                with open(base_path, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[+] Support hybride dict ajouté à ToolResult dans {base_path}")
        except Exception as e:
            print(f"[-] Erreur patch base.py: {e}")

# C. Sécurisation SQL dans store.py
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    try:
        with open(store_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Remplacement propre des clauses de tri pour éviter l'empilement
        code = re.sub(
            r'FROM\s+execution_ledger\s+WHERE\s+action_name\s+=\s+\?[^"]*?"',
            'FROM execution_ledger WHERE action_name = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?"',
            code, flags=re.IGNORECASE
        )
        code = re.sub(
            r'FROM\s+state_transitions\s+WHERE\s+exec_id\s+=\s+\?[^"]*?"',
            'FROM state_transitions WHERE exec_id = ? ORDER BY rowid ASC"',
            code, flags=re.IGNORECASE
        )

        with open(store_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("[+] store.py : Clauses SQL normalisées.")
    except Exception as e:
        print(f"[-] Erreur patch store.py: {e}")

print("[*] Patch Python terminé avec succès.")
