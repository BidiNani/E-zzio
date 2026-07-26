import unittest
import subprocess
import sys
from pathlib import Path
from runtime.memory.sqlite.store import SQLiteEventStore

class TestProcessPersistence(unittest.TestCase):
    def test_database_survives_process_termination(self):
        # 1. Lancement d'un processus isolé A pour produire un événement
        script_producer = """
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest

builder = RuntimeBuilder().with_allowed_level(1)
runtime = builder.build()
req = ToolRequest(name="filesystem.read", arguments={"path": "runtime.json"})
runtime.execute(req, "session_subprocess_001")
runtime.event_bus.stop_and_wait()
runtime.stop()
print("PRODUCER_DONE")
"""
        res_prod = subprocess.run([sys.executable, "-c", script_producer], capture_output=True, text=True)
        self.assertEqual(res_prod.returncode, 0, f"Erreur du processus producteur: {res_prod.stderr}")
        self.assertIn("PRODUCER_DONE", res_prod.stdout)

        # 2. Lancement d'un processus ou lecture directe depuis un store frais (Processus B)
        # On instancie un nouveau store pointant vers le même fichier SQLite
        store = SQLiteEventStore()
        events = store.get_events_by_session("session_subprocess_001")

        self.assertGreater(
            len(events), 
            0, 
            "Le processus B doit retrouver l'événement enregistré par le processus A dans SQLite"
        )
        
        mem_event = events[0]
        self.assertEqual(mem_event["event_type"], "ToolExecuted")
        self.assertEqual(mem_event["session_id"], "session_subprocess_001")
        print(f"\n[INTER-PROCESS SUCCESS] Événement récupéré inter-processus (Trace ID: {mem_event['trace_id']})")

if __name__ == "__main__":
    unittest.main()