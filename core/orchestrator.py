"""core/orchestrator.py - Cœur d'orchestration multi-agents et contrôle d'exécution."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from core.bus import AgentEvent, EventBus
from core.cognitive_router import ModelRouter
from core.sandbox import SecuritySandbox


class Orchestrator:
    def __init__(
        self,
        bus: EventBus,
        router: ModelRouter,
        sandbox: Optional[SecuritySandbox] = None,
    ) -> None:
        self.bus = bus
        self.router = router
        self.sandbox = sandbox or SecuritySandbox()

    async def run(
        self,
        run_id: str,
        prompt: str,
        profile: str = "normal",
        is_approved: bool = False,
    ) -> Dict[str, Any]:
        try:
            routes = self.router.resolve_route(profile)
            plan_steps = [
                f"1. Routage vers {routes['primary']['provider']}:{routes['primary']['model']}",
                "2. Analyse cognitive et détection d'outils",
                "3. Exécution sécurisée sous contrôle sandbox",
                "4. Consolidation du résultat final",
            ]

            await self.bus.emit(
                AgentEvent(
                    run_id=run_id,
                    event_type="plan",
                    agent_id="Orchestrateur",
                    payload={"steps": plan_steps, "profile": profile},
                )
            )

            cognitive_res = await self.router.complete(profile=profile, prompt=prompt)

            await self.bus.emit(
                AgentEvent(
                    run_id=run_id,
                    event_type="thought",
                    agent_id="Cognition",
                    payload={
                        "provider": cognitive_res["provider_used"],
                        "model": cognitive_res["model_used"],
                        "fallback_triggered": cognitive_res.get("fallback_triggered", False),
                    },
                )
            )

            execution_details: Optional[Dict[str, Any]] = None
            clean_prompt = prompt.strip()
            if clean_prompt.startswith("exec:") or clean_prompt.startswith("run:"):
                cmd = clean_prompt.split(":", 1)[1].strip()
                risk, needs_approval = self.sandbox.assess_risk(cmd)

                await self.bus.emit(
                    AgentEvent(
                        run_id=run_id,
                        event_type="tool_call",
                        agent_id="SandboxTerminal",
                        payload={"command": cmd, "risk": risk},
                        requires_approval=needs_approval,
                    )
                )

                exec_res = await self.sandbox.execute(cmd, is_approved=is_approved)
                execution_details = {
                    "command": exec_res.command,
                    "exit_code": exec_res.exit_code,
                    "stdout": exec_res.stdout,
                    "stderr": exec_res.stderr,
                    "approved": exec_res.approved,
                }

                await self.bus.emit(
                    AgentEvent(
                        run_id=run_id,
                        event_type="terminal",
                        agent_id="SandboxTerminal",
                        payload=execution_details,
                    )
                )

            final_payload = {
                "text": cognitive_res["text"],
                "provider": cognitive_res["provider_used"],
                "model": cognitive_res["model_used"],
                "execution": execution_details,
                "status": "completed",
            }

            await self.bus.emit(
                AgentEvent(
                    run_id=run_id,
                    event_type="final",
                    agent_id="Orchestrateur",
                    payload=final_payload,
                )
            )

            return final_payload

        except Exception as exc:
            error_payload = {"error": str(exc), "status": "failed"}
            await self.bus.emit(
                AgentEvent(
                    run_id=run_id,
                    event_type="final",
                    agent_id="Orchestrateur",
                    payload=error_payload,
                )
            )
            return error_payload


# Canonical unification : ré-export des composants DAG V9.2
from core.orchestration import (
    TaskDAG,
    DAGNode,
    DAGExecutionStatus,
    CycleDetectedError,
    DependencyNotMetError,
    DAGOrchestrator,
)

__all__ = [
    "Orchestrator",
    "TaskDAG",
    "DAGNode",
    "DAGExecutionStatus",
    "CycleDetectedError",
    "DependencyNotMetError",
    "DAGOrchestrator",
]

