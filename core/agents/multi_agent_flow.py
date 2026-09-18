"""E-ZZIO — flux multi-agents délibératif (débat méthodique borné).

3 temps : analyse/découpage → table ronde (Code propose, Qualité critique,
Architecte arbitre) → synthèse ADR. Exécution via DeliberationOrchestrator
(fédération gouvernée, cap 2 tours). Déclenchement auto : tâche > STANDARD,
activable par EZZIO_MULTI_AGENT=1 (désactivé par défaut, sans surprise).
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("ezzio.multi_agent")

DOMAIN_KEYWORDS = {
    "code": ("def ", "class ", "fonction", "bug", "patch", "script", ".py",
             "refactor", "implement"),
    "architecture": ("architecture", "design", "structure", "pattern",
                     "système", "system", "governance", "ADR"),
    "securite": ("sécur", "secur", "secret", "vuln", "fail-closed", "audit",
                 "permission", "auth"),
}

AUTO_TRIGGER_ENV = "EZZIO_MULTI_AGENT"


def analyze_domains(request: str) -> list[str]:
    """Découpe une requête en domaines (lexical déterministe, 0 token)."""
    text = (request or "").lower()
    found = [d for d, kws in DOMAIN_KEYWORDS.items()
             if any(k in text for k in kws)]
    return found or ["code"]


def should_auto_trigger(profile=None, mission_profile: str = "STANDARD") -> bool:
    """Déclenchement auto : complexité > STANDARD + flag explicite."""
    if os.getenv(AUTO_TRIGGER_ENV, "0") != "1":
        return False
    if profile is not None:
        try:
            return str(getattr(profile.complexity, "value",
                               profile.complexity)).upper() in ("COMPLEX", "CRITICAL")
        except Exception:
            return False
    return str(mission_profile or "STANDARD").upper() in ("COMPLEX", "CRITICAL")


class MultiAgentFlow:
    """Orchestre débat Code → Qualité → Architecte → synthèse ADR."""

    ROLES = ("coder", "quality", "architect")

    def __init__(self, federation=None, blackboard=None):
        from core.agents.orchestrator import DeliberationOrchestrator
        self._delegate_cls = DeliberationOrchestrator
        self.federation = federation
        self.blackboard = blackboard

    async def run(self, request: str, skeleton: str = "") -> dict[str, Any]:
        from core.agents.orchestrator import DeliberationOrchestrator
        domains = analyze_domains(request)
        orch = DeliberationOrchestrator(federation=self.federation,
                                        blackboard=self.blackboard)
        adrs = []
        for domain in domains:
            adr = await orch.deliberate(
                f"[{domain}] {request}", skeleton or f"contexte:{domain}")
            adrs.append({"domain": domain, "adr_id": adr.adr_id,
                         "title": adr.title, "decision": adr.decision})
        synth = "\n".join(f"### {a['domain']}\n{a['decision']}" for a in adrs)
        return {"domains": domains, "consensus": synth, "adrs": adrs}
