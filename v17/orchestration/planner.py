from pydantic import BaseModel, Field
from typing import List, Dict, Any
from v17.orchestration.intent import StructuredIntent, intent_engine
from v17.models.intelligence_router import model_intelligence_router, RouteDecision
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity

class PlanStep(BaseModel):
    step_index: int
    description: str
    action_type: str
    risk_level: str
    confirmation_required: bool

class OrchestrationPlan(BaseModel):
    plan_id: str
    intent: StructuredIntent
    route_decision: RouteDecision
    steps: List[PlanStep]
    total_steps: int
    requires_approval: bool

class PlannerEngine:
    def build_plan(self, prompt: str) -> OrchestrationPlan:
        intent = intent_engine.parse_intent(prompt)
        route = model_intelligence_router.route_for_task(intent.task_type)

        steps = []
        steps.append(PlanStep(
            step_index=1,
            description="Classification & validation des contraintes de sécurité",
            action_type="GET_SYSTEM_STATE",
            risk_level="READ_ONLY",
            confirmation_required=False
        ))

        if intent.requires_tools:
            steps.append(PlanStep(
                step_index=2,
                description=f"Exécution outillée de la tâche {intent.task_type}",
                action_type=f"EXEC_{intent.task_type}",
                risk_level=intent.risk_level,
                confirmation_required=intent.requires_human_approval
            ))

        steps.append(PlanStep(
            step_index=len(steps) + 1,
            description="Synthèse et vérification de conformité des résultats",
            action_type="VERIFY_RESULT",
            risk_level="READ_ONLY",
            confirmation_required=False
        ))

        import uuid
        plan = OrchestrationPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            intent=intent,
            route_decision=route,
            steps=steps,
            total_steps=len(steps),
            requires_approval=any(s.confirmation_required for s in steps)
        )

        global_event_buffer.publish(
            event_type="plan.created",
            source="v17.orchestration.planner",
            payload={"plan_id": plan.plan_id, "steps_count": plan.total_steps, "model": route.selected_model},
            severity=EventSeverity.INFO
        )

        return plan

planner_engine = PlannerEngine()
