"""
core/agent/web_access_manager.py — Universal Web Access & URL Manager for E-ZZIO Agents.
Features: SSRF Protection, Access Mode Classification, HTML/JSON Extraction, Audit Provenance & Prompt Injection Isolation.
"""
from __future__ import annotations
import os
import re
import sys
import json
import logging
from enum import Enum
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from core.agent.input_access_manager import InputDocument, InputType

logger = logging.getLogger("ezzio.agent.web_access_manager")

# Limites de sécurité des ressources Web
MAX_WEB_DOWNLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
WEB_FETCH_TIMEOUT_SEC = 15.0


class WebAccessMode(str, Enum):
    PUBLIC_HTTP = "PUBLIC_HTTP"
    PUBLIC_API = "PUBLIC_API"
    AUTHORIZED_BROWSER_SESSION = "AUTHORIZED_BROWSER_SESSION"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"


# Adresses et domaines privés interdits (Protection SSRF)
BLOCKED_IP_PATTERNS = [
    r"^127\.", r"^10\.", r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", r"^192\.168\.",
    r"^169\.254\.", r"^0\.0\.0\.0$", r"^localhost$"
]


class WebAccessManager:
    """Manager d'accès web universel : classification, protection SSRF, extraction HTML/JSON et traçabilité."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or r"G:\AI\E-zzio"
        self._user_agent = "E-ZZIO-Sovereign-Agent/1.0 (WebAccessManager; +http://127.0.0.1:8001)"

    def is_ssrf_safe(self, url: str) -> Tuple[bool, str]:
        """Vérifie la sécurité de l'URL contre les attaques SSRF (IPs privées, localhost, schemes interdits)."""
        if not url or not isinstance(url, str):
            return False, "URL vide ou invalide."

        url_clean = url.strip()
        parsed = urlparse(url_clean)

        if parsed.scheme.lower() not in ["http", "https"]:
            return False, f"Scheme non autorisé : {parsed.scheme}"

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "Nom d'hôte manquant dans l'URL."

        for pattern in BLOCKED_IP_PATTERNS:
            if re.search(pattern, hostname):
                return False, f"Protection SSRF : accès bloqué vers hôte privé '{hostname}'."

        return True, "OK"

    def classify_access_mode(self, url: str) -> WebAccessMode:
        """Classifie le mode d'accès requis pour l'URL ciblée."""
        safe, reason = self.is_ssrf_safe(url)
        if not safe:
            return WebAccessMode.BLOCKED

        hostname = (urlparse(url).hostname or "").lower()

        # Domaines spécifiques
        if "leboncoin.fr" in hostname:
            # Respect des conditions d'utilisation
            return WebAccessMode.PUBLIC_HTTP
        elif "instagram.com" in hostname or "facebook.com" in hostname:
            return WebAccessMode.PUBLIC_HTTP
        elif "api." in hostname or "/api/" in url:
            return WebAccessMode.PUBLIC_API

        return WebAccessMode.PUBLIC_HTTP

    def fetch_url(self, url: str, max_chars: int = 100000) -> InputDocument:
        """Récupère et extrait le contenu d'une URL publique de manière sécurisée."""
        mode = self.classify_access_mode(url)
        if mode == WebAccessMode.BLOCKED:
            self._log_audit("WEB_ACCESS_BLOCKED", {"url": url, "reason": "SSRF or Policy Blocked"})
            return InputDocument(
                source=url,
                input_type=InputType.URL,
                status="BLOCKED",
                content_text="[SECURITY BLOCK] Accès bloqué : tentative SSRF ou politique réseau restreinte."
            )

        try:
            import httpx
            headers = {"User-Agent": self._user_agent}
            resp = httpx.get(url, headers=headers, timeout=WEB_FETCH_TIMEOUT_SEC, follow_redirects=True)

            if resp.status_code in [401, 403]:
                self._log_audit("WEB_AUTH_REQUIRED", {"url": url, "status_code": resp.status_code})
                return InputDocument(
                    source=url,
                    input_type=InputType.URL,
                    status="AUTH_REQUIRED",
                    content_text=f"[AUTH REQUIRED] La ressource web nécessite une authentification (HTTP {resp.status_code})."
                )

            if resp.status_code != 200:
                return InputDocument(
                    source=url,
                    input_type=InputType.URL,
                    status="UNAVAILABLE",
                    content_text=f"Ressource web indisponible (HTTP {resp.status_code})."
                )

            content_type = resp.headers.get("content-type", "").lower()
            raw_text = resp.text[:max_chars]

            # Nettoyage HTML si text/html
            if "html" in content_type:
                clean_text = re.sub(r'<script[^>]*>.*?</script>', '', raw_text, flags=re.DOTALL)
                clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.DOTALL)
                clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            else:
                clean_text = raw_text.strip()

            self._log_provenance(url, mode.value, resp.status_code, len(clean_text))

            return InputDocument(
                source=url,
                input_type=InputType.URL,
                status="READY",
                content_text=f"[DONNÉES WEB EXTRACTIVES : {url}]\n{clean_text}",
                extracted_data={"http_status": resp.status_code, "content_type": content_type},
                metadata={"url": url, "access_mode": mode.value}
            )

        except Exception as exc:
            logger.warning("[WEB-FETCH-FAIL] Échec récupération URL %s : %s", url, exc)
            return InputDocument(
                source=url,
                input_type=InputType.URL,
                status="UNAVAILABLE",
                content_text=f"Échec de connexion réseau : {exc}"
            )

    def _log_provenance(self, url: str, access_mode: str, status_code: int, char_count: int) -> None:
        """Consigne l'accès web et la provenance dans l'AuditLedger."""
        payload = {
            "url": url[:200],
            "access_mode": access_mode,
            "status_code": status_code,
            "char_count": char_count
        }
        self._log_audit("WEB_PROVENANCE_RECORDED", payload)

    def _log_audit(self, action: str, payload: Dict[str, Any]) -> None:
        """Méthode interne d'enregistrement dans AuditLedger."""
        try:
            from core.security.audit_ledger import AuditLedger
            AuditLedger().record_event(actor="web-access-manager", action=action, payload=payload)
        except Exception:
            pass


web_access_manager = WebAccessManager()
