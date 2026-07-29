import json
import os
from datetime import datetime



class MemoryAuditBridge:


    def __init__(
        self,
        file="runtime/memory/action_audit.json"
    ):

        self.file=file



    def record(
        self,
        action,
        status
    ):


        os.makedirs(
            os.path.dirname(self.file),
            exist_ok=True
        )


        entry={

            "timestamp":
                datetime.now().isoformat(),

            "action":
                action,

            "status":
                status

        }


        with open(
            self.file,
            "a",
            encoding="utf8"
        ) as f:

            f.write(
                json.dumps(entry)
                + "\n"
            )


        return entry
