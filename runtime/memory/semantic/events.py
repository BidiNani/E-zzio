from datetime import datetime


class MemoryEvents:


    @staticmethod
    def event(
        name,
        payload=None
    ):

        return {

            "event":
                name,

            "timestamp":
                datetime.now().isoformat(),

            "payload":
                payload or {}

        }
