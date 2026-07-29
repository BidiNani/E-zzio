import os
import json
import shutil
from datetime import datetime

from runtime.memory.semantic.crypto import MemoryCrypto


class MemorySelfHealing:


    def __init__(
        self,
        cache_file="runtime/memory/working_memory.json"
    ):

        self.cache_file=cache_file

        self.backup_file=(
            cache_file+".bak"
        )


    def validate_cache(self):

        try:

            with open(
                self.cache_file,
                encoding="utf-8"
            ) as f:

                data=json.load(f)


            if "interactions" not in data:

                raise Exception(
                    "Missing interactions"
                )


            return True


        except Exception:

            return self.repair_cache()



    def repair_cache(self):

        if os.path.exists(
            self.backup_file
        ):

            shutil.copy2(
                self.backup_file,
                self.cache_file
            )

            return True


        fresh={
            "version":
            "5.0-AutonomousCore",

            "interactions":[]
        }


        with open(
            self.cache_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                fresh,
                f,
                indent=4
            )


        return True



    def health(self):

        return {

            "status":
            "healthy"
            if self.validate_cache()
            else
            "failed",

            "timestamp":
            datetime.now().isoformat()

        }
