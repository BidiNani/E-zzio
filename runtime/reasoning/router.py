from enum import Enum


class ExecutionTarget(str, Enum):
    LOCAL_OLLAMA = "LOCAL_OLLAMA"
    LOCAL_HEAVY = "LOCAL_HEAVY"
    CLOUD_API = "CLOUD_API"


class CognitiveRouter:
    """Routes cognitive tasks based on complexity (Local-First)."""

    @staticmethod
    def route(task_type: str, complexity_score: float) -> ExecutionTarget:
        if complexity_score < 0.4:
            return ExecutionTarget.LOCAL_OLLAMA
        elif complexity_score < 0.8:
            return ExecutionTarget.LOCAL_HEAVY
        else:
            return ExecutionTarget.CLOUD_API
