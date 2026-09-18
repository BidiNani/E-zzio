"""
E-ZZIO Capability Router — Composio Toolset & SaaS Provider.
Gère les intégrations d'outils SaaS (Notion, Slack, Linear, Gmail, Calendars...) via l'API Composio ou Toolsets locaux.

Politique de sécurité (CapabilityPolicy) :
- composio.list_apps / composio.read : Consultation des outils et métadonnées (ALLOW)
- composio.execute_read : Exécution d'actions de lecture seule (ALLOW)
- composio.execute_write : Actions d'écriture / modification (REQUIRE_HUMAN)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision

logger = logging.getLogger("ComposioProvider")


class ComposioProvider:
    """Fournisseur d'accès aux outils SaaS via l'écosystème Composio."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()
        self.api_key = self._get_secret("COMPOSIO_API_KEY")
        self.api_base = "https://backend.composio.dev/api/v1"

    def _get_secret(self, key: str) -> str | None:
        """Récupère la clé Composio depuis secrets/.env ou variables d'environnement."""
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

    def is_configured(self) -> bool:
        """Indique si la clé d'API Composio est présente."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "E-ZzIO-Autonomous-Core/2.0",
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    async def list_available_apps(self) -> dict[str, Any]:
        """Liste les intégrations SaaS disponibles (scope: composio.read)."""
        decision, reason = self.policy.evaluate_scope("composio.read", {})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        if not self.is_configured():
            # Mode Fail-Closed avec retour informatif
            return {
                "ok": True,
                "configured": False,
                "status": "UNCONFIGURED_FAIL_CLOSED",
                "message": "COMPOSIO_API_KEY absente. Dégradation contrôlée.",
                "supported_apps": ["github", "linear", "slack", "notion", "gmail", "trello", "jira"]
            }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{self.api_base}/apps", headers=self._get_headers())
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "ok": True,
                        "configured": True,
                        "apps": data.get("items", data) if isinstance(data, dict) else data
                    }
                return {"ok": False, "status_code": r.status_code, "error": r.text}
        except Exception as exc:
            logger.warning("[COMPOSIO-FAIL] Erreur de communication API : %s", exc)
            return {"ok": False, "error": str(exc)}

    async def execute_action(
        self,
        action_name: str,
        params: dict[str, Any],
        is_write: bool = False
    ) -> dict[str, Any]:
        """
        Exécute une action SaaS sous contrôle strict des scopes de gouvernance.
        Les actions d'écriture nécessitent validation humaine explicite.
        """
        scope = "composio.execute_write" if is_write else "composio.execute_read"
        decision, reason = self.policy.evaluate_scope(scope, {"action": action_name, "params": params})

        if decision == PolicyDecision.REQUIRE_HUMAN:
            return {
                "ok": False,
                "requires_human": True,
                "status": "PENDING_APPROVAL",
                "scope": scope,
                "action": action_name,
                "reason": f"Action d'écriture '{action_name}' requiert approbation humaine explicite."
            }

        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        if not self.is_configured():
            return {
                "ok": False,
                "error": "COMPOSIO_API_KEY absente dans secrets/.env (Fail-Closed)."
            }

        try:
            payload = {
                "actionName": action_name,
                "input": params
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.api_base}/actions/execute",
                    headers=self._get_headers(),
                    json=payload
                )
                if r.status_code == 200:
                    return {"ok": True, "action": action_name, "data": r.json()}
                return {"ok": False, "status_code": r.status_code, "error": r.text}
        except Exception as exc:
            logger.error("[COMPOSIO-ACTION-FAIL] Échec d'exécution %s : %s", action_name, exc)
            return {"ok": False, "error": str(exc)}
