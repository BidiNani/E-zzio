import time
from datetime import datetime

from runtime.memory.semantic.health import MemoryHealth


class MemorySentinel:


    def check(self):

        report=MemoryHealth.report()

        return {
            "timestamp":
                datetime.now().isoformat(),

            "health":
                report["overall"],

            "report":
                report
        }



    def watch(self,interval=60):

        while True:

            result=self.check()

            print(result)

            time.sleep(
                interval
            )
