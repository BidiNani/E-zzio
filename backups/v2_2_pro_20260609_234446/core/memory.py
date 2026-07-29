import json
from datetime import datetime
from pathlib import Path

class MemoryManager:
    def __init__(self, storage_path="G:/AI/E-zzio/registry/history.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def _load(self):
        try:
            content = self.storage_path.read_text(encoding="utf-8").strip()
            if not content:
                return []
            return json.loads(content)
        except Exception:
            return []

    def _save(self, data):
        self.storage_path.write_text(
            json.dumps(data[-500:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_interaction(self, input_text, response_text, expert_name):
        data = self._load()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": str(input_text),
            "response": str(response_text),
            "expert": str(expert_name),
        }
        data.append(entry)
        self._save(data)
        return entry

    def get_context(self, last_n=5):
        return self._load()[-last_n:]

    def search(self, query, limit=10):
        tokens = [t.lower() for t in str(query).split() if t.strip()]
        results = []
        for item in self._load():
            haystack = f"{item.get('input','')} {item.get('response','')} {item.get('expert','')}".lower()
            if any(token in haystack for token in tokens):
                results.append(item)
        return results[-limit:]

ezzio_memory = MemoryManager()
