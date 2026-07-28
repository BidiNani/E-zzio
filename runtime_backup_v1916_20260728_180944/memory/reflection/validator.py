import sqlite3
import json
import uuid
from datetime import datetime
from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.core.events import EventBus

class PromotionController:
    """Cortex Préfrontal : Évalue les propositions avec Zero-Trust et gère REVIEW_REQUIRED."""
    def __init__(self, store: SQLiteEventStore, event_bus: EventBus):
        self.store = store
        self.event_bus = event_bus

    def evaluate_pending_proposals(self):
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM reflection_proposals WHERE status = 'PENDING'")
            pendings = [dict(r) for r in cursor.fetchall()]

        for prop in pendings:
            self._evaluate_single(prop)

    def _evaluate_single(self, prop: dict):
        try:
            evidence = json.loads(prop["evidence"])
        except Exception:
            evidence = []
            
        confidence = prop["confidence"]
        
        # Règle de consolidation industrielle (3+ = PROMOTED, 2 = REVIEW, <2 = REJECTED)
        status = "REJECTED"
        if confidence >= 0.85:
            if len(evidence) >= 3:
                status = "PROMOTED"
                self._promote_to_cortex(prop, evidence)
            elif len(evidence) == 2:
                status = "REVIEW_REQUIRED" # Suspendu pour validation humaine ou deep check
            else:
                status = "REJECTED" # Une seule observation = simple anecdote

        with self.store._lock:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.execute(
                    "UPDATE reflection_proposals SET status = ?, validated_at = ? WHERE proposal_id = ?",
                    (status, __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), prop["proposal_id"])
                )
        
        self.event_bus.emit("AuditLog", {"message": f"Proposal {prop['proposal_id']} évaluée -> {status}.", "level": "INFO"})

    def _promote_to_cortex(self, prop: dict, evidence: list):
        ptype = prop["type"]
        now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        
        with self.store._lock:
            with sqlite3.connect(self.store.db_path) as conn:
                if ptype == "fact_candidate":
                    conn.execute("INSERT OR REPLACE INTO facts (fact_id, statement, confidence, origin_episodes, created_at, last_verified) VALUES (?, ?, ?, ?, ?, ?)", (f"fact_{uuid.uuid4().hex[:8]}", prop["statement"], prop["confidence"], json.dumps(evidence), now, now))
                elif ptype == "rule_candidate":
                    conn.execute("INSERT OR REPLACE INTO rules (rule_id, condition, action, confidence, origin_episodes, is_active) VALUES (?, ?, ?, ?, ?, ?)", (f"rule_{uuid.uuid4().hex[:8]}", "General", prop["statement"], prop["confidence"], json.dumps(evidence), 1))
                elif ptype == "belief_update":
                    conn.execute("INSERT OR REPLACE INTO beliefs (belief_id, statement, confidence, origin_episodes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (f"bel_{uuid.uuid4().hex[:8]}", prop["statement"], prop["confidence"], json.dumps(evidence), now, now))
                elif ptype == "skill_candidate":
                    conn.execute("INSERT OR REPLACE INTO skills (skill_id, name, description, trigger, procedure, confidence, origin_episodes, last_used) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (f"skill_{uuid.uuid4().hex[:8]}", prop["statement"][:30], prop["statement"], "general", json.dumps([]), prop["confidence"], json.dumps(evidence), now))