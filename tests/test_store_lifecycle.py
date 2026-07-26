import unittest
from runtime.memory.sqlite.store import SQLiteEventStore
from runtime.memory.episode_store import EpisodeStore

class TestStoreLifecycle(unittest.TestCase):
    def test_sqlite_event_store_lifecycle_and_idempotence(self):
        store = SQLiteEventStore(":memory:")
        
        # Double fermeture (idempotence)
        store.close()
        store.close()

        # Tentative d'écriture après fermeture
        with self.assertRaises(RuntimeError):
            store.append_event(None)

    def test_episode_store_lifecycle_and_idempotence(self):
        store = EpisodeStore(":memory:")
        
        # Double fermeture (idempotence)
        store.close()
        store.close()

        # Tentative de lecture/écriture après fermeture
        with self.assertRaises(RuntimeError):
            store.get_episodes_by_session("any_session")

if __name__ == "__main__":
    unittest.main()