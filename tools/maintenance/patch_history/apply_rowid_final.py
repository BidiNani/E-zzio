from pathlib import Path
import re

print("[*] Application du tri strict rowid DESC sur ActionStore...")

store_path = Path("runtime/action/store.py")
if store_path.exists():
    code = store_path.read_text(encoding="utf-8")

    # On remplace proprement tout ORDER BY dans get_execution_history par ORDER BY rowid DESC
    def fix_ledger_sorting(match):
        method_body = match.group(0)
        # Remplace n'importe quel ORDER BY ... par ORDER BY rowid DESC
        method_body = re.sub(r'ORDER BY\s+[a-z0-9_,\s]+', 'ORDER BY rowid DESC', method_body, flags=re.IGNORECASE)
        return method_body

    code = re.sub(
        r'def get_execution_history\(.*?(?=\n    def |\nclass |\Z)',
        fix_ledger_sorting,
        code,
        flags=re.DOTALL
    )

    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py : Tri par rowid DESC appliqué avec succès.")
