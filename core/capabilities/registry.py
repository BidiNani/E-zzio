"""
E-ZZIO Core — Capability Registry & Qualification Authority.
Gère l'enregistrement, la validation et l'exécution sécurisée des capacités externes qualifiées.
"""
from __future__ import annotations

import logging
from typing import Any

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.capabilities.capability_qualification import CapabilityQualification, QualificationStatus
from core.capabilities.composio_provider import ComposioProvider
from core.capabilities.github_provider import GitHubProvider
from core.capabilities.google_workspace_provider import GoogleWorkspaceProvider
from core.capabilities.slack_provider import SlackProvider
from core.capabilities.web_provider import WebProvider
from core.perception.youtube_adapter import YouTubeAdapter

logger = logging.getLogger("CapabilityRegistry")


class CapabilityRegistry:
    """Registre souverain des capacités qualifiées d'E-ZZIO."""

    def __init__(self):
        self.qualifications: dict[str, CapabilityQualification] = {}
        self.policy = CapabilityPolicy()
        self.web_provider = WebProvider()
        self.github_provider = GitHubProvider()
        self.google_provider = GoogleWorkspaceProvider()
        self.slack_provider = SlackProvider()
        self.composio_provider = ComposioProvider()
        self.youtube_adapter = YouTubeAdapter()
        self._register_canonical_capabilities()

    def _register_canonical_capabilities(self):
        """Enregistre et qualifie formellement les capacités de base."""
        # 1. web-search-mcp
        self.register(
            CapabilityQualification(
                name="web-search-mcp",
                category="web",
                provider="web_provider.WebProvider.search",
                input_contract={"query": "str", "limit": "int"},
                output_contract={"results": "list[dict]"},
                permissions=["read_web"],
                network_access=True,
                ssrf_protection=True,
                timeout_seconds=10.0,
                max_payload_mb=5.0,
                fail_closed=True,
                fallback_behavior="GRACEFUL_DEGRADE",
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_capability_policy.py", "tests/test_capability_registry_and_qualifications.py"]
            )
        )

        # 2. crawl4ai-engine
        self.register(
            CapabilityQualification(
                name="crawl4ai-engine",
                category="web",
                provider="web_provider.WebProvider.crawl",
                input_contract={"target_url": "str", "max_chars": "int"},
                output_contract={"content": "str", "length": "int"},
                permissions=["crawl_web"],
                network_access=True,
                ssrf_protection=True,
                timeout_seconds=15.0,
                max_payload_mb=10.0,
                fail_closed=True,
                fallback_behavior="GRACEFUL_DEGRADE",
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_capability_policy.py", "tests/test_capability_registry_and_qualifications.py"]
            )
        )

        # 3. github-mcp
        self.register(
            CapabilityQualification(
                name="github-mcp",
                category="saas",
                provider="github_provider.GithubProvider",
                input_contract={"operation": "str", "params": "dict"},
                output_contract={"data": "dict"},
                permissions=["read_repo", "write_issue"],
                network_access=True,
                secrets_required=["GITHUB_TOKEN"],
                ssrf_protection=True,
                timeout_seconds=15.0,
                fail_closed=True,
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_phase6_saas_and_tools.py"]
            )
        )

        # 4. composio-tools
        self.register(
            CapabilityQualification(
                name="composio-tools",
                category="saas",
                provider="composio_provider.ComposioProvider",
                input_contract={"action": "str", "params": "dict", "is_write": "bool"},
                output_contract={"data": "dict"},
                permissions=["read_saas", "write_saas"],
                network_access=True,
                secrets_required=["COMPOSIO_API_KEY"],
                ssrf_protection=True,
                timeout_seconds=15.0,
                fail_closed=True,
                fallback_behavior="GRACEFUL_DEGRADE",
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_composio_qualification.py"]
            )
        )

        # 5. google-workspace-mcp
        self.register(
            CapabilityQualification(
                name="google-workspace-mcp",
                category="saas",
                provider="google_workspace_provider.GoogleWorkspaceProvider",
                input_contract={"service": "str", "operation": "str", "params": "dict"},
                output_contract={"data": "dict"},
                permissions=["gmail.readonly", "drive.readonly", "calendar.readonly"],
                network_access=True,
                secrets_required=["GOOGLE_WORKSPACE_CLIENT_ID", "GOOGLE_WORKSPACE_CLIENT_SECRET", "GOOGLE_WORKSPACE_REFRESH_TOKEN"],
                ssrf_protection=True,
                timeout_seconds=15.0,
                fail_closed=True,
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_phase6_saas_and_tools.py"]
            )
        )

        # 6. slack-direct-mcp
        self.register(
            CapabilityQualification(
                name="slack-direct-mcp",
                category="saas",
                provider="slack_provider.SlackProvider",
                input_contract={"text": "str", "channel": "str"},
                output_contract={"status": "str"},
                permissions=["slack.read", "slack.send"],
                network_access=True,
                secrets_required=["SLACK_WEBHOOK_URL"],
                ssrf_protection=True,
                timeout_seconds=10.0,
                fail_closed=True,
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_priority_4_qualified_capabilities.py"]
            )
        )

        # 7. youtube-adapter
        self.register(
            CapabilityQualification(
                name="youtube-adapter",
                category="multimodal_perception",
                provider="youtube_adapter.YouTubeAdapter",
                input_contract={"url": "str", "extract_subtitles": "bool"},
                output_contract={"data": "dict", "provenance_tag": "str"},
                permissions=["youtube.inspect", "youtube.download"],
                network_access=True,
                ssrf_protection=True,
                timeout_seconds=25.0,
                fail_closed=True,
                status=QualificationStatus.QUALIFIED,
                tests_reference=["tests/test_youtube_perception_qualification.py"]
            )
        )

        # 8. glm-5.3-candidate
        self.register(
            CapabilityQualification(
                name="glm-5.3-candidate",
                category="llm",
                provider="agent_provider.AgentProviderAdapter",
                input_contract={"messages": "list[dict]", "temperature": "float"},
                output_contract={"text": "str"},
                permissions=["infer_cloud"],
                network_access=True,
                secrets_required=["GLM_API_KEY"],
                ssrf_protection=True,
                timeout_seconds=20.0,
                fail_closed=True,
                fallback_behavior="GRACEFUL_DEGRADE",
                status=QualificationStatus.CANDIDATE,
                tests_reference=["tests/test_capability_registry_and_qualifications.py"]
            )
        )

        # 9. opencode-candidate
        self.register(
            CapabilityQualification(
                name="opencode-candidate",
                category="coding_worker",
                provider="opencode.OpenCodeWorker",
                input_contract={"repo_path": "str", "task": "str", "model": "str"},
                output_contract={"diff": "str", "exit_code": "int"},
                permissions=["code.read", "code.patch", "code.test"],
                network_access=False,
                ssrf_protection=True,
                timeout_seconds=60.0,
                fail_closed=True,
                status=QualificationStatus.CANDIDATE,
                tests_reference=["tests/test_opentelemetry_and_docling_pipeline.py"]
            )
        )

    def register(self, qualification: CapabilityQualification) -> None:
        """Enregistre une nouvelle fiche de qualification dans le registre."""
        self.qualifications[qualification.name] = qualification
        logger.info("[CAPABILITY-REGISTER] Capacité '%s' enregistrée avec le statut %s", qualification.name, qualification.status.value)

    def get_qualification(self, name: str) -> CapabilityQualification | None:
        return self.qualifications.get(name)

    def get_capability(self, name: str) -> CapabilityQualification | None:
        return self.qualifications.get(name)

    def list_qualified_capabilities(self) -> list[str]:
        return [name for name, q in self.qualifications.items() if q.status == QualificationStatus.QUALIFIED]

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "name": q.name,
                "category": q.category,
                "status": q.status.value,
                "provider": q.provider,
                "permissions": q.permissions,
                "fail_closed": q.fail_closed
            }
            for q in self.qualifications.values()
        ]

    def resolve_scope(self, name: str, params: dict[str, Any]) -> str:
        """Résout le scope d'autorisation pour une capacité et ses paramètres donnés."""
        if "scope" in params and isinstance(params["scope"], str):
            return params["scope"]

        if name == "web-search-mcp":
            return "web.search"

        elif name == "crawl4ai-engine":
            return "web.crawl"

        elif name == "github-mcp":
            op = str(params.get("operation", "get_repo_info")).lower()
            if op in ("get_repo_info", "list_issues", "read"):
                return "github.read"
            elif op in ("push", "git_push"):
                return "github.push"
            elif op in ("create_pr", "pr_create"):
                return "github.pr_create"
            return "github.write"

        elif name == "google-workspace-mcp":
            srv = str(params.get("service", "gmail")).lower()
            op = str(params.get("operation", "search_emails")).lower()
            if srv == "gmail":
                if op in ("search_emails", "read", "get"):
                    return "gmail.read"
                elif op in ("delete", "remove"):
                    return "gmail.delete"
                return "gmail.send"
            elif srv == "drive":
                if op in ("list_files", "read", "get"):
                    return "drive.read"
                elif op in ("delete", "remove"):
                    return "drive.delete"
                return "drive.write"
            elif srv == "calendar":
                if op in ("read", "list"):
                    return "calendar.read"
                elif op in ("delete", "remove"):
                    return "calendar.delete"
                return "calendar.write"
            return f"{srv}.{op}"

        elif name == "slack-direct-mcp":
            op = str(params.get("operation", "send")).lower()
            if op in ("read", "history", "list"):
                return "slack.read"
            return "slack.send"

        elif name == "youtube-adapter":
            op = str(params.get("operation", "inspect")).lower()
            if op == "download_audio":
                return "youtube.download"
            return "youtube.inspect"

        elif name == "composio-tools":
            action = str(params.get("action", "")).lower()
            if action == "list_apps" or not action:
                return "composio.read"
            if bool(params.get("is_write", False)):
                return "composio.execute_write"
            return "composio.execute_read"

        return f"unknown.{name}"

    async def execute_capability(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Exécute une capacité sous contrôle de sécurité strict et de politique de gouvernance."""
        qualif = self.get_qualification(name)
        if not qualif:
            return {"ok": False, "error": f"Capacité '{name}' non enregistrée dans le CapabilityRegistry (Fail-Closed)."}

        if qualif.status != QualificationStatus.QUALIFIED:
            return {"ok": False, "error": f"Capacité '{name}' en statut {qualif.status.value} : exécution interdite."}

        # Pré-vol de gouvernance et arbitrage de sécurité
        scope = self.resolve_scope(name, params)
        decision, reason = self.policy.evaluate_scope(scope, params)
        if decision == PolicyDecision.DENY:
            logger.warning("[CAPABILITY-INTERCEPT-DENY] '%s' (scope=%s) bloqué : %s", name, scope, reason)
            return {"ok": False, "status": "DENY", "error": reason}

        if decision == PolicyDecision.REQUIRE_HUMAN:
            logger.warning("[CAPABILITY-INTERCEPT-REQUIRE_HUMAN] '%s' (scope=%s) requiert validation humaine : %s", name, scope, reason)
            return {"ok": False, "status": "REQUIRE_HUMAN", "reason": reason}

        # Dispatch d'exécution sécurisé (ALLOW)
        try:
            if name == "web-search-mcp":
                query = params.get("query", "")
                limit = int(params.get("limit", 5))
                return await self.web_provider.search(query=query, limit=limit)

            elif name == "crawl4ai-engine":
                target_url = params.get("url") or params.get("target_url", "")
                max_chars = int(params.get("max_chars", 4000))
                return await self.web_provider.crawl(target_url=target_url, max_chars=max_chars)

            elif name == "github-mcp":
                operation = params.get("operation", "get_repo_info")
                owner = params.get("owner", "")
                repo = params.get("repo", "")
                if operation == "get_repo_info":
                    return await self.github_provider.get_repo_info(owner=owner, repo=repo)
                elif operation == "list_issues":
                    return await self.github_provider.list_issues(owner=owner, repo=repo)
                return {"ok": False, "error": f"Opération GitHub '{operation}' non supportée."}

            elif name == "google-workspace-mcp":
                service = params.get("service", "gmail")
                operation = params.get("operation", "search_emails")
                if service == "gmail" and operation == "search_emails":
                    return await self.google_provider.search_emails(query=params.get("query", ""))
                elif service == "drive" and operation == "list_files":
                    return await self.google_provider.list_drive_files(query=params.get("query", ""))
                return {"ok": False, "error": f"Opération Workspace '{service}.{operation}' non supportée."}

            elif name == "slack-direct-mcp":
                text = params.get("text", "")
                channel = params.get("channel")
                require_approval = bool(params.get("require_approval", True))
                return await self.slack_provider.send_message(text=text, channel=channel, require_approval=require_approval)

            elif name == "youtube-adapter":
                url = params.get("url", "")
                extract_subtitles = bool(params.get("extract_subtitles", True))
                operation = params.get("operation", "inspect")
                if operation == "inspect":
                    return await self.youtube_adapter.inspect_video(video_url=url, extract_subtitles=extract_subtitles)
                elif operation == "download_audio":
                    require_approval = bool(params.get("require_approval", True))
                    audio_format = params.get("format", "mp3")
                    return await self.youtube_adapter.download_audio(video_url=url, audio_format=audio_format, require_approval=require_approval)
                return {"ok": False, "error": f"Opération YouTube '{operation}' non reconnue."}

            elif name == "composio-tools":
                action = params.get("action")
                if action == "list_apps" or not action:
                    return await self.composio_provider.list_available_apps()
                is_write = bool(params.get("is_write", False))
                action_params = params.get("params", {})
                return await self.composio_provider.execute_action(action_name=action, params=action_params, is_write=is_write)

            return {"ok": False, "error": f"Dispatcher non implémenté pour '{name}'."}

        except Exception as exc:
            logger.error("[CAPABILITY-EXEC-FAIL] Échec d'exécution de '%s' : %s", name, exc)
            return {"ok": False, "error": str(exc)}


# Singleton partagé du registre de capacités
capability_registry = CapabilityRegistry()
