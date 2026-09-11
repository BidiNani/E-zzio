import os
import time
import base64
import httpx
from dotenv import load_dotenv
from pathlib import Path

from core.cloud_guard import guarded_request, cloud_status

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


def reddit_token():
    state = _token_state_load()
    existing = state.get("reddit", {})
    if existing.get("access_token") and existing.get("expires_at", 0) > time.time() + 60:
        return existing["access_token"]

    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    username = os.getenv("REDDIT_USERNAME", "").strip()
    password = os.getenv("REDDIT_PASSWORD", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "E-ZZIO-local/1.0").strip()

    if not all([client_id, client_secret, username, password]):
        return None

    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    response = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=auth,
        data={"grant_type": "password", "username": username, "password": password},
        headers={"User-Agent": user_agent},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()

    token = data["access_token"]
    state["reddit"] = {
        "access_token": token,
        "expires_at": time.time() + int(data.get("expires_in", 3600)),
    }
    _token_state_save(state)
    return token


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


def blizzard_token():
    state = _token_state_load()
    existing = state.get("blizzard", {})
    if existing.get("access_token") and existing.get("expires_at", 0) > time.time() + 60:
        return existing["access_token"]

    client_id = os.getenv("BLIZZARD_CLIENT_ID", "").strip()
    client_secret = os.getenv("BLIZZARD_CLIENT_SECRET", "").strip()

    if not all([client_id, client_secret]):
        return None

    blizzard_region()
    token_url = "https://oauth.battle.net/token"

    auth_raw = f"{client_id}:{client_secret}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_raw).decode("ascii")

    response = requests.post(
        token_url,
        headers={"Authorization": f"Basic {auth_b64}"},
        data={"grant_type": "client_credentials"},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()

    token = data["access_token"]
    state["blizzard"] = {
        "access_token": token,
        "expires_at": time.time() + int(data.get("expires_in", 3600)),
    }
    _token_state_save(state)
    return token


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
