"""Model Router Context — Assemblage du contexte avec socle canonique inviolable."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from core.identity.canonical_identity import CanonicalIdentity

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CANONICAL_IDENTITY: CanonicalIdentity | None = None


class ContextAssembler:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or PROJECT_ROOT

    def build_system_prompt(self, caller_context: Optional[str] = None) -> str:
        """
        Règle d'autorité identitaire :
        CanonicalIdentity constitue la base immuable du prompt.
        Le contexte de l'appelant est uniquement annexé en tant que métadonnée opérationnelle.
        """
        global _CANONICAL_IDENTITY
        if _CANONICAL_IDENTITY is None:
            try:
                _CANONICAL_IDENTITY = CanonicalIdentity(root_dir=self.root_dir)
            except Exception as exc:
                raise RuntimeError(f"[IDENTITY FAIL-CLOSED] ModelRouter Context: {exc}") from exc

        canonical_prompt = _CANONICAL_IDENTITY.build_system_prompt(source="router_context", mode="operational")

        if caller_context and caller_context.strip():
            return f"{canonical_prompt}\n\n### [CONTEXTE OPÉRATIONNEL ADDITIONNEL]\n{caller_context.strip()}"
        return canonical_prompt
