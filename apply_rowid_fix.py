from pathlib import Path
import re

print("[*] E-ZZIO v1.9.2.2 - Application du tri strict par rowid DESC...")

store_path = Path("runtime/action/store.py")
if store_path.exists():
    code = store_path.read_text(encoding="utf-8")

    # Remplacement des requêtes pour s'appuyer uniquement sur le rowid DESC (chronologie d'insertion brute)
    code = re.sub(
        r'ORDER BY\s+timestamp\s+DESC,\s+rowid\s+DESC',
        'ORDER BY rowid DESC',
        code,
        flags=re.IGNORECASE
    )

    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py : Tri SQLite basculé en strict 'ORDER BY rowid DESC'.")
