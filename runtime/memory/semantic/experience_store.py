import json
import os
from datetime import datetime


class ExperienceStore:


    def __init__(
        self,
        file="runtime/memory/experience.json"
    ):

        self.file=file

        os.makedirs(
            os.path.dirname(file),
            exist_ok=True
        )


    def record(
        self,
        action,
        result,
        score
    ):

        entry={

            "timestamp":
                datetime.now().isoformat(),

            "action":
                action,

            "result":
                result,

            "score":
                score
        }


        data=self.load()

        data.append(entry)

        with open(
            self.file,
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )


    def load(self):

        if not os.path.exists(self.file):
            return []


        with open(
            self.file,
            encoding="utf8"
        ) as f:

            return json.load(f)
