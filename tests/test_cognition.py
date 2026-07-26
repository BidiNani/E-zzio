import unittest
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest
from runtime.memory.sqlite.store import SQLiteEventStore

class TestCognitiveMemory(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(1)
        self.runtime = self.builder.build()
        self.store = self.builder.memory_gateway.store

    def tearDown(self):
        self.runtime.stop()

    def test_episodic_memory_formation_on_failure(self):
        # 1. On provoque un échec délibéré (haute saillance)
        req = ToolRequest(name="powershell.safe.execute", arguments={"command": "Remove-Item forbidden.txt"})
        res = self.runtime.execute(req, "session_cognitive_01")
        
        self.assertFalse(res.success) # Doit échouer (bloqué par AST)

        # 2. Flush de l'EventBus asynchrone
        self.runtime.event_bus.stop_and_wait()

        # 3. Vérification de l'ADN (Event Sourcing)
        import sqlite3
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM episodes WHERE session_id = 'session_cognitive_01'")
            episodes = [dict(r) for r in cursor.fetchall()]
        
        self.assertGreater(len(episodes), 0, "L'épisode d'échec aurait dû être cristallisé.")
        
        ep = episodes[0]
        self.assertFalse(ep["success"])
        self.assertIn("DENIED BY AST POLICY", ep["outcome"])
        self.assertGreater(ep["importance"], 0.7, "Un échec de sécurité doit avoir une haute importance biologique.")
        
        print(f"\n[COGNITION] Épisode cristallisé : {ep['episode_id']} | Outcome: {ep['outcome']} | Importance: {ep['importance']}")

if __name__ == "__main__":
    unittest.main()