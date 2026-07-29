from datetime import datetime


class MemoryTelemetry:


    def __init__(self):

        self.metrics={}


    def record(
        self,
        name,
        value
    ):

        self.metrics[name]=value


    def export(self):

        return {

            "timestamp":
                datetime.now().isoformat(),

            "metrics":
                self.metrics

        }
