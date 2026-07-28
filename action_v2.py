from pathlib import Path
import re

print("[*] Patch ActionStore v2")


p=Path("runtime/action/store.py")

code=p.read_text(encoding="utf-8")


method=r'''
    def get_execution_history(self, action_name=None, limit=50):
        import sqlite3
        import json

        with sqlite3.connect(self.db_path) as conn:

            if action_name:
                sql="""
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
                ORDER BY timestamp DESC
                LIMIT ?
                """

                args=(action_name,limit)

            else:

                sql="""
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
                ORDER BY timestamp DESC
                LIMIT ?
                """

                args=(limit,)


            cursor=conn.execute(sql,args)

            columns=[
                x[0]
                for x in cursor.description
            ]


            result=[]

            for row in cursor.fetchall():

                item=dict(
                    zip(columns,row)
                )


                for field in [
                    "payload",
                    "result"
                ]:

                    if isinstance(item[field],str):

                        try:
                            item[field]=json.loads(item[field])
                        except Exception:
                            pass


                result.append(item)


            return result
'''


code=re.sub(
    r'    def get_execution_history\(.*?(?=\n    def |\nclass |\Z)',
    method,
    code,
    flags=re.S
)


p.write_text(
    code,
    encoding="utf-8"
)


print("[OK] ActionStore v2")
