import os
import json
from datetime import datetime


class MemoryQuarantine:


    def __init__(
        self,
        path="runtime/memory/quarantine"
    ):

        self.path=path

        os.makedirs(
            path,
            exist_ok=True
        )


    def isolate(self,data):

        name=(
            datetime.now()
            .strftime("%Y%m%d_%H%M%S")
            + ".json"
        )


        target=os.path.join(
            self.path,
            name
        )


        with open(
            target,
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )


        return target
