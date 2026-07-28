from pathlib import Path

print("[*] Reconstruction totale et propre de runtime/action/store.py...")

store_path = Path("runtime/action/store.py")

# On lit le fichier existant, on repère la classe ActionStore, et on réécrit la méthode proprement en Python pur
code = store_path.read_text(encoding="utf-8")

# Nettoyage de l'ancienne méthode get_execution_history
import re
code = re.sub(r'def get_execution_history\(.*?(?=\n    def |\nclass |\Z)', '', code, flags=re.DOTALL)

# Nouvelle méthode avec indentation rigoureuse (4 espaces par niveau)
new_method = """
    def get_execution_history(self, action_name=None, limit=50):
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

            columns = [x[0] for x in cursor.description]
            result = []
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                for field in ["payload", "result"]:
                    if isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except Exception:
                            pass
                result.append(item)
            return result
"""

# Insertion de la méthode juste avant la fin du fichier ou dans la classe ActionStore
if "class ActionStore" in code:
    # Insérer avant la dernière méthode ou à la fin de la classe
    code = code.strip() + "\n" + new_method
    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py : Méthode réinsérée proprement.")
else:
    print("[-] Erreur : Classe ActionStore introuvable.")
