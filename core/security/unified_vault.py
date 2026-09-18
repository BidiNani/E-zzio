"""Gestionnaire de clés centralisé avec support Multi-Key Rotation."""

import itertools
import os
import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
ENV_FILES = [
    ROOT_DIR / "secrets" / ".env",
    ROOT_DIR / "secrets" / "cloud_brain.env",
    ROOT_DIR / ".env",
]


class UnifiedKeyVault:
    """Singleton centralisant l'accès aux clés avec rotation multi-clés."""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._key_iterators: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        self._cache.clear()
        self._key_iterators.clear()

        # Lecture des fichiers .env
        for env_path in reversed(ENV_FILES):
            if env_path.exists():
                try:
                    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                        line = raw.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        clean_k = k.strip()
                        clean_v = v.strip().strip('"').strip("'")
                        if clean_k and clean_v:
                            self._cache[clean_k] = clean_v
                except Exception:
                    pass

        # Priorité aux variables système actives
        for k, v in os.environ.items():
            if v:
                self._cache[k] = v

    def get(self, key: str, default: str = "") -> str:
        val = os.environ.get(key) or self._cache.get(key) or default
        return str(val).strip()

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, str(default)).lower()
        return val in {"1", "true", "yes", "y", "on"}

    def get_all_keys_for_provider(self, provider: str) -> list[str]:
        """Récupère l'ensemble des clés enregistrées pour un provider (multi-clés)."""
        p = provider.lower().strip()
        keys: list[str] = []

        if p == "gemini":
            patterns = [r"^GEMINI_API_KEY(?:_\d+)?$", r"^GOOGLE_API_KEY(?:_\d+)?$"]
        elif p == "groq":
            patterns = [r"^GROQ_API_KEY(?:_\d+)?$"]
        elif p == "openrouter":
            patterns = [r"^OPENROUTER_API_KEY(?:_\d+)?$"]
        else:
            patterns = [rf"^{p.upper()}_API_KEY(?:_\d+)?$"]

        for k, v in self._cache.items():
            if any(re.match(pat, k) for pat in patterns) and v:
                if v not in keys:
                    keys.append(v)

        return keys

    def get_provider_key(self, provider: str) -> str:
        """Retourne la clé suivante via rotation round-robin."""
        p = provider.lower().strip()
        keys = self.get_all_keys_for_provider(p)

        if not keys:
            return ""
        if len(keys) == 1:
            return keys[0]

        if p not in self._key_iterators:
            self._key_iterators[p] = itertools.cycle(keys)

        return next(self._key_iterators[p])

    def is_cloud_allowed(self) -> bool:
        return self.get_bool("EZZIO_CLOUD_ALLOW_SEND", default=True)


key_vault = UnifiedKeyVault()
