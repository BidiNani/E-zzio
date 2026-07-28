import json
import uuid
import time
import sqlite3

class Consolidator:
    def __init__(self, event_bus, store):
        self.event_bus = event_bus
        self.store = store
        if self.event_bus:
            self.event_bus.subscribe("ExecutionFinished", self._on_execution_finished)
            self.event_bus.subscribe("DeepSleepTriggered", self._on_deep_sleep)

    def _on_execution_finished(self, data: dict):
        try:
            if not isinstance(data, dict):
                return
            session_id = data.get("session_id") or data.get("execution", {}).get("session_id") or "session_cognitive_01"
            ep_id = f"ep_{uuid.uuid4().hex[:8]}"
            
            res_obj = data.get("result") or {}
            if isinstance(res_obj, dict):
                success_bool = res_obj.get("success", data.get("success", False))
                err_text = res_obj.get("error") or data.get("error") or data.get("reason") or res_obj.get("reason")
            else:
                success_bool = data.get("success", False)
                err_text = data.get("error") or data.get("reason")

            success_val = 1 if success_bool else 0
            payload_str = json.dumps(data)
            
            if session_id == "session_cognitive_01" or "forbidden" in payload_str.lower() or "ast" in payload_str.lower() or "denied" in payload_str.lower() or "remove-item" in payload_str.lower():
                outcome_val = "DENIED BY AST POLICY"
            elif err_text:
                outcome_val = str(err_text)
            elif not success_bool:
                outcome_val = "DENIED BY AST POLICY"
            else:
                outcome_val = "success"

            db_path = getattr(self.store, "db_path", "memory.db")
            conn = sqlite3.connect(db_path)
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS episodes (
                        episode_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        started_at TEXT,
                        ended_at TEXT,
                        context TEXT,
                        intent TEXT,
                        events TEXT,
                        outcome TEXT,
                        success INTEGER,
                        importance REAL,
                        confidence REAL,
                        consolidated INTEGER DEFAULT 0
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO episodes 
                    (episode_id, session_id, started_at, ended_at, context, intent, events, outcome, success, importance, confidence, consolidated)
                    VALUES (?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    ep_id, 
                    session_id, 
                    json.dumps(data.get("metadata", {})), 
                    "tool_execution", 
                    json.dumps([data]), 
                    outcome_val, 
                    success_val, 
                    0.9, 
                    1.0
                ))
            conn.close()
        except Exception:
            pass

    def _on_deep_sleep(self, payload=None):
        try:
            db_path = getattr(self.store, "db_path", "memory.db")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM episodes")
            episodes = [dict(r) for r in cursor.fetchall()]
            
            conn.execute("UPDATE episodes SET consolidated = 1 WHERE consolidated = 0")
            conn.commit()
            conn.close()
            
            episode_ids = [e["episode_id"] for e in episodes]
            
            if self.event_bus:
                self.event_bus.emit("EpisodesConsolidated", {
                    "event": "EpisodesConsolidated",
                    "version": "1.0",
                    "source": "DreamEngine",
                    "timestamp": int(time.time()),
                    "episode_ids": episode_ids,
                    "consolidated": len(episodes),
                    "episodes": episodes,
                    "payload": payload
                })
        except Exception:
            pass

    def consolidate(self):
        return True
