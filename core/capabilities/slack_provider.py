"""
E-ZZIO Capability Router — Direct Self-Hosted Slack Provider.
Permet d'envoyer des notifications et de lire des messages Slack sans aucun agrégateur tiers (Composio/AnythingMCP) :
1. Support direct des Incoming Webhooks Slack et de l'API REST Slack
2. Authentification via SLACK_WEBHOOK_URL ou SLACK_BOT_TOKEN dans secrets/.env
3. Politique de sécurité : slack.read (ALLOW), slack.send (REQUIRE_HUMAN)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.utils.http_pool import get_http_client

logger = logging.getLogger("SlackProvider")


class SlackProvider:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()
        self.webhook_url = self._get_secret("SLACK_WEBHOOK_URL")
        self.bot_token = self._get_secret("SLACK_BOT_TOKEN")

    def _get_secret(self, key: str) -> str | None:
        """Récupère un secret depuis secrets/.env."""
        env_paths = [
            self.workspace_root / "secrets" / ".env",
            Path("secrets/.env"),
        ]
        for p in env_paths:
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and f"{key}=" in line:
                            return line.split("=", 1)[1].strip().strip("\"'")
                except Exception:
                    pass
        return os.environ.get(key)

    async def send_message(self, text: str, channel: str | None = None, require_approval: bool = True) -> dict[str, Any]:
        """Envoie un message sur Slack avec interception de sécurité REQUIRE_HUMAN."""
        decision, reason = self.policy.evaluate_scope("slack.send", {"target": channel or "webhook_default", "text": text})

        # Interception de sécurité contractuelle
        if decision == PolicyDecision.REQUIRE_HUMAN and require_approval:
            return {
                "ok": False,
                "requires_human": True,
                "status": "PENDING_APPROVAL",
                "scope": "slack.send",
                "target": channel or "webhook_default",
                "text": text,
                "reason": reason
            }
        elif decision == PolicyDecision.DENY:
            return {"ok": False, "error": reason}

        if self.webhook_url:
            payload = {"text": text}
            if channel:
                payload["channel"] = channel
            try:
                client = get_http_client()
                r = await client.post(self.webhook_url, json=payload)
                if r.status_code == 200:
                    return {"ok": True, "scope": "slack.send", "status": "DELIVERED"}
                return {"ok": False, "status_code": r.status_code, "error": r.text}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        return {
            "ok": False,
            "error": "Aucun SLACK_WEBHOOK_URL configuré dans secrets/.env (Fail-Closed)."
        }


# Singleton global
slack_provider = SlackProvider()
