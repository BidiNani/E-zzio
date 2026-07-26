import unittest
import tempfile
from pathlib import Path
from runtime.memory.events import RuntimeEvent
from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.memory.episode_store import EpisodeStore
from runtime.memory.episode_extractor import EpisodeExtractor
from runtime.memory.episode_recovery import EpisodeRecovery

class TestEpisodeRecovery(unittest.TestCase):
    def test_recovery_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = str(Path(tmpdir) / "cognitive_store.db")

            # Simulation Processus A : Écriture d'événements bruts sans consolidation
            event_store_a = SQLiteEventStore(db_file)
            event_a = RuntimeEvent(
                event_id="ev_rec_001",
                event_type="ToolExecuted",
                trace_id="trace_rec_A",
                session_id="session_rec_001",
                actor="kernel",
                timestamp="2026-07-26T20:00:00",
                payload={
                    "capability": {"tool": "filesystem.read"},
                    "execution": {"success": True, "duration_sec": 0.003}
                }
            )
            event_store_a.append_event(event_a, retention_score=0.9)
            event_store_a.close()
            del event_store_a

            # Simulation Processus B (Redémarrage / Démarrage à froid)
            event_store_b = SQLiteEventStore(db_file)
            episode_store_b = EpisodeStore(db_file)
            extractor = EpisodeExtractor()

            recovery = EpisodeRecovery(event_store_b, episode_store_b, extractor)
            rebuilt_episodes = recovery.recover()

            # Vérifications post-reconstruction
            self.assertEqual(len(rebuilt_episodes), 1)
            ep = rebuilt_episodes[0]
            self.assertEqual(ep.session_id, "session_rec_001")
            self.assertEqual(ep.trace_id, "trace_rec_A")
            self.assertEqual(ep.goal, "Execute tool: filesystem.read")

            unconsolidated = event_store_b.get_unconsolidated_events()
            self.assertEqual(len(unconsolidated), 0, "Tous les événements récupérés doivent être marqués consolidés")

            event_store_b.close()
            episode_store_b.close()

            print(f"\n[RECOVERY SUCCESS] Events found: 1, Episodes rebuilt: 1, Events consolidated: 1")

if __name__ == "__main__":
    unittest.main()