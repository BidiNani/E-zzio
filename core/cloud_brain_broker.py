from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_ROOT = PROJECT_ROOT / "secrets"
SECRETS_PATH = SECRETS_ROOT / "cloud_brain.env"
STATE_ROOT = PROJECT_ROOT / "state" / "cloud_brain"
CACHE_ROOT = STATE_ROOT / "cache"
USAGE_PATH = STATE_ROOT / "usage.jsonl"
AUDIT_PATH = STATE_ROOT / "audit.jsonl"

STATE_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

for key, value in {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}.items():
    os.environ[key] = value

DEFAULTS = {
    "EZZIO_CLOUD_ALLOW_SEND": "false",
    "EZZIO_CLOUD_MODE": "local_first",
    "EZZIO_CLOUD_DAILY_TOTAL_LIMIT": "120",
    "EZZIO_CLOUD_TIMEOUT_SEC": "60",
    "EZZIO_CLOUD_CACHE_TTL_SEC": "86400",
    "EZZIO_CLOUD_REDACT_SECRETS": "true",
    "EZZIO_CLOUD_LOG_PROMPTS": "false",
    "GEMINI_API_KEY": "",
    "GEMINI_MODEL": "gemini-2.0-flash",
    "GEMINI_DAILY_LIMIT": "50",
    "GROQ_API_KEY": "",
    "GROQ_MODEL": "llama-3.1-8b-instant",
    "GROQ_DAILY_LIMIT": "80",
    "OPENROUTER_API_KEY": "",
    "OPENROUTER_MODEL": "",
    "OPENROUTER_DAILY_LIMIT": "45",
    "OPENROUTER_SITE_URL": "http://127.0.0.1:8001",
    "OPENROUTER_APP_NAME": "E-ZZIO",
}

SECRET_KEYS = {"GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"}

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def today() -> str:
    return time.strftime("%Y-%m-%d")

def bool_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}

def int_value(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default

def parse_env_file(path: Path) -> Dict[str, str]:
    env = dict(DEFAULTS)

    if path.exists():
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")

    for key in set(DEFAULTS.keys()) | SECRET_KEYS:
        val = os.environ.get(key)
        if val:
            env[key] = val

    return env

def cfg() -> Dict[str, str]:
    return parse_env_file(SECRETS_PATH)

def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    event.setdefault("created_at", now())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

def read_jsonl(path: Path, limit: int = 1000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-max(1, min(limit, 5000)):]:
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"broken_line": line[:400]})
    return rows

def usage_counts() -> Dict[str, Any]:
    rows = read_jsonl(USAGE_PATH, 5000)
    day = today()
    by_provider: Dict[str, int] = {}
    total = 0

    for row in rows:
        if row.get("day") != day:
            continue
        provider = row.get("provider") or "unknown"
        by_provider[provider] = by_provider.get(provider, 0) + 1
        total += 1

    return {"day": day, "total_today": total, "by_provider": by_provider}

def provider_key(provider: str, config: Dict[str, str]) -> str:
    return {
        "gemini": config.get("GEMINI_API_KEY", ""),
        "groq": config.get("GROQ_API_KEY", ""),
        "openrouter": config.get("OPENROUTER_API_KEY", ""),
    }.get(provider, "")

def provider_model(provider: str, config: Dict[str, str]) -> str:
    return {
        "gemini": config.get("GEMINI_MODEL", ""),
        "groq": config.get("GROQ_MODEL", ""),
        "openrouter": config.get("OPENROUTER_MODEL", ""),
    }.get(provider, "")

def provider_limit(provider: str, config: Dict[str, str]) -> int:
    return int_value({
        "gemini": config.get("GEMINI_DAILY_LIMIT", "50"),
        "groq": config.get("GROQ_DAILY_LIMIT", "80"),
        "openrouter": config.get("OPENROUTER_DAILY_LIMIT", "45"),
    }.get(provider, "0"), 0)

def provider_available(provider: str, config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    config = config or cfg()
    usage = usage_counts()
    used = int(usage.get("by_provider", {}).get(provider, 0))
    limit = provider_limit(provider, config)
    key = provider_key(provider, config)
    model = provider_model(provider, config)

    return {
        "provider": provider,
        "configured": bool(key),
        "model": model,
        "today_used": used,
        "daily_limit": limit,
        "remaining": max(0, limit - used),
        "usable": bool(key) and bool(model) and used < limit,
    }

def redacted_config(config: Dict[str, str]) -> Dict[str, Any]:
    output = {}
    for key, value in config.items():
        if key in SECRET_KEYS:
            output[key] = {"configured": bool(value), "redacted": "***" if value else ""}
        else:
            output[key] = value
    return output

def providers() -> Dict[str, Any]:
    config = cfg()
    names = ["gemini", "groq", "openrouter"]
    usage = usage_counts()

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.23.1c-cloud-brain-stable",
        "allow_send": bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND")),
        "mode": config.get("EZZIO_CLOUD_MODE", "local_first"),
        "usage": usage,
        "daily_total_limit": int_value(config.get("EZZIO_CLOUD_DAILY_TOTAL_LIMIT"), 120),
        "providers": [provider_available(name, config) for name in names],
        "config": redacted_config(config),
        "policy": {
            "local_first": True,
            "cloud_requires_allow_send": True,
            "secrets_redacted": True,
            "no_ads": True,
            "no_tracking": True,
            "gpu": "untouched",
        },
    }

def status() -> Dict[str, Any]:
    try:
        data = providers()
        data.update({
            "secrets_path": str(SECRETS_PATH),
            "state_root": str(STATE_ROOT),
            "cache_count": len(list(CACHE_ROOT.glob("*.json"))),
            "audit_path": str(AUDIT_PATH),
            "usage_path": str(USAGE_PATH),
            "endpoints": [
                "/cloud-brain/status",
                "/cloud-brain/providers",
                "/cloud-brain/route",
                "/api/chat/cloud",
                "/api/chat/hybrid",
            ],
        })
        return data
    except Exception as exc:
        return {
            "ok": False,
            "version": "v2.23.1c-cloud-brain-stable",
            "error": str(exc),
            "secrets_path": str(SECRETS_PATH),
            "state_root": str(STATE_ROOT),
        }

def redact_text(text: str) -> str:
    cleaned = text or ""
    for pattern in [
        r"sk-[A-Za-z0-9_\-]{12,}",
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"gsk_[A-Za-z0-9_\-]{20,}",
        r"or-[A-Za-z0-9_\-]{20,}",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+",
    ]:
        cleaned = re.sub(pattern, "[REDACTED_SECRET]", cleaned)
    return cleaned

def cache_key(provider: str, model: str, text: str, system: str) -> str:
    payload = json.dumps(
        {"provider": provider, "model": model, "text": text, "system": system},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def cache_get(key: str, ttl: int) -> Optional[Dict[str, Any]]:
    path = CACHE_ROOT / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("_created_at_epoch", 0)) > ttl:
            return None
        data["cache_hit"] = True
        return data
    except Exception:
        return None

def cache_set(key: str, data: Dict[str, Any]) -> None:
    clone = dict(data)
    clone["_created_at_epoch"] = time.time()
    (CACHE_ROOT / f"{key}.json").write_text(json.dumps(clone, ensure_ascii=False, indent=2), encoding="utf-8")

def allowed_to_send(provider: str, config: Dict[str, str]) -> Tuple[bool, str]:
    if not bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND")):
        return False, "cloud_send_disabled"

    usage = usage_counts()
    total_limit = int_value(config.get("EZZIO_CLOUD_DAILY_TOTAL_LIMIT"), 120)
    if int(usage.get("total_today", 0)) >= total_limit:
        return False, "daily_total_limit_reached"

    available = provider_available(provider, config)
    if not available["configured"]:
        return False, "provider_key_missing"
    if not available["model"]:
        return False, "provider_model_missing"
    if available["remaining"] <= 0:
        return False, "provider_daily_limit_reached"

    return True, "ok"

def record_usage(provider: str, model: str, ok: bool) -> None:
    append_jsonl(USAGE_PATH, {"day": today(), "provider": provider, "model": model, "ok": ok})

def http_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "json": json.loads(raw)}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "error": raw[:2000]}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}

def default_system() -> str:
    return (
        "Tu es le cerveau cloud optionnel d'E-ZZIO. Réponds en français, avec précision. "
        "E-ZZIO local garde le contrôle des actions PC. Respecte local-first, CPU/RAM only, "
        "GPU untouched, zéro publicité, zéro tracking."
    )

def call_gemini(text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    provider = "gemini"
    model = provider_model(provider, config)
    key = provider_key(provider, config)
    timeout = int_value(config.get("EZZIO_CLOUD_TIMEOUT_SEC"), 60)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{text}".strip()}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 700},
    }

    res = http_json(url, {"Content-Type": "application/json"}, payload, timeout)
    if not res["ok"]:
        return {"ok": False, "provider": provider, "model": model, "status": res.get("status"), "error": res.get("error")}

    reply = ""
    try:
        parts = res["json"]["candidates"][0]["content"]["parts"]
        reply = "".join(p.get("text", "") for p in parts)
    except Exception:
        reply = ""

    return {"ok": bool(reply), "provider": provider, "model": model, "reply": reply.strip(), "raw_status": res.get("status")}

def call_openai_compatible(provider: str, base_url: str, text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    model = provider_model(provider, config)
    key = provider_key(provider, config)
    timeout = int_value(config.get("EZZIO_CLOUD_TIMEOUT_SEC"), 60)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    if provider == "openrouter":
        headers["HTTP-Referer"] = config.get("OPENROUTER_SITE_URL", "http://127.0.0.1:8001")
        headers["X-Title"] = config.get("OPENROUTER_APP_NAME", "E-ZZIO")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }

    res = http_json(base_url.rstrip("/") + "/chat/completions", headers, payload, timeout)
    if not res["ok"]:
        return {"ok": False, "provider": provider, "model": model, "status": res.get("status"), "error": res.get("error")}

    reply = ""
    try:
        reply = res["json"]["choices"][0]["message"]["content"]
    except Exception:
        reply = ""

    return {"ok": bool(reply), "provider": provider, "model": model, "reply": reply.strip(), "raw_status": res.get("status")}

def call_provider(provider: str, text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    allowed, reason = allowed_to_send(provider, config)
    if not allowed:
        return {"ok": False, "provider": provider, "blocked": True, "reason": reason}

    clean_text = redact_text(text) if bool_value(config.get("EZZIO_CLOUD_REDACT_SECRETS")) else text
    clean_system = redact_text(system) if bool_value(config.get("EZZIO_CLOUD_REDACT_SECRETS")) else system

    if provider == "gemini":
        result = call_gemini(clean_text, clean_system, config)
    elif provider == "groq":
        result = call_openai_compatible(provider, "https://api.groq.com/openai/v1", clean_text, clean_system, config)
    elif provider == "openrouter":
        result = call_openai_compatible(provider, "https://openrouter.ai/api/v1", clean_text, clean_system, config)
    else:
        result = {"ok": False, "provider": provider, "error": "unknown_provider"}

    record_usage(provider, result.get("model", ""), bool(result.get("ok")))

    append_jsonl(AUDIT_PATH, {
        "provider": provider,
        "ok": bool(result.get("ok")),
        "model": result.get("model"),
        "status": result.get("status") or result.get("raw_status"),
        "blocked": result.get("blocked", False),
        "reason": result.get("reason"),
        "logged_prompt": clean_text if bool_value(config.get("EZZIO_CLOUD_LOG_PROMPTS")) else "[prompt_logging_disabled]",
    })

    return result

def choose_providers(config: Dict[str, str], prefer: str = "auto") -> List[str]:
    if prefer and prefer != "auto":
        return [prefer]
    order = ["gemini", "groq", "openrouter"]
    usable = [p for p in order if provider_available(p, config)["usable"]]
    return usable + [p for p in order if p not in usable]

def cloud_chat(text: str, provider: str = "auto", system: str = "", use_cache: bool = True) -> Dict[str, Any]:
    started = time.time()
    config = cfg()
    system_prompt = system.strip() or default_system()
    ttl = int_value(config.get("EZZIO_CLOUD_CACHE_TTL_SEC"), 86400)

    attempts = []
    for name in choose_providers(config, provider):
        model = provider_model(name, config)
        key = cache_key(name, model, redact_text(text), system_prompt)

        if use_cache:
            cached = cache_get(key, ttl)
            if cached:
                cached["elapsed_ms"] = int((time.time() - started) * 1000)
                cached["cache_hit"] = True
                return cached

        result = call_provider(name, text, system_prompt, config)
        attempts.append({
            "provider": name,
            "ok": result.get("ok"),
            "blocked": result.get("blocked", False),
            "reason": result.get("reason"),
            "status": result.get("status"),
            "model": result.get("model"),
        })

        if result.get("ok") and result.get("reply"):
            output = {
                "ok": True,
                "created_at": now(),
                "version": "v2.23.1c-cloud-brain-stable",
                "provider": name,
                "model": result.get("model"),
                "reply": result.get("reply"),
                "attempts": attempts,
                "elapsed_ms": int((time.time() - started) * 1000),
                "cache_hit": False,
                "policy": {"cloud_optional": True, "local_controls_actions": True, "secrets_redacted": True, "gpu": "untouched", "no_ads": True},
            }
            if use_cache:
                cache_set(key, output)
            return output

    return {
        "ok": False,
        "created_at": now(),
        "version": "v2.23.1c-cloud-brain-stable",
        "provider": None,
        "model": None,
        "reply": "Aucun fournisseur cloud disponible ou autorisé. Fallback local recommandé.",
        "attempts": attempts,
        "elapsed_ms": int((time.time() - started) * 1000),
        "cache_hit": False,
    }

def hybrid_chat(text: str, provider: str = "auto", force_cloud: bool = False) -> Dict[str, Any]:
    low = (text or "").lower()
    wants_cloud = force_cloud or any(w in low for w in ["cloud", "api", "raisonnement profond", "analyse complexe", "cerveau externe"])

    if wants_cloud:
        cloud = cloud_chat(text=text, provider=provider, use_cache=True)
        if cloud.get("ok"):
            cloud["mode"] = "cloud"
            return cloud

    try:
        from core.pc_commander import command
        local = command(text=text, session="pc")
        local["mode"] = "local_fallback" if wants_cloud else "local_first"
        local["cloud_attempted"] = wants_cloud
        return local
    except Exception as exc:
        return {"ok": False, "version": "v2.23.1c-cloud-brain-stable", "mode": "error", "reply": f"Erreur fallback local : {exc}", "error": str(exc)}

def route(text: str, provider: str = "auto") -> Dict[str, Any]:
    config = cfg()
    low = (text or "").lower()
    reasons = []

    if any(w in low for w in ["cloud", "api", "raisonnement profond", "analyse complexe", "gros code", "long contexte"]):
        reasons.append("demande_complexe_ou_cloud")

    if any(w in low for w in ["secret", "clé api", "cle api", "token", "password", "mot de passe"]):
        reasons.append("secret_detected_prefer_local")

    allow = bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND"))
    decision = "cloud" if allow and reasons and "secret_detected_prefer_local" not in reasons else "local"

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.23.1c-cloud-brain-stable",
        "decision": decision,
        "reasons": reasons or ["local_first_default"],
        "allow_send": allow,
        "providers": providers().get("providers", []),
        "policy": {"local_first": True, "cloud_optional": True, "secret_redaction": True, "no_ads": True, "gpu": "untouched"},
    }

