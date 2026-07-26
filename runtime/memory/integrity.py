import hashlib
import json
from runtime.memory.models import MemoryItem

class MemoryIntegrityChecker:
    @staticmethod
    def verify(item: MemoryItem) -> bool:
        """Verifies if the memory content matches its SHA-256 hash."""
        content_str = json.dumps(
            item.content,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str
        )
        expected_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
        return expected_hash == item.content_hash
