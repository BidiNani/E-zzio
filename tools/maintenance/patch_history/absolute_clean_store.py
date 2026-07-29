from pathlib import Path
import re

print("[*] Nettoyage total et fusion unique de get_execution_history dans store.py...")

store_path = Path("runtime/action/store.py")
code = store_path.read_text(encoding="utf-8")

# 1. Suppression de TOUTES les définitions de get_execution_history présentes dans le fichier
while "def get_execution_history" in code:
    start = code.find("def get_execution_history")
    # Trouver la prochaine définition de méthode ou la fin du fichier
    next_def = code.find("\n    def ", start + 1)
    if next_def == -1:
        next_def = code.find("\ndef ", start + 1)
    
    if next_def != -1:
        code = code[:start] + code[next_def:]
    else:
        code = code[:start]

# 2. Injection de la version unique, parfaite et définitive juste avant def clear(self):
unique_method = """    def get_execution_history(self, action_name=None, limit=50):
        import sqlite3
        import json

        with sqlite3.connect(self.db_path) as conn:
            if action_name:
                cursor = conn.execute(
                    \"\"\"
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp
                    FROM execution_ledger
                    WHERE action_name = ?
                    ORDER BY rowid DESC
                    LIMIT ?
                    \"\"\",
                    (action_name, limit)
                )
            else:
                cursor = conn.execute(
                    \"\"\"
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp
                    FROM execution_ledger
                    ORDER BY rowid DESC
                    LIMIT ?
                    \"\"\",
                    (limit,)
                )

            rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                "exec_id": row[0],
                "action_name": row[1],
                "status": row[2],
                "payload": json.loads(row[3]) if isinstance(row[3], str) else row[3],
                "result": json.loads(row[4]) if isinstance(row[4], str) else row[4],
                "cost": row[5],
                "duration_ms": row[6],
                "timestamp": row[7]
            })

        return history

"""

target = "    def clear(self):"
if target in code:
    code = code.replace(target, unique_method + target)
    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py : Méthode unifiée et injectée avec succès.")
else:
    print("[-] Erreur : Point d'ancrage def clear(self) introuvable.")
