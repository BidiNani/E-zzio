"""
core/capabilities/web_cache.py — Lightweight Sovereign Web Cache Engine for E-ZZIO.
Provides deterministic canonical keying, configurable TTLs, bounded LRU eviction,
security masking (no credentials/headers), and observable hit/miss telemetry.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("WebCache")


class WebCache:
    """Cache Web SQLite souverain append/lookup avec TTL et éviction bornée."""

    def __init__(
        self,
        db_path: str = "runtime/cache/web_cache.db",
        workspace_root: str = r"G:\AI\E-zzio",
        default_ttl_sec: float = 86400.0,  # 24h
        max_entries: int = 1000
    ):
        if not Path(db_path).is_absolute():
            self.db_path = (Path(workspace_root) / db_path).resolve()
        else:
            self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.default_ttl_sec = default_ttl_sec
        self.max_entries = max_entries
        self._lock = threading.Lock()

        # Telemetry counters
        self.hits = 0
        self.misses = 0
        self.saved_calls = 0
        self.latency_saved_ms = 0.0

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS web_cache (
                        cache_key TEXT PRIMARY KEY,
                        operation TEXT NOT NULL,
                        query_or_url TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        cost_class TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        hit_count INTEGER DEFAULT 0,
                        latency_saved_ms REAL DEFAULT 0.0
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON web_cache(expires_at);")

    @staticmethod
    def build_canonical_key(
        operation: str,
        query_or_url: str,
        role: str = "SEARCH",
        options: dict[str, Any] | None = None
    ) -> str:
        """Génère une clé déterministe canonique sans aucune donnée de credential."""
        norm_op = str(operation).strip().lower()
        norm_target = str(query_or_url).strip().lower()
        norm_role = str(role).strip().upper()

        clean_opts: dict[str, str] = {}
        if options:
            for k, v in sorted(options.items()):
                if k.lower() in ("api_key", "authorization", "token", "cookie", "headers", "secret"):
                    continue
                clean_opts[k] = str(v)

        raw_payload = json.dumps({
            "op": norm_op,
            "target": norm_target,
            "role": norm_role,
            "opts": clean_opts
        }, sort_keys=True)

        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        """Récupère un résultat du cache s'il est présent et non expiré."""
        now = time.time()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT data_json, expires_at, latency_saved_ms FROM web_cache WHERE cache_key = ?;",
                        (cache_key,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        self.misses += 1
                        return None

                    data_json, expires_at, latency_saved = row
                    if now > expires_at:
                        conn.execute("DELETE FROM web_cache WHERE cache_key = ?;", (cache_key,))
                        self.misses += 1
                        return None

                    conn.execute("UPDATE web_cache SET hit_count = hit_count + 1 WHERE cache_key = ?;", (cache_key,))
                    self.hits += 1
                    self.saved_calls += 1
                    self.latency_saved_ms += latency_saved

                    res = json.loads(data_json)
                    if isinstance(res, dict):
                        res["cached"] = True
                    return res
            except Exception as exc:
                logger.debug("[WEB-CACHE-GET-FAIL] %s", exc)
                self.misses += 1
                return None

    def put(
        self,
        cache_key: str,
        operation: str,
        query_or_url: str,
        data: dict[str, Any],
        ttl_sec: float | None = None,
        cost_class: str = "FREE",
        latency_ms: float = 0.0
    ) -> None:
        """Insère ou met à jour une entrée dans le cache avec nettoyage d'éviction bornée."""
        now = time.time()
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl_sec
        expires_at = now + ttl

        clean_data = self._sanitize_data_for_cache(data)
        data_json = json.dumps(clean_data)

        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM web_cache WHERE expires_at < ?;", (now,))

                    cursor = conn.execute("SELECT COUNT(*) FROM web_cache;")
                    count = cursor.fetchone()[0]
                    if count >= self.max_entries:
                        conn.execute("""
                            DELETE FROM web_cache WHERE cache_key IN (
                                SELECT cache_key FROM web_cache ORDER BY created_at ASC LIMIT ?
                            );
                        """, (count - self.max_entries + 1,))

                    conn.execute("""
                        INSERT OR REPLACE INTO web_cache
                        (cache_key, operation, query_or_url, data_json, cost_class, created_at, expires_at, latency_saved_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (cache_key, operation, query_or_url, data_json, cost_class, now, expires_at, latency_ms))
            except Exception as exc:
                logger.debug("[WEB-CACHE-PUT-FAIL] %s", exc)

    def _sanitize_data_for_cache(self, data: Any) -> Any:
        """Supprime de manière récursive toute donnée sensible ou credential des objets mis en cache."""
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                if k.lower() in ("api_key", "authorization", "token", "cookie", "headers", "secret"):
                    continue
                clean[k] = self._sanitize_data_for_cache(v)
            return clean
        elif isinstance(data, list):
            return [self._sanitize_data_for_cache(x) for x in data]
        return data

    def get_stats(self) -> dict[str, Any]:
        """Observabilité complète du cache Web."""
        total = self.hits + self.misses
        hit_ratio = float(self.hits) / total if total > 0 else 0.0
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM web_cache WHERE expires_at > ?;", (time.time(),))
                    active_entries = cursor.fetchone()[0]
            except Exception:
                active_entries = 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
            "saved_calls": self.saved_calls,
            "latency_saved_ms": round(self.latency_saved_ms, 2),
            "active_entries": active_entries,
            "max_entries": self.max_entries,
            "default_ttl_sec": self.default_ttl_sec
        }
