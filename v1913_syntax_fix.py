import re
import os

store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    print("[*] E-ZZIO v1.9.1.3 - Restauration de la syntaxe Python...")

    # 1. Rollback chirurgical : on annule le remplacement abusif sur le mot-clé 'limit'
    # Cela réparera la signature de la fonction et l'appel (action_name, limit)
    code = re.sub(r'ORDER\s+BY\s+rowid\s+DESC\s+LIMIT', 'limit', code, flags=re.IGNORECASE)

    # 2. Injection SQL stricte : on cible UNIQUEMENT les chaînes de requêtes SQL
    code = re.sub(
        r'("SELECT\s+exec_id.*?FROM\s+execution_ledger[^"]*?)\s*limit\s*\?',
        r'\1 ORDER BY rowid DESC LIMIT ?',
        code,
        flags=re.IGNORECASE
    )

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    
    print("[+] store.py : Syntaxe Python restaurée et requête SQL verrouillée en toute sécurité.")
