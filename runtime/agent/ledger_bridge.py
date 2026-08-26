import time
import hashlib
import json


class AgentLedgerBridge:
    def __init__(self):
        self.events = []
        self.last_hash = "0" * 64  # Genesis block hash

    def record(self, event_type, payload):
        entry = {"event": event_type, "timestamp": time.time(), "previous_hash": self.last_hash, "payload": payload}
        raw = json.dumps(entry, sort_keys=True).encode()
        current_hash = hashlib.sha256(raw).hexdigest()
        entry["hash"] = current_hash

        self.last_hash = current_hash
        self.events.append(entry)
        return entry
