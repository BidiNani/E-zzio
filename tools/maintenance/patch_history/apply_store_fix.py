from pathlib import Path
import re

print("[*] E-ZZIO v1.9.2.1 - Intégration et blindage de ActionStore...")

store_path = Path("runtime/action/store.py")
if store_path.exists():
    code = store_path.read_text(encoding="utf-8")

    # 1. Blindage de log_execution pour forcer le json.dumps sur les objets et dictionnaires
    log_exec_patch = '''    def log_execution(self, exec_id, action_name, status, payload, result, cost, duration_ms):
        import json
        with sqlite3.connect(self.db_path) as conn:
            p_str = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
            r_str = json.dumps(result, default=str) if not isinstance(result, str) else result
            conn.execute(
                "INSERT INTO execution_ledger (exec_id, action_name, status, payload, result, cost, duration_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (exec_id, action_name, status, p_str, r_str, cost, duration_ms)
            )
            conn.commit()'''

    code = re.sub(
        r'def log_execution\(.*?(?=\n    def |\nclass |\Z)',
        log_exec_patch.strip(),
        code,
        flags=re.DOTALL
    )

    # 2. Blindage de get_execution_history (Tri timestamp DESC, rowid DESC + décodage sécurisé)
    get_exec_patch = '''    def get_execution_history(self, action_name=None, limit=50):
        import sqlite3
        import json

        with sqlite3.connect(self.db_path) as conn:
            if action_name:
                cursor = conn.execute(
                    """
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp 
                    FROM execution_ledger 
                    WHERE action_name = ? 
                    ORDER BY timestamp DESC, rowid DESC 
                    LIMIT ?
                    """,
                    (action_name, limit)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT exec_id, action_name, status, payload, result, cost, duration_ms, timestamp 
                    FROM execution_ledger 
                    ORDER BY timestamp DESC, rowid DESC 
                    LIMIT ?
                    """,
                    (limit,)
                )
            rows = cursor.fetchall()
        
        history = []
        for r in rows:
            def safe_load(val):
                if isinstance(val, dict):
                    return val
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except Exception:
                        return {"error": val, "output": val}
                return {} if val is None else {"value": val}

            history.append({
                "exec_id": r[0],
                "action_name": r[1],
                "status": r[2],
                "payload": safe_load(r[3]),
                "result": safe_load(r[4]),
                "cost": r[5],
                "duration_ms": r[6],
                "timestamp": r[7]
            })
        return history'''

    code = re.sub(
        r'def get_execution_history\(.*?(?=\n    def |\nclass |\Z)',
        get_exec_patch.strip(),
        code,
        flags=re.DOTALL
    )

    store_path.write_text(code, encoding="utf-8")
    print("[+] store.py réécrit avec succès (JSON strict + Double tri).")

