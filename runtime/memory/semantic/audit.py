import json
import os
from datetime import datetime


class MemoryAudit:


    def __init__(
        self,
        file="runtime/memory/audit.json"
    ):

        self.file=file


    def record(
        self,
        event,
        payload
    ):

        entry={

            "timestamp":
                datetime.now().isoformat(),

            "event":
                event,

            "payload":
                payload

        }


        os.makedirs(
            os.path.dirname(self.file),
            exist_ok=True
        )


        with open(
            self.file,
            "a",
            encoding="utf8"
        ) as f:

            f.write(
                json.dumps(entry)
                + "\n"
            )
