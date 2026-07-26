import unittest
import json
import sqlite3
import threading
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest
from runtime.memory.reflection.validator import PromotionController

class TestPhase79Hardening(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(2)
        self.runtime = self.builder.build()
        self.store = self.builder.memory_gateway.store
        self.validator = PromotionController(self.store, self.runtime.event_bus)

    def tearDown(self):
        self.runtime.stop()

    def test_end_to_end_provenance_and_schema(self):
        """Test ultime Phase 7.9 : Vérifie le contrat versionné v1.0 et la provenance exacte des épisodes de SQLite."""
        
        # 1. Insertion de 3 épisodes avec des IDs spécifiques traçables
        target_ids = ["ep_prov_01", "ep_prov_02", "ep_prov_03"]
        with self.store._lock:
            with sqlite3.connect(self.store.db_path) as conn:
                for eid in target_ids:
                    conn.execute(
                        "INSERT OR REPLACE INTO episodes (episode_id, session_id, started_at, ended_at, context, intent, events, outcome, success, importance, confidence, consolidated) VALUES (?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, ?, ?, ?, 0)",
                        (eid, "sess_provenance", json.dumps({"env": "windows"}), "test_provenance", "[]", "fail", 0, 0.9, 1.0)
                    )

        # 2. Interception par un test de provenance stricte de l'enveloppe
        captured_envelopes = []
        provenance_event = threading.Event()

        def provenance_probe(envelope):
            captured_envelopes.append(envelope)
            provenance_event.set()

        self.runtime.event_bus.subscribe("EpisodesConsolidated", provenance_probe)

        # 3. Déclenchement du sommeil profond
        self.runtime.event_bus.emit("DeepSleepTriggered", {"unresolved_patterns": 3})

        # 4. Attente de la résolution asynchrone
        success = provenance_event.wait(timeout=5.0)
        self.assertTrue(success, "Timeout : Le cycle de provenance n'a pas bouclé.")

        # 5. Validation rigoureuse du contrat versionné (Schema v1.0 & Provenance exacte)
        self.assertGreater(len(captured_envelopes), 0)
        env = captured_envelopes[0]
        
        self.assertEqual(env.get("event"), "EpisodesConsolidated")
        self.assertEqual(env.get("version"), "1.0")
        self.assertEqual(env.get("source"), "DreamEngine")
        self.assertIn("timestamp", env)
        
        # Vérification de la provenance exacte (les IDs de SQLite doivent correspondre)
        received_ids = env.get("episode_ids", [])
        for tid in target_ids:
            self.assertIn(tid, received_ids, f"L'épisode {tid} issu de SQLite manque dans la traçabilité de l'événement.")

        print(f"\n[PHASE 7.9 HARDENING VALIDÉ] Contrat v1.0 et provenance de bout en bout certifiés pour les IDs : {received_ids}")

if __name__ == "__main__":
    unittest.main()