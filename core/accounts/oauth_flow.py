"""Génération URL authorize + échange code->token."""
from __future__ import annotations
import logging
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import httpx
from core.accounts import store
from core.accounts.oauth_registry import get_provider

logger = logging.getLogger("OAuthFlow")
_STATES: Dict[str, str] = {}

def _redirect_uri(provider_id: str, base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/accounts/callback/{provider_id}"

def build_authorize_url(provider_id: str, base_url: str) -> Dict[str, Any]:
    cfg = get_provider(provider_id)
    if not cfg:
        return {"ok": False, "error": f"Provider inconnu : {provider_id}"}
    if not cfg["client_id"] or not cfg["client_secret"]:
        return {
            "ok": False, "error": "PROVIDER_NOT_CONFIGURED",
            "message": (f"Le provider '{cfg['name']}' n'a pas de credentials. "
                        f"Renseigne {cfg['client_id_env']} et {cfg['client_secret_env']} "
                        f"dans secrets/.env puis redémarre le backend."),
            "doc_url": cfg["doc_url"],
        }
    state = secrets.token_urlsafe(24)
    _STATES[state] = provider_id
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": _redirect_uri(provider_id, base_url),
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "state": state,
    }
    if provider_id in ("google", "x"):
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    if provider_id == "x":
        params["code_challenge"] = "challenge"
        params["code_challenge_method"] = "plain"
    return {"ok": True, "url": f"{cfg['authorize_url']}?{urlencode(params)}",
            "state": state, "provider": provider_id}

async def exchange_code(provider_id: str, code: str, state: str, base_url: str) -> Dict[str, Any]:
    if _STATES.pop(state, None) != provider_id:
        return {"ok": False, "error": "STATE_INVALID", "message": "State OAuth invalide."}
    cfg = get_provider(provider_id)
    if not cfg or not cfg["client_id"] or not cfg["client_secret"]:
        return {"ok": False, "error": "PROVIDER_NOT_CONFIGURED"}
    payload = {
        "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "code": code, "grant_type": "authorization_code",
        "redirect_uri": _redirect_uri(provider_id, base_url),
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(cfg["token_url"], data=payload,
                                  headers={"Accept": "application/json"})
            r.raise_for_status()
            tok = r.json()
        except Exception as exc:
            logger.error("[OAUTH] échange échoué (%s) : %s", provider_id, exc)
            return {"ok": False, "error": "TOKEN_EXCHANGE_FAILED", "message": str(exc)}
        access_token = tok.get("access_token")
        if not access_token:
            return {"ok": False, "error": "NO_ACCESS_TOKEN", "raw": tok}
        refresh_token = tok.get("refresh_token")
        expires_in = tok.get("expires_in")
        scopes = (tok.get("scope") or "").split() or cfg["scopes"]
        profile: Dict[str, Any] = {}
        try:
            pr = await client.get(cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/json"})
            if pr.status_code == 200:
                profile = pr.json()
        except Exception as exc:
            logger.warning("[OAUTH] profil échoué : %s", exc)
    def _extract(path):
        if not path: return None
        cur = profile
        for part in path.split("."):
            if isinstance(cur, dict): cur = cur.get(part)
            else: return None
        return str(cur) if cur is not None else None
    saved = store.save_account(
        provider_id, access_token=access_token, refresh_token=refresh_token,
        expires_in=expires_in, scopes=scopes,
        account_id=_extract(cfg.get("account_id_field")),
        display_name=_extract(cfg.get("display_name_field")),
        email=_extract(cfg.get("email_field")),
    )
    return {"ok": True, "account": saved}