"""E-ZZIO — orchestrateur de délibération bornée (cap 2 tours).

Tour 1 : Coder + Architect proposent isolément (JSON AgentContribution).
Tour 2 : Critique via fédération (profil FAST) sur les diffs.
Arbitrage : Superviseur (profil STANDARD) fusionne → ADR.
Routage via CoderModelFederationRouter : fallbacks 429/transitoires natifs.
(Pool Groq direct HS/403 : non utilisé, fédération seule autorité.)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import List, Optional

from core.agents.blackboard import Blackboard
from core.agents.schemas import ADRRecord, AgentContribution
from core.agents.token_frugality import enforce_unified_diff, prune_deliberation_context

logger = logging.getLogger("ezzio.deliberation")

MAX_ROUNDS = 2
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_contribution(raw: str, agent_id: str, phase: str) -> AgentContribution:
    """Extrait le JSON strict, fail-closed si invalide."""
    m = _JSON_RE.search(raw or "")
    if not m:
        raise ValueError(f"[{agent_id}] réponse non-JSON, contribution rejetée.")
    data = json.loads(m.group(0))
    data.setdefault("agent_id", agent_id)
    data.setdefault("phase", phase)
    if isinstance(data.get("summary", ""), str):
        data["summary"] = data["summary"][:200]
    return AgentContribution(**data)


class DeliberationOrchestrator:
    def __init__(self, federation=None, blackboard: Optional[Blackboard] = None):
        if federation is None:
            from core.agent.coder_federation import coder_federation_router
            federation = coder_federation_router
        self.federation = federation
        self.board = blackboard or Blackboard()

    def _profile(self, task_type: str):
        from core.agent.coder_federation import (
            ContextSize, LatencyClass, PrivacyRequirement,
            TaskComplexity, TaskProfile, TaskType,
        )
        task_upper = (task_type or "").upper()
        if task_upper in ("CODING", "CODE", "CRITIQUE", "ARCHITECT", "SUPERVISEUR"):
            tt = TaskType.CODING
        elif task_upper in ("REASONING", "STRATEGIC", "DELIBERATE"):
            tt = TaskType.REASONING
        else:
            tt = TaskType.GENERAL

        fast = task_upper == "CRITIQUE"
        return TaskProfile(
            complexity=TaskComplexity.MICRO if fast else TaskComplexity.STANDARD,
            context_size=ContextSize.NORMAL,
            latency_preference=LatencyClass.FAST if fast else LatencyClass.BALANCED,
            privacy=PrivacyRequirement.PREFER_LOCAL,
            task_type=tt,
        )

    async def _ask(self, prompt: str, task_type: str) -> str:
        resp = await self.federation.execute_task(
            prompt=prompt, profile=self._profile(task_type))
        if resp.error_class is not None or not (resp.content or "").strip():
            raise RuntimeError(f"inférence indispo ({resp.error_class})")
        return resp.content

    async def deliberate(self, goal: str, skeleton: str) -> ADRRecord:
        await self.board.init()
        sid = await self.board.create_session(goal)

        prior = await self.board.find_similar_adr(goal)
        if prior:
            logger.info("[DELIB] ADR pré-existant trouvé, pas de re-délibération.")
            await self.board.close_session(sid, "DEDUPLICATED")
            top = prior[0]
            return ADRRecord(adr_id=top["id"], title=top["title"],
                             decision=top["decision"], rationale="Reprise FTS5.",
                             status="ACCEPTED")

        brief = (
            "Réponds UNIQUEMENT en JSON strict "
            '{"phase": ..., "confidence": 0.0-1.0, "summary": "<=200 car.", '
            '"unified_diff": "@@ ... @@ ou null", "identified_risks": [], "blockers": []}. '
            "Aucun texte hors JSON."
        )
        # Tour 1 — divergence isolée
        proposals = []
        for agent_id in ("coder", "architect"):
            raw = await self._ask(
                f"OBJECTIF : {goal}\nSQUELETTE :\n{skeleton}\n{brief}", "CODING")
            contrib = _extract_contribution(raw, agent_id, "PROPOSAL")
            await self.board.post_contribution(sid, 1, contrib)
            proposals.append(contrib)

        # Tour 2 — critique des diffs
        diffs = "\n---\n".join(
            f"[{p.agent_id}] {p.unified_diff or '(aucun diff)'}" for p in proposals)
        raw_crit = await self._ask(
            f"OBJECTIF : {goal}\nDIFFS :\n{diffs}\n{brief}", "CRITIQUE")
        critique = _extract_contribution(raw_crit, "critic", "CRITIQUE")
        await self.board.post_contribution(sid, 2, critique)

        # Arbitrage — synthèse supervisée
        ctx = prune_deliberation_context([
            {"kind": "brief", "t": goal},
            {"kind": "skeleton", "t": skeleton},
            {"kind": "diff", "t": diffs},
        ])
        raw_sup = await self._ask(
            f"OBJECTIF : {goal}\nCONTEXTE ÉLAGUÉ : {json.dumps(ctx)[:3000]}\n"
            f"CRITIQUE : {critique.summary}\n"
            "Réponds UNIQUEMENT en JSON strict "
            '{"adr_id": "ADR-<n>", "title": "..", "decision": "..", '
            '"rationale": "..", "rejected_alternatives": []}.',
            "CODING")
        m = _JSON_RE.search(raw_sup or "")
        if not m:
            raise ValueError("[supervisor] ADR non-JSON, session avortée.")
        adr = ADRRecord(**json.loads(m.group(0)))
        await self.board.record_adr(adr)
        await self.board.close_session(sid, "CLOSED")
        return adr
