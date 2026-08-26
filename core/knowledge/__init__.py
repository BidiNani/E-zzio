"""
E-ZZIO OS — Knowledge Subsystem
Provides sovereign introspection and self-awareness capabilities based on verifiable artifacts.
"""

from core.knowledge.self_awareness import SelfAwarenessGateway, IntrospectionResult
from core.knowledge.drift_detector import ForensicDriftDetector, DriftVerdict, DriftResult

__all__ = [
    "SelfAwarenessGateway",
    "IntrospectionResult",
    "ForensicDriftDetector",
    "DriftVerdict",
    "DriftResult",
]
