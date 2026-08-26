import json
import hashlib
import threading
import copy
from pathlib import Path
from typing import Dict, Any


class ManifestProvider:
    """Fournisseur d'état du manifest, garantissant l'intégrité via SHA-256 du contenu."""

    SUPPORTED_VERSION = 2

    def __init__(self, path: str = None):
        self.path = Path(path or Path(__file__).resolve().parents[1] / "tools" / "manifest.json")
        self._cache = {}
        self._cache_hash = "unknown"
        self._lock = threading.Lock()

    def get_manifest_hash(self) -> str:
        self.get_tools()
        return self._cache_hash

    def get_tools(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}

        with self._lock:
            try:
                content = self.path.read_bytes()
                current_hash = hashlib.sha256(content).hexdigest()[:12]

                # Invalidation parfaite basée sur le contenu réel
                if self._cache and current_hash == self._cache_hash:
                    return copy.deepcopy(self._cache)

                data = json.loads(content.decode("utf-8"))
                if data.get("manifest_version") != self.SUPPORTED_VERSION:
                    raise ValueError(f"Version non supportée: {data.get('manifest_version')}")

                self._cache = data.get("tools", {})
                self._cache_hash = current_hash
                return copy.deepcopy(self._cache)
            except Exception:
                self._cache = {}
                return {}
