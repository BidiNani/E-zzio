from typing import Dict, Any, List, Optional
from runtime.cognition.state import CognitiveState
from runtime.cognition.events import EventBus
from runtime.reasoning.planner import DeterministicPlanner
from runtime.action.executor import ActionExecutor
from runtime.learning.feedback import FeedbackEngine


class CognitiveLoop:
    """Complete controlled cognitive cycle engine running step-by-step (run_once)."""

    def __init__(self, brain=None):
        self.brain = brain
        self.state = CognitiveState.IDLE
        self.event_bus = EventBus()
        self.planner = DeterministicPlanner()
        self.executor = ActionExecutor(brain)
        self.feedback_engine = FeedbackEngine()

        self.last_observation: Optional[Dict[str, Any]] = None
        self.last_analysis: Optional[Dict[str, Any]] = None
        self.last_decision: Optional[List[Dict[str, Any]]] = None

    def observe(self, raw_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.state = CognitiveState.OBSERVING
        observation = raw_input or {"source": "idle_tick", "importance": 0.1, "category": "general"}
        self.last_observation = observation
        self.event_bus.emit("OBSERVATION_RECEIVED", observation)
        return observation

    def analyze(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        self.state = CognitiveState.ANALYZING
        importance = observation.get("importance", 0.5)
        analysis = {"importance": importance, "category": observation.get("category", "general"), "requires_action": importance >= 0.5}
        self.last_analysis = analysis
        self.event_bus.emit("ANALYSIS_COMPLETED", analysis)
        return analysis

    def retrieve(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        memories = []
        if self.brain and hasattr(self.brain, "long_term"):
            memories = self.brain.long_term.search_knowledge_by_keywords([analysis.get("category", "general")])
        return memories

    def reason(self, analysis: Dict[str, Any], memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.state = CognitiveState.REASONING
        plans = self.planner.plan(analysis)
        self.last_decision = plans
        self.event_bus.emit("REASONING_DECIDED", {"plans_count": len(plans)})
        return plans

    def act(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.state = CognitiveState.ACTING
        results = []
        for plan in plans:
            res = self.executor.execute(plan)
            results.append(res)
        self.event_bus.emit("ACTION_COMPLETED", {"results_count": len(results)})
        return results

    def learn(self, action_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.state = CognitiveState.LEARNING
        total_delta = 0.0
        for res in action_results:
            fb = self.feedback_engine.process_feedback(res)
            total_delta += fb.get("confidence_delta", 0.0)

        feedback_summary = {"status": "PROCESSED", "total_confidence_delta": round(total_delta, 2)}
        self.event_bus.emit("LEARNING_FEEDBACK_PROCESSED", feedback_summary)
        self.state = CognitiveState.IDLE
        return feedback_summary

    def cycle(self, raw_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            obs = self.observe(raw_input)
            ana = self.analyze(obs)
            mem = self.retrieve(ana)
            dec = self.reason(ana, mem)
            res = self.act(dec)
            lrn = self.learn(res)
            return {"state": self.state.value, "observation": obs, "plans": dec, "execution": res, "feedback": lrn}
        except Exception as e:
            self.state = CognitiveState.ERROR
            self.event_bus.emit("ERROR_OCCURRED", {"error": str(e)})
            return {"state": self.state.value, "error": str(e)}

    def run_once(self, raw_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.cycle(raw_input)
