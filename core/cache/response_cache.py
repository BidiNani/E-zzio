"""
E-ZZIO Core — Technical Response Cache (Deterministic Optimization Layer).
Ce module est un cache technique d'optimisation de latence et de quota pour les requêtes LLM.
INVARIANTS :
1. STRICTEMENT NON-COGNITIF : Ne modifie jamais UnifiedMemoryGateway ni les archives FTS5.
2. ZÉRO SECONDE AUTORITÉ : Ne prend aucune décision de routage.
3. SÉCURITÉ : Interdiction d'enregistrer les secrets/clés/credentials privés.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger("EzzioResponseCache")

DEFAULT_CACHE_DIR = Path("G:/AI/E-zzio/state/cache")
DEFAULT_CACHE_DB = DEFAULT_CACHE_DIR / "response_cache.db"
DEFAULT_TTL_SECONDS = 3600.0  # 1 heure par défaut


class ResponseCache:
    """Cache technique de réponses d'inférence avec clé composite et invalidation TTL/Git."""

    _instance: ResponseCache | None = None
    _lock = Lock()

    def __new__(cls, db_path: Path | str = DEFAULT_CACHE_DB):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_cache(db_path)
            return cls._instance

    def _init_cache(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    prompt_hash TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    repo_revision TEXT,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at);")
            conn.commit()

    @staticmethod
    def compute_key(
        prompt: str,
        context: str = "",
        profile: str = "general",
        system_prompt: str = "",
        toolset: str = "",
        repo_revision: str = ""
    ) -> str:
        """Génère une clé composite SHA-256 déterministe pour la requête logique."""
        raw_seed = f"{prompt.strip()}|{context.strip()}|{profile.strip().lower()}|{system_prompt.strip()}|{toolset.strip()}|{repo_revision.strip()}"
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()

    @staticmethod
    def contains_sensitive_data(text: str) -> bool:
        """Détecte la présence potentielle de clés secrètes pour interdire la mise en cache."""
        sensitive_markers = [
            "AIzaSy", "sk-", "gsk_", "Bearer ", "PRIVATE KEY", "BEGIN RSA", "PASSWORD="
        ]
        return any(marker in text for marker in sensitive_markers)

    def get(
        self,
        prompt: str,
        context: str = "",
        profile: str = "general",
        system_prompt: str = "",
        toolset: str = "",
        repo_revision: str = ""
    ) -> dict[str, Any] | None:
        """Recherche dans le cache. Retourne la réponse si valide, None sinon."""
        key = self.compute_key(prompt, context, profile, system_prompt, toolset, repo_revision)
        now = time.time()

        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT response_text, provider, model, profile, created_at, expires_at, hit_count "
                    "FROM response_cache WHERE cache_key = ?",
                    (key,)
                )
                row = cursor.fetchone()

                if not row:
                    self.misses += 1
                    return None

                response_text, prov, mod, prof, created_at, expires_at, hit_count = row

                if now > expires_at:
                    # Expiré -> suppression
                    cursor.execute("DELETE FROM response_cache WHERE cache_key = ?", (key,))
                    conn.commit()
                    self.misses += 1
                    return None

                # Cache Hit valide
                cursor.execute(
                    "UPDATE response_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                    (key,)
                )
                conn.commit()
                self.hits += 1

                return {
                    "hit": True,
                    "source": "cache",
                    "text": response_text,
                    "provider": prov,
                    "model": mod,
                    "profile": prof,
                    "cached_at": created_at,
                    "cache_key": key,
                    "hit_count": hit_count + 1
                }
        except Exception as exc:
            logger.debug("[CACHE-GET-ERROR] %s", exc)
            self.misses += 1
            return None

    def set(
        self,
        prompt: str,
        response_text: str,
        context: str = "",
        profile: str = "general",
        model: str = "",
        provider: str = "",
        system_prompt: str = "",
        toolset: str = "",
        repo_revision: str = "",
        ttl_seconds: float = DEFAULT_TTL_SECONDS
    ) -> bool:
        """Enregistre une réponse complète valide dans le cache."""
        if not response_text or not response_text.strip():
            return False

        # Garde de sécurité anti-secrets
        if self.contains_sensitive_data(prompt) or self.contains_sensitive_data(response_text):
            logger.info("[CACHE-SECURITY] Requête ou réponse contenant un marqueur sensible : ignoré du cache.")
            return False

        key = self.compute_key(prompt, context, profile, system_prompt, toolset, repo_revision)
        prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
        now = time.time()
        expires_at = now + max(1.0, ttl_seconds)

        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO response_cache "
                    "(cache_key, prompt_hash, response_text, provider, model, profile, created_at, expires_at, repo_revision, hit_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                    (key, prompt_hash, response_text, provider, model, profile, now, expires_at, repo_revision)
                )
                conn.commit()
                self.writes += 1
                return True
        except Exception as exc:
            logger.debug("[CACHE-SET-ERROR] %s", exc)
            return False

    def invalidate_all(self) -> int:
        """Purge complète du cache technique."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM response_cache")
                count = cursor.rowcount
                conn.commit()
                logger.info("[CACHE-PURGE] %d entrées purgées du cache technique.", count)
                return count
        except Exception as exc:
            logger.error("[CACHE-PURGE-ERROR] %s", exc)
            return 0

    def get_stats(self) -> dict[str, Any]:
        """Retourne la télémétrie du cache."""
        total_items = 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM response_cache")
                total_items = cursor.fetchone()[0]
        except Exception:
            pass

        return {
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "total_items": total_items,
            "hit_ratio": (self.hits / (self.hits + self.misses)) if (self.hits + self.misses) > 0 else 0.0
        }


# Singleton
response_cache = ResponseCache()
