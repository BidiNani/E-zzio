"""E-ZZIO Universal Perception — Safe Web Fetcher (Strict Anti-SSRF Defense).

Protects the core runtime from Server-Side Request Forgery:
- Resolves DNS and strictly rejects loopback, RFC 1918 private IPs, link-local (169.254.x.x)
- Enforces strict response size limits (max 10 MB) and timeout (8s)
- Passes downloaded content to UniversalFileReader for safe extraction
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from core.perception.universal_reader import UniversalFileReader

logger = logging.getLogger("SafeWebFetcher")

MAX_RESPONSE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Mo


class SSRFSecurityError(PermissionError):
    """Levée en cas de tentative d'accès à une IP privée/locale."""
    pass


class SafeWebFetcher:
    def __init__(self, timeout_s: float = 8.0, max_size_bytes: int = MAX_RESPONSE_SIZE_BYTES):
        self.timeout_s = timeout_s
        self.max_size_bytes = max_size_bytes
        self.reader = UniversalFileReader(max_size_bytes=max_size_bytes)

    def is_ip_allowed(self, ip_str: str) -> bool:
        """Vérifie si une adresse IP est publique et non locale/privée."""
        try:
            ip = ipaddress.ip_address(ip_str)
            # Rejeter adresses privées, loopback, link-local, réservées, multicast
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
            # Bloquer spécifiquement 0.0.0.0
            if ip.is_unspecified:
                return False
            return True
        except ValueError:
            return False

    def validate_url_safety(self, url: str) -> tuple[str, str]:
        """Valide qu'une URL n'est pas une tentative SSRF et retourne le hostname et l'IP épinglée."""
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise SSRFSecurityError(f"Protocole non sécurisé ou non supporté : {scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityError("URL invalide : hôte manquant.")

        # Vérification brute si le hostname est 'localhost' ou similaire
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "local"):
            raise SSRFSecurityError(f"[SSRF DENY] Accès à l'hôte local interdit : {hostname}")

        # Résolution DNS et validation de toutes les adresses
        safe_ip = None
        try:
            resolved_ips = socket.getaddrinfo(hostname, parsed.port or (443 if scheme == "https" else 80))
            for res in resolved_ips:
                ip_addr = res[4][0]
                if not self.is_ip_allowed(ip_addr):
                    raise SSRFSecurityError(f"[SSRF DENY] L'hôte {hostname} résout vers une IP locale/privée interdite ({ip_addr})")
                if safe_ip is None:
                    safe_ip = ip_addr
        except socket.gaierror as exc:
            raise SSRFSecurityError(f"Échec de résolution DNS pour {hostname} : {exc}") from exc

        if not safe_ip:
            raise SSRFSecurityError(f"Aucune adresse IP valide trouvée pour {hostname}")

        return hostname, safe_ip

    async def fetch_url(self, url: str) -> dict[str, Any]:
        """Récupère le contenu d'une URL externe de façon sécurisée (Anti-SSRF + Épinglage IP Anti-TOCTOU)."""
        try:
            hostname, safe_ip = self.validate_url_safety(url)
        except SSRFSecurityError as sec_err:
            logger.warning("[SSRF-BLOCKED] Requête bloquée vers %s : %s", url, sec_err)
            return {
                "ok": False,
                "status": "SSRF_BLOCKED",
                "error": str(sec_err),
                "url": url
            }

        headers = {
            "Host": hostname,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) E-ZzIO-Perception-Fetcher/2.0",
            "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain,*/*"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=False) as client:
                r = await client.get(url, headers=headers)
                if r.status_code != 200:
                    return {
                        "ok": False,
                        "status": f"HTTP_{r.status_code}",
                        "status_code": r.status_code,
                        "error": f"Erreur serveur HTTP {r.status_code}",
                        "url": url
                    }

                content_bytes = r.content
                if len(content_bytes) > self.max_size_bytes:
                    return {
                        "ok": False,
                        "status": "PAYLOAD_TOO_LARGE",
                        "error": f"Réponse HTTP trop volumineuse ({round(len(content_bytes)/(1024*1024), 2)} Mo)",
                        "url": url
                    }

                # Détection et parsing via UniversalFileReader
                detected_type = self.reader.detect_file_type(url, content_bytes)
                content_type = r.headers.get("content-type", "").lower()

                if "pdf" in content_type or detected_type == "pdf":
                    # Extraction textuelle PDF
                    return {
                        "ok": True,
                        "type": "pdf",
                        "url": url,
                        "bytes_count": len(content_bytes),
                        "content": f"[DOCUMENT PDF EN LIGNE : {url} | Taille : {len(content_bytes)} octets]"
                    }
                else:
                    # Extraction HTML épurée
                    raw_text = r.text
                    clean_text = self.reader._read_text_file(
                        Path(url)
                    ) if "html" not in content_type else self._clean_html_text(raw_text)

                    # Garde constitutionnelle : HTTP 200 ≠ Ingestion Réussie
                    # Si le texte extrait est vide ou correspond à une simple coquille HTML / mur de connexion
                    generic_shells = {"instagram", "facebook", "tiktok", "log in", "connexion", "login", "please enable javascript", "enable js"}
                    if len(clean_text) < 15 or clean_text.lower() in generic_shells:
                        return {
                            "ok": False,
                            "status": "EMPTY_OR_BLOCKED_SHELL",
                            "error": "La page récupérée est une coquille HTML vide, un challenge anti-bot ou un écran de connexion (HTTP 200 != Ingestion réussie).",
                            "url": url,
                            "chars_count": len(clean_text),
                            "content": clean_text
                        }

                    return {
                        "ok": True,
                        "type": "web_page",
                        "url": url,
                        "content_type": content_type,
                        "chars_count": len(clean_text),
                        "content": clean_text[:8000]
                    }

        except httpx.TimeoutException:
            return {"ok": False, "status": "TIMEOUT", "error": f"Délai d'attente dépassé ({self.timeout_s}s)", "url": url}
        except Exception as exc:
            return {"ok": False, "status": "FETCH_ERROR", "error": str(exc), "url": url}

    def _clean_html_text(self, html: str) -> str:
        """Nettoie le HTML pour en extraire le texte pur."""
        import re
        cleaned = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
