import unittest
import asyncio
from runtime.gateway import SessionManager, get_system_health, CognitiveRuntimeAdapter
from runtime.telemetry.collector import TelemetryCollector
from runtime.recovery.queue.bus import RecoveryEventBus

class TestGatewayHardening(unittest.TestCase):

    def test_session_manager_isolation(self):
        manager = SessionManager()
        session1 = manager.get_or_create("user_A")
        session2 = manager.get_or_create("user_B")
        
        session1["message_count"] += 5
        self.assertEqual(manager.get_or_create("user_A")["message_count"], 5)
        self.assertEqual(manager.get_or_create("user_B")["message_count"], 0)

    def test_health_endpoint_logic(self):
        health_full = get_system_health(TelemetryCollector(), RecoveryEventBus())
        self.assertEqual(health_full["status"], "ONLINE")
        self.assertEqual(health_full["telemetry"], "RUNNING")
        self.assertEqual(health_full["recovery"], "ARMED")

    def test_adapter_triggers_telemetry(self):
        collector = TelemetryCollector()
        bus = RecoveryEventBus()
        adapter = CognitiveRuntimeAdapter(telemetry=collector, recovery=bus)
        
        async def run_adapter():
            return await adapter.process("test_user", "Bonjour")
            
        res = asyncio.run(run_adapter())
        self.assertIn("Message #1", res)
        # Vérifie que la file de télémétrie a capturé l'exécution
        self.assertEqual(collector.get_queue_size(), 1)

if __name__ == "__main__":
    unittest.main()
