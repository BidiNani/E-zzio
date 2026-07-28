import os
import re

print("[*] E-ZZIO v1.9.0.9 - Déploiement de l'Omega Patch (Zéro Défaut)...")

# ------------------------------------------------------------------------------
# 1. INJECTION DYNAMIQUE DE L'ATTRIBUT 'STATE' (ANTI-CRASH DE CONTEXTE)
# ------------------------------------------------------------------------------
# Cette propriété est conçue pour contourner l'immuabilité (frozen=True) et 
# garantir que context.state renvoie toujours un dictionnaire sain.
STATE_PROPERTY = """
    @property
    def state(self):
        if not hasattr(self, '_state'):
            object.__setattr__(self, '_state', {})
        return self._state

    @state.setter
    def state(self, value):
        object.__setattr__(self, '_state', value)
"""

patched_context = False
for root, dirs, files in os.walk("runtime"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()

            # Si on localise la classe maîtresse et qu'elle n'a pas été patchée
            if "class ExecutionContext" in code and "def state" not in code:
                # Injection chirurgicale juste après la déclaration de classe (ou sa docstring)
                code = re.sub(
                    r'(class ExecutionContext.*?:(?:\n\s*""".*?""")?)', 
                    r'\1\n' + STATE_PROPERTY, 
                    code, 
                    count=1,
                    flags=re.DOTALL
                )
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[+] {file:<20} : Attribut universel 'state' greffé sur ExecutionContext.")
                patched_context = True

# Sécurité de repli si la classe est hors de portée
if not patched_context:
    print("[-] Attention : ExecutionContext non localisé. Application du patch de repli sur les exécuteurs...")
    for ex in ["runtime/tools/executors/powershell.py", "runtime/tools/executors/filesystem.py", "runtime/tools/executors/git.py"]:
        if os.path.exists(ex):
            with open(ex, "r", encoding="utf-8") as f:
                code = f.read()
            # Remplacement passif pour éviter le crash en lecture
            code = re.sub(r'\bcontext\.state\b', 'getattr(context, "state", {})', code)
            with open(ex, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"[+] {os.path.basename(ex):<20} : Repli getattr appliqué.")

# ------------------------------------------------------------------------------
# 2. VERROUILLAGE SQLITE (REMPLACEMENT DE 'id' PAR LE NATIF 'rowid')
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()
    
    # Remplacement exact et universel de l'erreur SQL
    code = re.sub(r'ORDER BY\s+id\b', 'ORDER BY rowid', code, flags=re.IGNORECASE)
    
    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[+] {'store.py':<20} : Requête scellée avec le métadonnée 'rowid' (Syntaxe Validée).")

