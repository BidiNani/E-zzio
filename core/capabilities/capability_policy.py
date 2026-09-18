"""E-ZZIO Capability Router — Sovereign Capability Policy Guard.

Enforces granular access control per scope:
- ALLOW: Read-only operations (gmail.read, drive.read, calendar.read, github.read, web.search)
- REQUIRE_HUMAN: Write/mutating operations (gmail.send, drive.write, github.push, calendar.write)
- DENY: Unauthorized or dangerous actions
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("CapabilityPolicy")


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"
    DENY = "DENY"


class CapabilityPolicy:
    # Définition stricte des politiques par scope
    SCOPE_POLICIES = {
        # Google Workspace Read-Only (Souverain & Direct)
        "gmail.read": PolicyDecision.ALLOW,
        "drive.read": PolicyDecision.ALLOW,
        "calendar.read": PolicyDecision.ALLOW,

        # Google Workspace Mutating (Requiert validation humaine explicite)
        "gmail.send": PolicyDecision.REQUIRE_HUMAN,
        "gmail.delete": PolicyDecision.REQUIRE_HUMAN,
        "drive.write": PolicyDecision.REQUIRE_HUMAN,
        "drive.delete": PolicyDecision.REQUIRE_HUMAN,
        "calendar.write": PolicyDecision.REQUIRE_HUMAN,
        "calendar.delete": PolicyDecision.REQUIRE_HUMAN,

        # GitHub
        "github.read": PolicyDecision.ALLOW,
        "github.write": PolicyDecision.REQUIRE_HUMAN,
        "github.push": PolicyDecision.REQUIRE_HUMAN,
        "github.pr_create": PolicyDecision.REQUIRE_HUMAN,

        # Web & Recherche
        "web.search": PolicyDecision.ALLOW,
        "web.crawl": PolicyDecision.ALLOW,
        "browser.automate": PolicyDecision.REQUIRE_HUMAN,

        # Code & Système local
        "code.read": PolicyDecision.ALLOW,
        "code.patch": PolicyDecision.ALLOW,
        "code.test": PolicyDecision.ALLOW,
        "system.destructive": PolicyDecision.DENY,

        # Direct Self-Hosted Slack
        "slack.read": PolicyDecision.ALLOW,
        "slack.send": PolicyDecision.REQUIRE_HUMAN,

        # Composio SaaS Ecosystem (Legacy Fallback)
        "composio.read": PolicyDecision.ALLOW,
        "composio.execute_read": PolicyDecision.ALLOW,
        "composio.execute_write": PolicyDecision.REQUIRE_HUMAN,

        # Multimodal Cloud Generation & Perception
        "image.generate_ai": PolicyDecision.ALLOW,
        "video.generate_cloud": PolicyDecision.REQUIRE_HUMAN,
        "audio.transcribe_cloud": PolicyDecision.ALLOW,

        # YouTube Multimodal Perception (yt-dlp)
        "youtube.inspect": PolicyDecision.ALLOW,
        "youtube.download": PolicyDecision.REQUIRE_HUMAN,
    }

    def evaluate_scope(self, scope: str, metadata: dict[str, Any] | None = None) -> tuple[PolicyDecision, str]:
        """Évalue si un scope d'action est autorisé, nécessite une confirmation humaine ou est rejeté."""
        meta = metadata or {}
        decision = self.SCOPE_POLICIES.get(scope, PolicyDecision.DENY)

        if decision == PolicyDecision.ALLOW:
            return PolicyDecision.ALLOW, f"[POLICY OK] Scope lecture/exécution autorisé : {scope}"

        elif decision == PolicyDecision.REQUIRE_HUMAN:
            target = meta.get("target", "action mutante")
            logger.warning("[CAPABILITY-POLICY] Escalade REQUIRE_HUMAN pour le scope %s sur %s", scope, target)
            return PolicyDecision.REQUIRE_HUMAN, f"[REQUIRE_HUMAN] L'opération d'écriture/modification '{scope}' requiert une validation humaine."

        else:
            logger.error("[CAPABILITY-POLICY] Scope non autorisé ou interdit : %s", scope)
            return PolicyDecision.DENY, f"[POLICY DENY] Scope non autorisé par la politique souveraine : {scope}"
