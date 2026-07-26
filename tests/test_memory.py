import unittest
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest
from runtime.memory.sqlite.store import SQLiteEventStore

class TestMemoryKernel(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(1)
        self.runtime = self.builder.build()
        self.store = self.builder.memory_gateway.store

    def tearDown(self):
        self.runtime.stop()

    def test_memory_event_sourcing_on_execution(self):
        # 1. On exécute une action traçable
        req = ToolRequest(name="filesystem.read", arguments={"path": "runtime/tools/manifest.json"})
        res = self.runtime.execute(req, "session_test_mem_001")
        self.assertTrue(res.success)

        # 2. On s'assure que l'EventBus a eu le temps de flusher (Queue asynchrone)
        self.runtime.event_bus.stop_and_wait()

        # 3. On interroge la mémoire (Event Store SQLite)
        events = self.store.get_events_by_session("session_test_mem_001")

        self.assertGreater(len(events), 0, "L'événement aurait dû être mémorisé.")

        mem_event = events[0]
        self.assertEqual(mem_event["event_type"], "ToolExecuted")
        self.assertEqual(mem_event["actor"], "kernel")
        self.assertIn("execution", mem_event["payload"])

        print(f"\n[EVENT SOURCING] Fact stored: ID {mem_event['event_id']} (Trace: {mem_event['trace_id']})")

    def test_memory_survives_restart(self):
        # 1. Instance A du Runtime
        builder1 = RuntimeBuilder().with_allowed_level(1)
        runtime1 = builder1.build()

        req = ToolRequest(name="filesystem.read", arguments={"path": "runtime.json"})
        runtime1.execute(req, "session_test_restart_001")
        runtime1.event_bus.stop_and_wait()

        # Récupération des événements avant arrêt
        events_before = runtime1.memory_gateway.store.get_events_by_session("session_test_restart_001")
        self.assertGreater(
            len(events_before),
            0,
            "Un événement doit exister après exécution dans l'instance A"
        )
        trace_id_before = events_before[0]["trace_id"] if isinstance(events_before[0], dict) else events_before[0].trace_id

        # Simulation de la mort du processus / nettoyage de la première instance
        runtime1.stop()
        del runtime1
        del builder1

        # 2. Instance B du Runtime (Nouveau processus logique)
        builder2 = RuntimeBuilder().with_allowed_level(1)
        runtime2 = builder2.build()

        events_after = runtime2.memory_gateway.store.get_events_by_session("session_test_restart_001")
        self.assertGreater(
            len(events_after),
            0,
            "La mémoire doit persister et être accessible par l'instance B du runtime"
        )
        trace_id_after = events_after[0]["trace_id"] if isinstance(events_after[0], dict) else events_after[0].trace_id

        self.assertEqual(
            trace_id_before,
            trace_id_after,
            "Le trace_id de l'événement doit être rigoureusement identique après redémarrage"
        )
        runtime2.stop()
        print(f"\n[PERSISTENCE SUCCESS] Événement retrouvé après redémarrage (Trace ID: {trace_id_after})")

if __name__ == "__main__":
    unittest.main()