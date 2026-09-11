"""E-ZZIO Capability Router — Google Workspace Provider (Direct Self-Hosted OAuth).

Enforces strictly Read-Only scopes:
- https://www.googleapis.com/auth/gmail.readonly
- https://www.googleapis.com/auth/drive.readonly
- https://www.googleapis.com/auth/calendar.readonly

Zero third-party vendor lock-in. Authenticates via local OAuth refresh token or service credentials.
"""
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision

logger = logging.getLogger("GoogleWorkspaceProvider")


class GoogleWorkspaceProvider:
    READONLY_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root)
        self.policy = CapabilityPolicy()
        self.client_id = self._get_secret("GOOGLE_WORKSPACE_CLIENT_ID")
        self.client_secret = self._get_secret("GOOGLE_WORKSPACE_CLIENT_SECRET")
        self.refresh_token = self._get_secret("GOOGLE_WORKSPACE_REFRESH_TOKEN")

    def _get_secret(self, key: str) -> Optional[str]:
        """Récupère un secret depuis secrets/.env sans jamais l'exposer en clair."""
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

    async def _get_access_token(self) -> Optional[str]:
        """Échange le refresh token direct contre un access token éphémère (sans tiers)."""
        if not self.client_id or not self.client_secret or not self.refresh_token:
            logger.warning("[WORKSPACE-OAUTH] Identifiants OAuth non configurés dans secrets/.env")
            return None

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(token_url, data=payload)
                if r.status_code == 200:
                    return r.json().get("access_token")
                logger.error("[WORKSPACE-OAUTH-FAIL] Échec du renouvellement token : %s", r.text[:120])
        except Exception as exc:
            logger.error("[WORKSPACE-OAUTH-ERR] Erreur de transport OAuth : %s", exc)
        return None

    async def list_recent_emails(self, limit: int = 5) -> Dict[str, Any]:
        """Lit les derniers messages Gmail (scope: gmail.read)."""
        decision, reason = self.policy.evaluate_scope("gmail.read", {"limit": limit})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        access_token = await self._get_access_token()
        if not access_token:
            return {
                "ok": False,
                "scope": "gmail.read",
                "status": "OAUTH_CREDENTIALS_REQUIRED",
                "message": "Client OAuth Google Workspace non configuré. Renseignez GOOGLE_WORKSPACE_CLIENT_ID / REFRESH_TOKEN dans secrets/.env pour connecter votre boîte réelle.",
                "data": []
            }

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={limit}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    return {"ok": True, "scope": "gmail.read", "data": r.json().get("messages", [])}
                return {"ok": False, "status_code": r.status_code, "error": r.text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def list_recent_files(self, limit: int = 5) -> Dict[str, Any]:
        """Liste les fichiers récents Google Drive (scope: drive.read)."""
        decision, reason = self.policy.evaluate_scope("drive.read", {"limit": limit})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        access_token = await self._get_access_token()
        if not access_token:
            return {
                "ok": False,
                "scope": "drive.read",
                "status": "OAUTH_CREDENTIALS_REQUIRED",
                "message": "Client OAuth Google Workspace non configuré pour Drive.",
                "data": []
            }

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://www.googleapis.com/drive/v3/files?pageSize={limit}&fields=files(id,name,mimeType,modifiedTime)"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    return {"ok": True, "scope": "drive.read", "data": r.json().get("files", [])}
                return {"ok": False, "status_code": r.status_code, "error": r.text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def list_upcoming_events(self, limit: int = 5) -> Dict[str, Any]:
        """Liste les prochains événements Google Calendar (scope: calendar.read)."""
        decision, reason = self.policy.evaluate_scope("calendar.read", {"limit": limit})
        if decision != PolicyDecision.ALLOW:
            return {"ok": False, "error": reason}

        access_token = await self._get_access_token()
        if not access_token:
            return {
                "ok": False,
                "scope": "calendar.read",
                "status": "OAUTH_CREDENTIALS_REQUIRED",
                "message": "Client OAuth Google Workspace non configuré pour Calendar.",
                "data": []
            }

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults={limit}&singleEvents=true&orderBy=startTime"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    return {"ok": True, "scope": "calendar.read", "data": r.json().get("items", [])}
                return {"ok": False, "status_code": r.status_code, "error": r.text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
