"""
core/routing/federated_router.py — Alias Gateway for Federated Router
"""
from core.agent.coder_federation import CoderModelFederationRouter as FederatedRouter
from core.agent.coder_federation import (
    CoderModelFederationRouter,
    TaskProfile,
    TaskComplexity,
    TaskType,
    ContextSize,
    LatencyClass,
    PrivacyRequirement,
    _normalize_model_name,
)
