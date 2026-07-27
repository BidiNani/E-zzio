from typing import Dict, Any, Optional
from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.metrics import ExecutionMetric
from runtime.recovery.queue.bus import RecoveryEventBus
from runtime.recovery.contracts import IncidentBundle, Severity, IncidentCategory
from runtime.gateway.session import SessionManager
import uuid
import time
from datetime import datetime, timezone

class CognitiveRuntimeAdapter:
    """Pont entre l'API (FastAPI) et les moteurs internes (Memory, Routing LLM, Telemetry, Recovery)."""
    
    def __init__(self, telemetry: TelemetryCollector, recovery: RecoveryEventBus):
        self.telemetry = telemetry
        self.recovery = recovery
        self.sessions = SessionManager()

    async def process(self, user_id: str, message: str) -> str:
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        session = self.sessions.get_or_create(user_id)
        session["message_count"] += 1
        session["history"].append({"role": "user", "content": message})

        metric = ExecutionMetric(
            exec_id=exec_id,
            action_name="cognitive_processing",
            status="RUNNING",
            duration_ms=0.0,
            cost=0.0,
            risk_level="LOW"
        )

        try:
            # TODO: Remplacer par l'appel au Model Router (Ollama/Gemini)
            response_text = f"🧠 [Cognitive Core] Contexte chargé. Message #{session['message_count']} traité. (Routeur LLM en attente de la Phase 4)."
            
            session["history"].append({"role": "assistant", "content": response_text})
            
            metric.status = "SUCCESS"
            metric.duration_ms = round((time.time() - start_time) * 1000, 2)
            self.telemetry.record_execution(metric)
            
            return response_text
            
        except Exception as e:
            metric.status = "FAILED"
            metric.duration_ms = round((time.time() - start_time) * 1000, 2)
            self.telemetry.record_execution(metric)
            
            # Transfert au RecoveryEventBus pour décision autonome
            bundle = IncidentBundle(
                incident_id=f"inc_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                severity=Severity.HIGH,
                severity_score=70,
                category=IncidentCategory.UNHANDLED_EXCEPTION,
                execution_id=exec_id,
                action_name="cognitive_processing",
                trace_id=None,
                span_id=None,
                state_trace=[],
                context_signature_valid=True,
                payload_hash="",
                bundle_hash="",
                telemetry_snapshot={},
                findings=[],
                root_candidates=[f"EXCEPTION: {str(e)}"],
                metadata={"user_id": user_id}
            )
            self.recovery.publish_incident(bundle)
            return "⚠️ Je rencontre une perturbation cognitive interne. Mon moteur de récupération autonome traite l'incident."
