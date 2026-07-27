from dataclasses import dataclass
from typing import Optional

@dataclass
class ExecutionMetric:
    """Conteneur structuré des métriques d'exécution individuelles."""
    exec_id: str
    action_name: str
    status: str
    duration_ms: float
    cost: float
    risk_level: str
    category: Optional[str] = None
