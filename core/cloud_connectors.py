
import os
from pathlib import Path

from dotenv import load_dotenv

from core.cloud_guard import cloud_status, guarded_request


def reddit_token():
    """Récupère le token OAuth Reddit depuis les variables d'environnement."""
    return (os.getenv("REDDIT_TOKEN") or os.getenv("REDDIT_ACCESS_TOKEN") or "").strip()


def blizzard_token():
    """Récupère le token OAuth Blizzard depuis les variables d'environnement."""
    return (os.getenv("BLIZZARD_TOKEN") or os.getenv("BLIZZARD_ACCESS_TOKEN") or "").strip()


PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_PATH = PROJECT_ROOT / "secrets" / ".env"
TOKEN_STATE = PROJECT_ROOT / "registry" / "cloud_tokens_runtime.json"

load_dotenv(SECRETS_PATH)


def _token_state_load():
    try:
        if TOKEN_STATE.exists():
            return __import__("json").loads(TOKEN_STATE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _token_state_save(data):
    TOKEN_STATE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_STATE.write_text(__import__("json").dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def github_headers():
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "E-ZZIO-local",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(path, params=None):
    path = path.lstrip("/")
    return guarded_request(
        "GET",
        f"https://api.github.com/{path}",
        headers=github_headers(),
        params=params or {},
        cache=True,
    )


def reddit_headers():
    user_agent = os.getenv("REDDIT_USER_AGENT", "E-ZZIO-local/1.0").strip()
    token = reddit_token()
    headers = {"User-Agent": user_agent}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def reddit_get(path, params=None):
    path = path.lstrip("/")
    return guarded_request(
        "GET",
        f"https://oauth.reddit.com/{path}",
        headers=reddit_headers(),
        params=params or {},
        cache=True,
        cache_ttl=120,
    )


def blizzard_region():
    return os.getenv("BLIZZARD_REGION", "eu").strip().lower() or "eu"


def blizzard_headers():
    token = blizzard_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def blizzard_get(path, params=None):
    region = blizzard_region()
    path = path.lstrip("/")
    merged = dict(params or {})
    merged.setdefault("namespace", f"dynamic-{region}")
    merged.setdefault("locale", "fr_FR")

    return guarded_request(
        "GET",
        f"https://{region}.api.blizzard.com/{path}",
        headers=blizzard_headers(),
        params=merged,
        cache=True,
        cache_ttl=600,
    )


def connectors_status():
    return {
        "cloud_guard": cloud_status(),
        "tokens_configured": {
            "github": bool(os.getenv("GITHUB_TOKEN", "").strip()),
            "reddit": bool(os.getenv("REDDIT_CLIENT_ID", "").strip() and os.getenv("REDDIT_CLIENT_SECRET", "").strip()),
            "blizzard": bool(os.getenv("BLIZZARD_CLIENT_ID", "").strip() and os.getenv("BLIZZARD_CLIENT_SECRET", "").strip()),
        },
    }

