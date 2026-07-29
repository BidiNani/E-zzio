from pathlib import Path
import re

path = Path("runtime/action/store.py")

code = path.read_text(encoding="utf-8")


print("[1] Suppression anciennes méthodes get_execution_history")


code = re.sub(
    r'\n\s*def get_execution_history\(.*?(?=\n\s*def |\Z)',
    '',
    code,
    flags=re.S
)


print("[2] Injection méthode propre")


method = '''

    def get_execution_history(self, action_name=None, limit=50):
        import sqlite3
        import json

        with sqlite3.connect(self.db_path) as conn:

            if action_name:
                cursor = conn.execute(
                    """
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp
                    FROM execution_ledger
                    WHERE action_name = ?
                    ORDER BY rowid DESC
                    LIMIT ?
                    """,
                    (action_name, limit)
                )

            else:
                cursor = conn.execute(
                    """
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp
                    FROM execution_ledger
                    ORDER BY rowid DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            rows = cursor.fetchall()


        history=[]

        for row in rows:

            history.append({
                "exec_id": row[0],
                "action_name": row[1],
                "status": row[2],
                "payload": json.loads(row[3]) if isinstance(row[3],str) else row[3],
                "result": json.loads(row[4]) if isinstance(row[4],str) else row[4],
                "cost": row[5],
                "duration_ms": row[6],
                "timestamp": row[7]
            })


        return history

'''


insert = code.find("    def clear(self):")


if insert == -1:
    raise Exception("Impossible de trouver clear()")


code = code[:insert] + method + code[insert:]


path.write_text(code,encoding="utf-8")


print("[OK] store.py réparé")
