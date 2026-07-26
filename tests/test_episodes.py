import unittest
from runtime.memory.episode import EpisodeStep
from runtime.memory.episode_extractor import EpisodeExtractor
from runtime.memory.episode_store import EpisodeStore

class TestEpisodePipeline(unittest.TestCase):
    def test_segmentation_and_storage(self):
        # Simulation d'événements de traces et sessions différentes
        raw_events = [
            {
                "event_id": "ev_001",
                "event_type": "ToolExecuted",
                "trace_id": "trace_A",
                "session_id": "session_001",
                "actor": "kernel",
                "timestamp": "2026-07-26T18:00:00",
                "payload": {"capability": {"tool": "filesystem.read"}}
            },
            {
                "event_id": "ev_002",
                "event_type": "ToolExecuted",
                "trace_id": "trace_B",
                "session_id": "session_001",
                "actor": "kernel",
                "timestamp": "2026-07-26T18:00:10",
                "payload": {"capability": {"tool": "powershell.safe.execute"}}
            }
        ]

        extractor = EpisodeExtractor()
        episodes = extractor.extract_from_events(raw_events)

        # On s'attend à 2 épisodes distincts en raison des trace_id différents (trace_A vs trace_B)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].trace_id, "trace_A")
        self.assertEqual(episodes[1].trace_id, "trace_B")

        # Persistance et rechargement
        store = EpisodeStore(":memory:")
        for ep in episodes:
            store.save_episode(ep)

        loaded = store.get_episodes_by_session("session_001")
        self.assertEqual(len(loaded), 2)
        print("\n[EPISODE SEGMENTATION SUCCESS] Segmentation multi-trace validée et persistée.")

if __name__ == "__main__":
    unittest.main()