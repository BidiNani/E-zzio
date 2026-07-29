import json
import os
from datetime import datetime


class MemoryWAL:


    def __init__(
        self,
        path="runtime/memory/journal/memory.wal"
    ):
        self.path=path


    def append(
        self,
        operation,
        payload
    ):

        os.makedirs(
            os.path.dirname(self.path),
            exist_ok=True
        )


        entry={
            "timestamp":
                datetime.now().isoformat(),

            "operation":
                operation,

            "payload":
                payload
        }


        with open(
            self.path,
            "a",
            encoding="utf8"
        ) as f:

            f.write(
                json.dumps(entry)
                + "\n"
            )


    def replay(self):

        if not os.path.exists(self.path):
            return []


        result=[]

        with open(
            self.path,
            encoding="utf8"
        ) as f:

            for line in f:

                try:
                    result.append(
                        json.loads(line)
                    )

                except:
                    continue


        return result
