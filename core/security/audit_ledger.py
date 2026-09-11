"""
E-ZZIO Core — Cryptographic Append-Only Audit Ledger (Inspiré des Principes Trinity).
Garantit une traçabilité immuable, inaltérable et vérifiable mathématiquement :
1. Chaînage cryptographique par hash SHA-256 (Blockchain locale)
2. Triggers SQLite d'interdiction formelle de mise à jour (UPDATE) et de suppression (DELETE)
3. Fonction de vérification d'intégrité de la chaîne complète
"""
from __future__ import annotations
import os
import time
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import threading

logger = logging.getLogger("AuditLedger")

GENESIS_HASH = "0" * 64


class AuditLedger:
    """Registre d'audit append-only scellé cryptographiquement et protégé contre les écritures concurrentes."""

    def __init__(self, db_path: str = "runtime/evidence/audit_ledger.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._write_lock:
            with self._get_connection() as conn:
                # Table append-only
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_trail (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        prev_hash TEXT NOT NULL,
                        current_hash TEXT NOT NULL UNIQUE,
                        timestamp REAL NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        status TEXT NOT NULL
                    );
                """)

                # Triggers SQLite pour interdire toute altération rétroactive
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_audit_update 
                    BEFORE UPDATE ON audit_trail
                    BEGIN
                        SELECT RAISE(ABORT, '[IMMUTABLE LEDGER VIOLATION] Modification interdite sur le journal d''audit.');
                    END;
                """)

                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS prevent_audit_delete 
                    BEFORE DELETE ON audit_trail
                    BEGIN
                        SELECT RAISE(ABORT, '[IMMUTABLE LEDGER VIOLATION] Suppression interdite sur le journal d''audit.');
                    END;
                """)
                conn.commit()

    def _compute_hash(self, prev_hash: str, timestamp: float, actor: str, action: str, payload_str: str) -> str:
        raw = f"{prev_hash}|{timestamp:.6f}|{actor}|{action}|{payload_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def record_event(
        self,
        actor: str,
        action: str,
        payload: Dict[str, Any],
        status: str = "SUCCESS"
    ) -> Dict[str, Any]:
        """Enregistre un nouvel événement dans le journal scellé (Sérialisation Thread-Safe)."""
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)

        # Verrou exclusif de sérialisation cryptographique
        with self._write_lock:
            now = time.time()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT current_hash FROM audit_trail ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                prev_hash = row[0] if row else GENESIS_HASH

                current_hash = self._compute_hash(prev_hash, now, actor, action, payload_str)

                cursor.execute("""
                    INSERT INTO audit_trail (prev_hash, current_hash, timestamp, actor, action, payload_json, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (prev_hash, current_hash, now, actor, action, payload_str, status))
                conn.commit()

                entry_id = cursor.lastrowid

        return {
            "id": entry_id,
            "prev_hash": prev_hash,
            "current_hash": current_hash,
            "timestamp": now,
            "actor": actor,
            "action": action,
            "status": status
        }

    def verify_chain_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """
        Vérifie mathématiquement chaque maillon de la chaîne cryptographique.
        Retourne (is_valid, total_events_checked, error_message).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, prev_hash, current_hash, timestamp, actor, action, payload_json FROM audit_trail ORDER BY id ASC")
            rows = cursor.fetchall()

            if not rows:
                return True, 0, None

            expected_prev = GENESIS_HASH
            for row in rows:
                r_id, prev_h, curr_h, ts, actor, action, payload_str = row
                if prev_h != expected_prev:
                    return False, r_id, f"Rupture de chaîne à l'entrée {r_id} : prev_hash attendu {expected_prev}, trouvé {prev_h}"

                recomputed = self._compute_hash(prev_h, ts, actor, action, payload_str)
                if recomputed != curr_h:
                    return False, r_id, f"Corruption de hash à l'entrée {r_id} : hash attendu {recomputed}, trouvé {curr_h}"

                expected_prev = curr_h

            return True, len(rows), None

    def query_events(self, limit: int = 50, actor: Optional[str] = None) -> List[Dict[str, Any]]:
        """Interroge le journal d'audit pour récupérer les derniers événements."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if actor:
                cursor.execute(
                    "SELECT id, prev_hash, current_hash, timestamp, actor, action, payload_json, status FROM audit_trail WHERE actor = ? ORDER BY id DESC LIMIT ?",
                    (actor, limit),
                )
            else:
                cursor.execute(
                    "SELECT id, prev_hash, current_hash, timestamp, actor, action, payload_json, status FROM audit_trail ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                r_id, prev_h, curr_h, ts, act, action, payload_str, status = row
                try:
                    payload = json.loads(payload_str)
                except Exception:
                    payload = {}
                results.append({
                    "id": r_id,
                    "prev_hash": prev_h,
                    "current_hash": curr_h,
                    "timestamp": ts,
                    "actor": act,
                    "action": action,
                    "payload": payload,
                    "status": status,
                })
            return results


# Singleton global
audit_ledger = AuditLedger()
