from pathlib import Path
import re

print("[1] Reconstruction ActionStore.get_execution_history")

p=Path("runtime/action/store.py")

code=p.read_text(encoding="utf-8")


new_method=r'''
    def get_execution_history(self, action_name=None, limit=50):
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:

            if action_name:
                cursor = conn.execute(
                    """
                    SELECT 
                        exec_id,
                        action_name,
                        status,
                        payload,
                        result,
                        cost,
                        duration_ms,
                        timestamp
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
                    SELECT
                        exec_id,
                        action_name,
                        status,
                        payload,
                        result,
                        cost,
                        duration_ms,
                        timestamp
                    FROM execution_ledger
                    ORDER BY rowid DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            columns=[x[0] for x in cursor.description]

            return [
                dict(zip(columns,row))
                for row in cursor.fetchall()
            ]
'''


code=re.sub(
    r'    def get_execution_history\(.*?(?=\n    def |\nclass |\Z)',
    new_method,
    code,
    flags=re.S
)


p.write_text(code,encoding="utf-8")

print("[OK] ActionStore stabilisé")
