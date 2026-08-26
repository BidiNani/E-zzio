from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.metrics import ExecutionMetric
from runtime.recovery.queue.bus import RecoveryEventBus
from runtime.recovery.contracts import IncidentBundle, Severity, IncidentCategory
from runtime.gateway.session import SessionManager
from runtime.core.ezzio_core import EzzioCore
import uuid
import time
from datetime import datetime, timezone


class CognitiveRuntimeAdapter:
    """Interface sécurisée exposant le Noyau E-zzio aux APIs réseau."""

    def __init__(self, telemetry: TelemetryCollector, recovery: RecoveryEventBus):
        self.telemetry = telemetry
        self.recovery = recovery
        self.sessions = SessionManager()
        self.core = EzzioCore(telemetry=self.telemetry, recovery=self.recovery)

    async def process(self, user_id: str, message: str) -> str:
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        session = self.sessions.get_or_create(user_id)

        metric = ExecutionMetric(
            exec_id=exec_id, action_name="core_think_cycle", status="RUNNING", duration_ms=0.0, cost=0.0, risk_level="LOW"
        )

        try:
            # Appel au VRAI moteur cognitif (qui route vers Gemini ou Local)
            response_text = await self.core.think(user_id=user_id, message=message, context_history=session["history"])

            session["message_count"] += 1
            session["history"].append({"role": "user", "content": message})
            session["history"].append({"role": "assistant", "content": response_text})

            metric.status = "SUCCESS"
            metric.duration_ms = round((time.time() - start_time) * 1000, 2)
            self.telemetry.record_execution(metric)

            return response_text

        except Exception as e:
            metric.status = "FAILED"
            metric.duration_ms = round((time.time() - start_time) * 1000, 2)
            self.telemetry.record_execution(metric)

            bundle = IncidentBundle(
                incident_id=f"inc_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                severity=Severity.HIGH,
                severity_score=70,
                category=IncidentCategory.UNHANDLED_EXCEPTION,
                execution_id=exec_id,
                action_name="core_think_cycle",
                trace_id=None,
                span_id=None,
                state_trace=[],
                context_signature_valid=True,
                payload_hash="",
                bundle_hash="",
                telemetry_snapshot={},
                findings=[],
                root_candidates=[f"COGNITIVE_EXCEPTION: {str(e)}"],
                metadata={"user_id": user_id},
            )
            self.recovery.publish_incident(bundle)
            return "⚠️ Erreur cognitive sévère détectée. Le système de récupération a été engagé."
