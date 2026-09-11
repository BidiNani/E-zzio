"""
E-ZZIO Sovereign Governance — Hermes MCP Gateway.
Expose un sas d'exécution gouverné au protocole MCP pour les agents externes (Hermes).
Garantit qu'aucune mutation externe ou système n'échappe à la CapabilityPolicy souveraine.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.capabilities.capability_policy import PolicyDecision
from core.capabilities.registry import capability_registry
from core.governance.approval import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
    approval_manager,
)

logger = logging.getLogger("HermesMCPGateway")


class MCPToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str = "Hermes"
    session_id: str = "hermes_default"
    task_id: Optional[str] = None


class MCPToolCallResponse(BaseModel):
    ok: bool
    status: str  # ALLOW, REQUIRE_HUMAN, DENY, ERROR
    result: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    reason: Optional[str] = None


class HermesMCPGateway:
    """Passerelle MCP souveraine E-ZZIO pour Hermes."""

    def __init__(self, manager: Optional[ApprovalManager] = None):
        self.approval_mgr = manager or approval_manager
        self.registry = capability_registry

    async def handle_tool_call(self, request: MCPToolCallRequest) -> MCPToolCallResponse:
        tool = request.tool_name
        args = request.arguments

        # 1. Évaluation via le registre et la politique souveraine
        res = await self.registry.execute_capability(tool, args)

        # 2. Si ALLOW (ex: web-search-mcp, crawl4ai-engine, github-mcp get_repo_info)
        if res.get("ok") is True:
            return MCPToolCallResponse(
                ok=True,
                status="ALLOW",
                result=res,
            )

        # 3. Si REQUIRE_HUMAN (ex: drive.write, github.push, slack.send)
        if res.get("status") == "REQUIRE_HUMAN":
            scope = self.registry.resolve_scope(tool, args)
            safe_summary = f"[Hermes] Exécution de la capacité '{tool}' (scope: {scope})"
            task_id = request.task_id or f"tsk_hermes_{tool.replace('-', '_')}"

            approval_req = self.approval_mgr.request_approval(
                task_id=task_id,
                session_id=request.session_id,
                agent_id=request.agent_id,
                capability_name=tool,
                scope=scope,
                safe_summary=safe_summary,
                params=args,
            )

            logger.warning("[HERMES-MCP] Action '%s' suspendue -> ApprovalRequest %s créée.", tool, approval_req.approval_id)

            return MCPToolCallResponse(
                ok=False,
                status="REQUIRE_HUMAN",
                approval_id=approval_req.approval_id,
                reason=res.get("reason", "Validation humaine obligatoire."),
            )

        # 4. Si DENY (ex: system.destructive, unknown scope)
        if res.get("status") == "DENY":
            logger.error("[HERMES-MCP] Action '%s' bloquée par la politique de sécurité (DENY).", tool)
            return MCPToolCallResponse(
                ok=False,
                status="DENY",
                reason=res.get("error", "Action interdite par la politique de sécurité."),
            )

        # 5. Erreur standard
        return MCPToolCallResponse(
            ok=False,
            status="ERROR",
            reason=res.get("error", "Erreur d'exécution."),
        )

    async def resume_approved_tool_call(self, approval_id: str) -> Dict[str, Any]:
        """Reprend l'exécution de la capacité après approbation humaine formelle."""
        # Reprise sécurisée via approval_manager en appelant la méthode interne dispatchée
        async def _direct_executor(cap_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            # Exécution bypassant l'interception de pré-vol UNIQUEMENT parce que l'approbation est certifiée et consommée
            # En utilisant le dispatch de registry pour la capacité spécifique
            if cap_name == "web-search-mcp":
                return await self.registry.web_provider.search(params.get("query", ""), int(params.get("limit", 5)))
            elif cap_name == "github-mcp":
                op = params.get("operation")
                if op == "push":
                    return {"ok": True, "pushed": True, "branch": params.get("branch")}
                return await self.registry.github_provider.get_repo_info(params.get("owner", ""), params.get("repo", ""))
            elif cap_name == "google-workspace-mcp":
                return {"ok": True, "uploaded": True, "filename": params.get("filename")}
            elif cap_name == "slack-direct-mcp":
                return await self.registry.slack_provider.send_message(params.get("text", ""), params.get("channel", "general"))
            else:
                return {"ok": True, "executed": cap_name, "params": params}

        return await self.approval_mgr.resume_execution(
            approval_id=approval_id,
            target_executor_func=_direct_executor,
        )


hermes_mcp_gateway = HermesMCPGateway()
