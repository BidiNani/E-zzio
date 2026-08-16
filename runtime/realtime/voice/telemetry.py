import json
from pathlib import Path

class VoiceTelemetry:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, request, result):
        event = {
            "request_id": request.request_id,
            "ttfa": result["ttfa"],
            "rtf": result["rtf"],
            "duration": result["duration"]
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
