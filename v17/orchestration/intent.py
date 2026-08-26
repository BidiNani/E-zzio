from pydantic import BaseModel
from typing import Dict, Any, List
from v17.orchestration.classifier import classify_user_prompt
from v17.control.classifier import classify_action_risk
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity

class StructuredIntent(BaseModel):
    raw_prompt: str
    task_type: str
    complexity: str
    risk_level: str
    requires_tools: bool
    requires_research: bool
    requires_human_approval: bool
    confidence: float

class IntentEngine:
    def parse_intent(self, prompt: str) -> StructuredIntent:
        task_type, complexity, conf = classify_user_prompt(prompt)
        risk, human_req = classify_action_risk(f"TASK_{task_type}", "system")

        intent = StructuredIntent(
            raw_prompt=prompt,
            task_type=task_type,
            complexity=complexity,
            risk_level=risk.value,
            requires_tools=task_type in ["CODE", "FORENSIC", "CRITICAL_OPERATION"],
            requires_research=task_type == "RESEARCH",
            requires_human_approval=human_req,
            confidence=conf
        )

        global_event_buffer.publish(
            event_type="intent.created",
            source="v17.orchestration.intent",
            payload={"task_type": task_type, "risk": risk.value, "approval_required": human_req},
            severity=EventSeverity.INFO
        )

        return intent

intent_engine = IntentEngine()
