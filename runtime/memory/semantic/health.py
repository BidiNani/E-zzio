import os
import sqlite3
from runtime.memory.semantic.self_healing import MemorySelfHealing


class MemoryHealth:


    @staticmethod
    def report():

        healer=MemorySelfHealing()

        result={}

        result["cache"] = healer.health()


        db="runtime/memory/database/memory.sqlite3"


        if os.path.exists(db):

            try:

                conn=sqlite3.connect(db)

                check=conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                conn.close()

                result["database"]=(
                    "OK"
                    if check[0]=="ok"
                    else
                    "FAILED"
                )


            except Exception:

                result["database"]="FAILED"

        else:

            result["database"]="ABSENT"



        result["overall"]=(
            "HEALTHY"
            if all(
                [
                result["cache"]["status"]=="healthy",
                result["database"]!="FAILED"
                ]
            )
            else
            "DEGRADED"
        )


        return result
