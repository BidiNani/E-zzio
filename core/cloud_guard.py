import json
import time
import hashlib
import ipaddress
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_PATH = PROJECT_ROOT / "secrets" / ".env"
CACHE_ROOT = PROJECT_ROOT / "registry" / "cloud_cache"
STATE_PATH = PROJECT_ROOT / "registry" / "cloud_rate_state.json"
AUDIT_PATH = PROJECT_ROOT / "registry" / "cloud_audit.jsonl"

load_dotenv(SECRETS_PATH)

ALLOWED_HOSTS = {
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",

    "oauth.reddit.com",
    "www.reddit.com",
    "reddit.com",

    "eu.api.blizzard.com",
    "us.api.blizzard.com",
    "kr.api.blizzard.com",
    "tw.api.blizzard.com",
    "oauth.battle.net",

    "fr.wikipedia.org",
    "en.wikipedia.org",
    "www.wikidata.org",
    "query.wikidata.org",
    "commons.wikimedia.org",
    "api.wikimedia.org",

    "api.stackexchange.com",

    "export.arxiv.org",

    "api.crossref.org",

    "api.open-meteo.com",
    "geocoding-api.open-meteo.com",
    "archive-api.open-meteo.com",

    "nominatim.openstreetmap.org",
}

DEFAULT_LIMITS = {
    "github": {"min_interval": 0.80, "cache_ttl": 300},
    "reddit": {"min_interval": 1.10, "cache_ttl": 180},
    "blizzard": {"min_interval": 0.45, "cache_ttl": 600},

    "wikipedia": {"min_interval": 1.00, "cache_ttl": 3600},
    "wikidata": {"min_interval": 1.20, "cache_ttl": 3600},
    "stackexchange": {"min_interval": 1.00, "cache_ttl": 900},
    "arxiv": {"min_interval": 3.20, "cache_ttl": 7200},
    "crossref": {"min_interval": 0.60, "cache_ttl": 7200},
    "openmeteo": {"min_interval": 0.30, "cache_ttl": 900},
    "osm": {"min_interval": 1.10, "cache_ttl": 86400},

    "generic": {"min_interval": 1.50, "cache_ttl": 300},
}

def now():
    return time.time()

def audit(event_type, payload=None):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": now(),
        "type": event_type,
        "payload": payload or {},
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def safe_json_read(path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def safe_json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def provider_from_url(url):
    host = urlparse(url).netloc.lower()

    if "github" in host:
        return "github"
    if "reddit" in host:
        return "reddit"
    if "blizzard" in host or "battle.net" in host:
        return "blizzard"
    if "wikipedia" in host or "wikimedia" in host:
        return "wikipedia"
    if "wikidata" in host:
        return "wikidata"
    if "stackexchange" in host:
        return "stackexchange"
    if "arxiv" in host:
        return "arxiv"
    if "crossref" in host:
        return "crossref"
    if "open-meteo" in host or "openmeteo" in host:
        return "openmeteo"
    if "openstreetmap" in host:
        return "osm"

    return "generic"

def is_private_host(host):
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
    except Exception:
        return False

def validate_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("Cloud Guard: HTTPS obligatoire.")

    host = parsed.netloc.lower().split("@")[-1].split(":")[0]

    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Cloud Guard: domaine refusé: {host}")

    if is_private_host(host):
        raise ValueError("Cloud Guard: adresse privée/locale refusée.")

    return host

def cache_key(method, url, params=None, body=None):
    raw = json.dumps({
        "method": method.upper(),
        "url": url,
        "params": params or {},
        "body": body or {},
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_cache(key, ttl):
    path = CACHE_ROOT / f"{key}.json"
    if not path.exists():
        return None

    item = safe_json_read(path, None)
    if not item:
        return None

    age = now() - float(item.get("ts", 0))
    if age > ttl:
        return None

    item["cache_age_sec"] = round(age, 2)
    return item

def set_cache(key, payload):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    path = CACHE_ROOT / f"{key}.json"
    safe_json_write(path, {
        "ts": now(),
        "payload": payload,
    })

def rate_wait(provider):
    limits = DEFAULT_LIMITS.get(provider, DEFAULT_LIMITS["generic"])
    state = safe_json_read(STATE_PATH, {})
    item = state.get(provider, {})
    last = float(item.get("last_request_ts", 0))
    elapsed = now() - last
    wait = max(0.0, float(limits["min_interval"]) - elapsed)

    if wait > 0:
        time.sleep(wait)

    item["last_request_ts"] = now()
    state[provider] = item
    safe_json_write(STATE_PATH, state)

    return round(wait, 3)

def redacted_headers(headers):
    clean = {}
    for key, value in (headers or {}).items():
        lk = key.lower()
        if lk in ["authorization", "cookie", "x-api-key"]:
            clean[key] = "***REDACTED***"
        else:
            clean[key] = value
    return clean

def guarded_request(method, url, headers=None, params=None, json_body=None, timeout=25, cache=True, cache_ttl=None):
    host = validate_url(url)
    provider = provider_from_url(url)
    limits = DEFAULT_LIMITS.get(provider, DEFAULT_LIMITS["generic"])
    ttl = cache_ttl if cache_ttl is not None else limits["cache_ttl"]

    method = method.upper()
    key = cache_key(method, url, params=params, body=json_body)

    if method == "GET" and cache:
        cached = get_cache(key, ttl)
        if cached:
            audit("cloud_cache_hit", {"provider": provider, "host": host, "url": url})
            return {
                "ok": True,
                "cached": True,
                "provider": provider,
                "status_code": 200,
                "data": cached["payload"],
                "cache_age_sec": cached.get("cache_age_sec"),
            }

    waited = rate_wait(provider)

    audit("cloud_request", {
        "provider": provider,
        "host": host,
        "method": method,
        "url": url,
        "params": params or {},
        "headers": redacted_headers(headers),
        "waited_sec": waited,
    })

    response = requests.request(
        method=method,
        url=url,
        headers=headers or {},
        params=params or {},
        json=json_body,
        timeout=timeout,
    )

    rate_headers = {
        k: v for k, v in response.headers.items()
        if k.lower().startswith("x-ratelimit") or k.lower() in ["retry-after", "x-cache-status"]
    }

    result = {
        "ok": response.status_code < 400,
        "cached": False,
        "provider": provider,
        "status_code": response.status_code,
        "rate_headers": rate_headers,
        "text": response.text[:30000],
    }

    try:
        result["data"] = response.json()
    except Exception:
        result["data"] = None

    if response.status_code == 429:
        result["warning"] = "Rate limit atteint. Respecter Retry-After / X-RateLimit-Reset."

    if method == "GET" and cache and result["ok"]:
        set_cache(key, result.get("data") if result.get("data") is not None else result.get("text"))

    return result

def cloud_status():
    return {
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "limits": DEFAULT_LIMITS,
        "state": safe_json_read(STATE_PATH, {}),
        "cache_dir": str(CACHE_ROOT),
        "audit_path": str(AUDIT_PATH),
        "policy": {
            "https_only": True,
            "domain_allowlist": True,
            "private_ip_block": True,
            "secrets_redaction": True,
            "local_rate_limit": True,
            "cache_get_requests": True,
            "no_rate_limit_bypass": True,
            "token_compression_ready": True,
        },
    }
