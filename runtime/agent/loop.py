from .contracts import AgentTask, AgentStatus
from .state_machine import AgentStateMachine
from .planner import Planner
from .executor import AgentExecutor
from .verifier import Verifier
from .policy import AgentPolicy, PolicyDecision
from .capability_guard import CapabilityGuard
from .ledger_bridge import AgentLedgerBridge
from .retry import RetryGovernor
from .constitution_guard import ConstitutionGuard
from runtime.incidents.registry import IncidentRegistry
from runtime.recovery.actions import RecoveryActions
from runtime.memory.episodic.episode_extractor import EpisodeExtractor
from runtime.memory.episodic.episode_store import EpisodeStore

class AgentLoop:
    def __init__(self):
        self.machine = AgentStateMachine()
        self.planner = Planner()
        self.executor = AgentExecutor()
        self.verifier = Verifier()
        self.policy = AgentPolicy()
        self.capability = CapabilityGuard()
        self.ledger = AgentLedgerBridge()
        self.retry = RetryGovernor()
        self.constitution = ConstitutionGuard()
        self.incidents = IncidentRegistry()
        self.episode_extractor = EpisodeExtractor()
        self.episode_store = EpisodeStore()

    def run(self, objective):
        task = AgentTask(objective=objective)
        self.ledger.record("TASK_CREATED", {"task_id": task.task_id})
        
        if not self.constitution.validate_action(objective):
            self.machine.transition(AgentStatus.HALTED)
            self.ledger.record("CONSTITUTION_VIOLATION", {"objective": objective})
            self.incidents.report("ConstitutionViolation", "AgentLoop", "HIGH", {"objective": objective})
            return {"state": "HALTED", "reason": "Constitution violation: Immutable path target detected", "ledger_events": len(self.ledger.events)}

        self.machine.transition(AgentStatus.PLANNING)
        plan = self.planner.create_plan(task)
        self.ledger.record("PLAN_CREATED", {"plan_id": plan.plan_id})
        
        step = plan.steps[0]
        
        if self.capability.validate(step.capability).value != "VALID":
            self.machine.transition(AgentStatus.HALTED)
            self.incidents.report("CapabilityRejected", "AgentLoop", "MEDIUM", {"capability": step.capability})
            return {"state": "HALTED", "reason": "Capability rejected", "ledger_events": len(self.ledger.events)}
            
        if self.policy.validate(step) != PolicyDecision.ALLOW:
            self.machine.transition(AgentStatus.HALTED)
            self.incidents.report("PolicyDenied", "AgentLoop", "MEDIUM", {"capability": step.capability})
            return {"state": "HALTED", "reason": "Policy denied", "ledger_events": len(self.ledger.events)}
            
        self.ledger.record("CAPABILITY_GRANTED", {"capability": step.capability})
        self.machine.transition(AgentStatus.WAITING_APPROVAL)
        self.machine.transition(AgentStatus.EXECUTING)
        
        result = self.executor.execute(step)
        self.ledger.record("EXECUTION_DONE", {"status": result.status})
        
        self.machine.transition(AgentStatus.VERIFYING)
        verification = self.verifier.verify(result)
        
        if verification.success:
            self.machine.transition(AgentStatus.COMPLETED)
            self.ledger.record("VERIFICATION_OK", {})
            status_str = "SUCCESS"
        else:
            if self.retry.can_retry():
                self.machine.transition(AgentStatus.PLANNING)
                self.incidents.report("ExecutionRetryTriggered", "AgentLoop", "LOW", {"step_id": step.step_id})
                status_str = "RETRY"
            else:
                self.machine.transition(AgentStatus.FAILED)
                self.incidents.report("ExecutionFailedCritical", "AgentLoop", "HIGH", {"step_id": step.step_id})
                status_str = "FAILED"
                try:
                    RecoveryActions.purge_execution_workspace(task.task_id)
                except Exception:
                    pass

        try:
            episode = self.episode_extractor.extract(
                task_id=task.task_id,
                objective=objective,
                status=status_str,
                ledger_events=self.ledger.events
            )
            self.episode_store.save(episode)
            self.ledger.record("EPISODE_SAVED", {"episode_id": getattr(episode, "episode_id", "unknown")})
        except Exception as e:
            self.ledger.record("EPISODE_EXTRACTION_ERROR", {"error": str(e)})

        return {
            "state": self.machine.state.value,
            "verification": verification.reason,
            "task_id": task.task_id,
            "ledger_events": len(self.ledger.events)
        }