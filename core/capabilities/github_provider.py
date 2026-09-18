"""E-ZZIO Capability Router — GitHub Provider (Self-Hosted Direct REST / MCP Adapter).

Enforces strictly Read-Only scopes by default:
- github.read: Repository metadata, issues, PRs, file contents (ALLOW)
- github.write: Comments, issue updates (REQUIRE_HUMAN)
- github.pr_create / github.push: Commits, branch creation, PRs (REQUIRE_HUMAN)

Authenticates directly via local GITHUB_TOKEN in secrets/.env (zero third-party aggregator).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision
from core.utils.http_pool import get_http_client

logger = logging.getLogger("GitHubProvider")


class GitHubProvider:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()
        self.github_token = self._get_secret("GITHUB_TOKEN") or self._get_secret("GH_TOKEN")
        self.api_base = "https://api.github.com"

    def _get_secret(self, key: str) -> str | None:
        """Récupère le jeton GitHub depuis secrets/.env sans l'exposer."""
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

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "E-ZzIO-Autonomous-Agent/2.0",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    async def get_repo_info(self, owner: str, repo: str) -> dict[str, Any]:
        """Lit les informations d'un dépôt GitHub (scope: github.read)."""
        decision, reason = self.policy.evaluate_scope("github.read", {"owner": owner, "repo": repo})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        url = f"{self.api_base}/repos/{owner}/{repo}"
        try:
            client = get_http_client()
            r = await client.get(url, headers=self._get_headers())
            if r.status_code == 200:
                data = r.json()
                return {
                    "ok": True,
                    "scope": "github.read",
                    "data": {
                        "name": data.get("full_name"),
                        "description": data.get("description"),
                        "stars": data.get("stargazers_count"),
                        "default_branch": data.get("default_branch"),
                        "open_issues": data.get("open_issues_count"),
                    }
                }
            return {"ok": False, "status_code": r.status_code, "error": r.text[:120]}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def list_issues(self, owner: str, repo: str, state: str = "open", limit: int = 5) -> dict[str, Any]:
        """Liste les issues d'un dépôt GitHub (scope: github.read)."""
        decision, reason = self.policy.evaluate_scope("github.read", {"owner": owner, "repo": repo})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        url = f"{self.api_base}/repos/{owner}/{repo}/issues?state={state}&per_page={limit}"
        try:
            client = get_http_client()
            r = await client.get(url, headers=self._get_headers())
            if r.status_code == 200:
                items = r.json()
                formatted = [
                    {
                        "number": it.get("number"),
                        "title": it.get("title"),
                        "user": it.get("user", {}).get("login"),
                        "state": it.get("state"),
                        "comments": it.get("comments"),
                    }
                    for it in items
                ]
                return {"ok": True, "scope": "github.read", "data": formatted}
            return {"ok": False, "status_code": r.status_code, "error": r.text[:120]}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open", limit: int = 5) -> dict[str, Any]:
        """Liste les Pull Requests d'un dépôt (scope: github.read)."""
        decision, reason = self.policy.evaluate_scope("github.read", {"owner": owner, "repo": repo})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        url = f"{self.api_base}/repos/{owner}/{repo}/pulls?state={state}&per_page={limit}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=self._get_headers())
                if r.status_code == 200:
                    items = r.json()
                    formatted = [
                        {
                            "number": it.get("number"),
                            "title": it.get("title"),
                            "user": it.get("user", {}).get("login"),
                            "head": it.get("head", {}).get("ref"),
                            "base": it.get("base", {}).get("ref"),
                        }
                        for it in items
                    ]
                    return {"ok": True, "scope": "github.read", "data": formatted}
                return {"ok": False, "status_code": r.status_code, "error": r.text[:120]}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def create_pull_request(self, owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> dict[str, Any]:
        """Création d'une PR protégée par REQUIRE_HUMAN (scope: github.pr_create)."""
        decision, reason = self.policy.evaluate_scope("github.pr_create", {"owner": owner, "repo": repo, "title": title})
        if decision != PolicyDecision.ALLOW:
            logger.warning("[GITHUB-POLICY-GUARD] Tentative de création de PR interceptée : %s", reason)
            return {
                "ok": False,
                "scope": "github.pr_create",
                "status": "REQUIRE_HUMAN",
                "message": reason,
                "draft_pr": {
                    "owner": owner,
                    "repo": repo,
                    "title": title,
                    "head": head,
                    "base": base,
                    "body": body
                }
            }

        return {"ok": False, "error": "Exécution bloquée en mode sécurisé."}
