"""Runtime Context Builder — Consommateur strict de CanonicalIdentity."""
from __future__ import annotations
from pathlib import Path
from core.identity.canonical_identity import CanonicalIdentity

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CANONICAL_IDENTITY: CanonicalIdentity | None = None


def get_base_system_prompt() -> str:
    """Retourne l'identité canonique en mode Fail-Closed strict (zéro fallback textuel)."""
    global _CANONICAL_IDENTITY
    if _CANONICAL_IDENTITY is None:
        try:
            _CANONICAL_IDENTITY = CanonicalIdentity(root_dir=PROJECT_ROOT)
        except Exception as exc:
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] ContextBuilder: {exc}") from exc
    return _CANONICAL_IDENTITY.build_system_prompt(source="runtime_context", mode="operational")
