"""Déclaration des providers OAuth supportés."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]

def _read_secret(key: str) -> str | None:
    env_path = _ROOT / "secrets" / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    val = v.strip().strip("\"'")
                    return val or None
        except Exception:
            pass
    return os.environ.get(key) or None

PROVIDERS: dict[str, dict[str, Any]] = {
    "discord": {
        "name": "Discord", "icon": "discord", "category": "chat", "color": "#5865F2",
        "doc_url": "https://discord.com/developers/applications",
        "description": "Recevoir et envoyer des messages dans tes serveurs Discord.",
        "authorize_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "userinfo_url": "https://discord.com/api/users/@me",
        "scopes": ["identify", "email", "guilds"],
        "client_id_env": "DISCORD_CLIENT_ID", "client_secret_env": "DISCORD_CLIENT_SECRET",
        "account_id_field": "id", "display_name_field": "username", "email_field": "email",
    },
    "github": {
        "name": "GitHub", "icon": "github", "category": "dev", "color": "#24292e",
        "doc_url": "https://github.com/settings/developers",
        "description": "Lire et gérer tes repos, issues et pull requests.",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": ["read:user", "user:email", "repo"],
        "client_id_env": "GITHUB_CLIENT_ID", "client_secret_env": "GITHUB_CLIENT_SECRET",
        "account_id_field": "id", "display_name_field": "login", "email_field": "email",
    },
    "google": {
        "name": "Google (Gmail, Drive, Calendar)", "icon": "google", "category": "productivity",
        "color": "#EA4335", "doc_url": "https://console.cloud.google.com/apis/credentials",
        "description": "Accéder à Gmail, Drive et Calendar en lecture.",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scopes": ["openid", "email", "profile",
                   "https://www.googleapis.com/auth/gmail.readonly",
                   "https://www.googleapis.com/auth/drive.readonly",
                   "https://www.googleapis.com/auth/calendar.readonly"],
        "client_id_env": "GOOGLE_WORKSPACE_CLIENT_ID",
        "client_secret_env": "GOOGLE_WORKSPACE_CLIENT_SECRET",
        "account_id_field": "sub", "display_name_field": "name", "email_field": "email",
    },
    "slack": {
        "name": "Slack", "icon": "slack", "category": "chat", "color": "#4A154B",
        "doc_url": "https://api.slack.com/apps",
        "description": "Envoyer et recevoir des messages dans tes workspaces Slack.",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "userinfo_url": "https://slack.com/api/auth.test",
        "scopes": ["chat:write", "channels:read", "im:read"],
        "client_id_env": "SLACK_CLIENT_ID", "client_secret_env": "SLACK_CLIENT_SECRET",
        "account_id_field": "user_id", "display_name_field": "user", "email_field": None,
    },
    "linkedin": {
        "name": "LinkedIn", "icon": "linkedin", "category": "social", "color": "#0077B5",
        "doc_url": "https://www.linkedin.com/developers/apps",
        "description": "Publier et lire depuis ton compte LinkedIn.",
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "userinfo_url": "https://api.linkedin.com/v2/userinfo",
        "scopes": ["openid", "profile", "email"],
        "client_id_env": "LINKEDIN_CLIENT_ID", "client_secret_env": "LINKEDIN_CLIENT_SECRET",
        "account_id_field": "sub", "display_name_field": "name", "email_field": "email",
    },
    "facebook": {
        "name": "Facebook / Instagram / Messenger", "icon": "facebook", "category": "social",
        "color": "#1877F2", "doc_url": "https://developers.facebook.com/apps",
        "description": "Publier et interagir avec Facebook, Instagram et Messenger.",
        "authorize_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "userinfo_url": "https://graph.facebook.com/me?fields=id,name,email",
        "scopes": ["public_profile", "email", "pages_show_list"],
        "client_id_env": "META_CLIENT_ID", "client_secret_env": "META_CLIENT_SECRET",
        "account_id_field": "id", "display_name_field": "name", "email_field": "email",
    },
    "x": {
        "name": "X (Twitter)", "icon": "twitter", "category": "social", "color": "#000000",
        "doc_url": "https://developer.twitter.com/en/portal/dashboard",
        "description": "Publier et lire depuis ton compte X.",
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "userinfo_url": "https://api.twitter.com/2/users/me",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],
        "client_id_env": "X_CLIENT_ID", "client_secret_env": "X_CLIENT_SECRET",
        "account_id_field": "data.id", "display_name_field": "data.username", "email_field": None,
    },
}

def list_providers() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pid, cfg in PROVIDERS.items():
        cid = _read_secret(cfg["client_id_env"])
        csec = _read_secret(cfg["client_secret_env"])
        out.append({
            "id": pid, "name": cfg["name"], "icon": cfg["icon"],
            "category": cfg["category"], "color": cfg["color"],
            "doc_url": cfg["doc_url"], "description": cfg["description"],
            "configured": bool(cid and csec),
            "client_id_present": bool(cid),
        })
    return out

def get_provider(pid: str) -> dict[str, Any] | None:
    cfg = PROVIDERS.get(pid)
    if not cfg:
        return None
    cfg = dict(cfg)
    cfg["id"] = pid
    cfg["client_id"] = _read_secret(cfg["client_id_env"])
    cfg["client_secret"] = _read_secret(cfg["client_secret_env"])
    return cfg
