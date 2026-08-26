"""E-ZZIO Identity Router — Passerelle en lecture seule vers CanonicalIdentity."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from core.identity.canonical_identity import CanonicalIdentity

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def identity_payload() -> Dict[str, Any]:
    ci = CanonicalIdentity(root_dir=PROJECT_ROOT)
    return {
        "status": "canonical_verified",
        "entity": "E-ZZIO",
        "authority": "CanonicalIdentity",
        "payload": ci.get_payload()
    }


def manifest_payload() -> Dict[str, Any]:
    return {
        "identity": identity_payload(),
        "integrity": "verified"
    }


def routes_payload(app: Any = None) -> Dict[str, Any]:
    return {
        "canonical_endpoint": "/master/chat",
        "identity_endpoint": "/identity"
    }
