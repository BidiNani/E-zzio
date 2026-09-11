"""E-ZZIO qualification policies."""
from __future__ import annotations
import os
from typing import Any
from .free_only import FREE_POLICY_NAME, FREE_POLICY_VERSION, accept_free_only, annotate_free_status

QUALIFICATION_POLICY = "FREE_ONLY"
FAIL_CLOSED = True

def policy_name() -> str:
    return FREE_POLICY_NAME

def is_free_only() -> bool:
    return True

def policy_allows(model: dict[str, Any]) -> bool:
    return accept_free_only(model)

def prepare_model(model: dict[str, Any]) -> dict[str, Any]:
    res = annotate_free_status(model)
    res["qualification_policy"] = FREE_POLICY_NAME
    res["qualification_policy_version"] = FREE_POLICY_VERSION
    res["policy_allowed"] = policy_allows(res)
    return res

def reject_reason(model: dict[str, Any]) -> str | None:
    prepared = prepare_model(model)
    if prepared["policy_allowed"]:
        return None
    if prepared.get("free_status") == "PAID":
        return "free_only_reject_paid_model"
    if prepared.get("free_status") == "UNKNOWN":
        return "free_only_reject_unknown_pricing"
    return "qualification_policy_denied"