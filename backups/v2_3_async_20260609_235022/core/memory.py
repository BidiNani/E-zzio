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
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def _save(self, data):
        self.storage_path.write_text(
            json.dumps(data[-600:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_interaction(self, input_text, response_text, expert_name, metadata=None):
        data = self._load()
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": str(input_text),
            "response": str(response_text),
            "expert": str(expert_name),
            "metadata": metadata or {},
        }
        data.append(entry)
        self._save(data)
        return entry

    def get_context(self, last_n=5):
        return self._load()[-last_n:]

    def search(self, query, limit=10):
        tokens = [t.lower() for t in str(query).split() if t.strip()]
        if not tokens:
            return self.get_context(last_n=limit)

        scored = []
        for item in self._load():
            haystack = f"{item.get('input','')} {item.get('response','')} {item.get('expert','')}".lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0])
        return [item for _, item in scored[-limit:]]

    def compact(self, keep_last=300):
        data = self._load()
        self._save(data[-keep_last:])
        return {"kept": min(len(data), keep_last), "previous": len(data)}

ezzio_memory = MemoryManager()
