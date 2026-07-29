from pathlib import Path

print("[*] E-ZZIO v1.9.2.6 - Réparation de l'indentation de store.py...")

store_path = Path("runtime/action/store.py")
code = store_path.read_text(encoding="utf-8")

# Définition de la méthode avec une indentation irréprochable (4 espaces mères, 8 pour le corps)
clean_method = """    def get_execution_history(self, action_name=None, limit=50):
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
            return result"""

# Remplacement chirurgical
start_idx = code.find("def get_execution_history")
if start_idx != -1:
    next_def = code.find("\n    def ", start_idx + 1)
    if next_def == -1:
        next_def = code.find("\ndef ", start_idx + 1)
    
    if next_def != -1:
        code = code[:start_idx] + clean_method + "\n\n" + code[next_def:]
    else:
        code = code[:start_idx] + clean_method

    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py : Indentation corrigée avec succès.")
else:
    print("[-] Erreur : get_execution_history introuvable.")
