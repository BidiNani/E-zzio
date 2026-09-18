"""
E-ZZIO OS — Knowledge Subsystem
Provides sovereign introspection and self-awareness capabilities based on verifiable artifacts.
"""

from core.knowledge.drift_detector import DriftResult, DriftVerdict, ForensicDriftDetector
from core.knowledge.self_awareness import IntrospectionResult, SelfAwarenessGateway

__all__ = [
    "SelfAwarenessGateway",
    "IntrospectionResult",
    "ForensicDriftDetector",
    "DriftVerdict",
    "DriftResult",
]
