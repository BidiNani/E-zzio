import json
import urllib.request
from .base import Capability


class EmbedderCapability(Capability):
    name = "memory.embed"
    description = "Vectorise du texte via Nomic."

    def run(self, parameters: dict) -> dict:
        text = parameters.get("text", "")
        payload = json.dumps({"model": "nomic-embed-text:latest", "prompt": text}).encode("utf-8")
        req = urllib.request.Request("http://localhost:11434/api/embeddings", data=payload, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"vector": data.get("embedding"), "status": "SUCCESS"}
