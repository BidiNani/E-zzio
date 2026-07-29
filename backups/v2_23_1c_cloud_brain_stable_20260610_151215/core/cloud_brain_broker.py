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
SECRETS_PATH = PROJECT_ROOT / "secrets" / "cloud_brain.env"
STATE_ROOT = PROJECT_ROOT / "state" / "cloud_brain"
CACHE_ROOT = STATE_ROOT / "cache"
USAGE_PATH = STATE_ROOT / "usage.jsonl"
AUDIT_PATH = STATE_ROOT / "audit.jsonl"

STATE_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
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
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

SECRET_KEYS = {
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
}

DEFAULTS: Dict[str, str] = {
    "EZZIO_CLOUD_ALLOW_SEND": "false",
    "EZZIO_CLOUD_MODE": "local_first",
    "EZZIO_CLOUD_DAILY_TOTAL_LIMIT": "120",
    "EZZIO_CLOUD_TIMEOUT_SEC": "60",
    "EZZIO_CLOUD_CACHE_TTL_SEC": "86400",
    "EZZIO_CLOUD_REDACT_SECRETS": "true",
    "EZZIO_CLOUD_LOG_PROMPTS": "false",
    "GEMINI_MODEL": "gemini-2.0-flash",
    "GEMINI_DAILY_LIMIT": "50",
    "GROQ_MODEL": "llama-3.1-8b-instant",
    "GROQ_DAILY_LIMIT": "80",
    "OPENROUTER_MODEL": "",
    "OPENROUTER_DAILY_LIMIT": "45",
    "OPENROUTER_SITE_URL": "http://127.0.0.1:8000",
    "OPENROUTER_APP_NAME": "E-ZZIO",
}

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def today() -> str:
    return time.strftime("%Y-%m-%d")

def parse_env_file(path: Path) -> Dict[str, str]:
    env = dict(DEFAULTS)

    if path.exists():
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env[key] = value

    for key in list(DEFAULTS.keys()) + list(SECRET_KEYS):
        if os.environ.get(key):
            env[key] = os.environ[key]

    return env

def cfg() -> Dict[str, str]:
    return parse_env_file(SECRETS_PATH)

def bool_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}

def int_value(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default

def redacted_config(config: Dict[str, str]) -> Dict[str, Any]:
    output = {}

    for key, value in config.items():
        if key in SECRET_KEYS:
            output[key] = {
                "configured": bool(value),
                "redacted": "***" if value else "",
            }
        else:
            output[key] = value

    return output

def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    item.setdefault("created_at", now())
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")

def read_jsonl(path: Path, limit: int = 1000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: List[Dict[str, Any]] = []

    for line in lines[-max(1, min(int(limit), 5000)):]:
        try:
            output.append(json.loads(line))
        except Exception:
            output.append({"broken_line": line[:400]})

    return output

def usage_counts() -> Dict[str, Any]:
    rows = read_jsonl(USAGE_PATH, limit=5000)
    day = today()

    total_today = 0
    by_provider: Dict[str, int] = {}

    for row in rows:
        if row.get("day") != day:
            continue

        total_today += 1
        provider = row.get("provider") or "unknown"
        by_provider[provider] = by_provider.get(provider, 0) + 1

    return {
        "day": day,
        "total_today": total_today,
        "by_provider": by_provider,
    }

def provider_daily_limit(provider: str, config: Dict[str, str]) -> int:
    key = {
        "gemini": "GEMINI_DAILY_LIMIT",
        "groq": "GROQ_DAILY_LIMIT",
        "openrouter": "OPENROUTER_DAILY_LIMIT",
    }.get(provider)

    if not key:
        return 0

    return int_value(config.get(key), 0)

def provider_available(provider: str, config: Dict[str, str]) -> Dict[str, Any]:
    key = {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider)

    model_key = {
        "gemini": "GEMINI_MODEL",
        "groq": "GROQ_MODEL",
        "openrouter": "OPENROUTER_MODEL",
    }.get(provider)

    configured = bool(config.get(key or ""))
    model = config.get(model_key or "") or ""
    counts = usage_counts()
    current = counts["by_provider"].get(provider, 0)
    limit = provider_daily_limit(provider, config)

    return {
        "provider": provider,
        "configured": configured,
        "model": model,
        "today_used": current,
        "daily_limit": limit,
        "remaining": max(0, limit - current),
        "usable": configured and bool(model) and current < limit,
    }

def providers() -> Dict[str, Any]:
    config = cfg()
    names = ["gemini", "groq", "openrouter"]
    items = [provider_available(name, config) for name in names]
    counts = usage_counts()

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.23-free-cloud-brain-broker",
        "allow_send": bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND")),
        "mode": config.get("EZZIO_CLOUD_MODE"),
        "usage": counts,
        "daily_total_limit": int_value(config.get("EZZIO_CLOUD_DAILY_TOTAL_LIMIT"), 120),
        "providers": items,
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
    data = providers()
    cache_files = list(CACHE_ROOT.glob("*.json"))

    data.update({
        "secrets_path": str(SECRETS_PATH),
        "state_root": str(STATE_ROOT),
        "cache_count": len(cache_files),
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

def redact_text(text: str) -> str:
    cleaned = text or ""
    patterns = [
        r"sk-[A-Za-z0-9_\-]{12,}",
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"gsk_[A-Za-z0-9_\-]{20,}",
        r"or-[A-Za-z0-9_\-]{20,}",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+",
    ]

    for pattern in patterns:
        cleaned = re.sub(pattern, "[REDACTED_SECRET]", cleaned)

    return cleaned

def cache_key(provider: str, model: str, text: str, system: str) -> str:
    payload = json.dumps({
        "provider": provider,
        "model": model,
        "text": text,
        "system": system,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def cache_get(key: str, ttl_sec: int) -> Optional[Dict[str, Any]]:
    path = CACHE_ROOT / f"{key}.json"

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        created_at_epoch = float(data.get("_created_at_epoch", 0))
        if time.time() - created_at_epoch > ttl_sec:
            return None
        data["cache_hit"] = True
        return data
    except Exception:
        return None

def cache_set(key: str, data: Dict[str, Any]) -> None:
    path = CACHE_ROOT / f"{key}.json"
    clone = dict(data)
    clone["_created_at_epoch"] = time.time()
    path.write_text(json.dumps(clone, ensure_ascii=False, indent=2), encoding="utf-8")

def record_usage(provider: str, model: str, ok: bool) -> None:
    append_jsonl(USAGE_PATH, {
        "day": today(),
        "provider": provider,
        "model": model,
        "ok": ok,
    })

def allowed_to_send(provider: str, config: Dict[str, str]) -> Tuple[bool, str]:
    if not bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND")):
        return False, "cloud_send_disabled"

    counts = usage_counts()
    total_limit = int_value(config.get("EZZIO_CLOUD_DAILY_TOTAL_LIMIT"), 120)

    if counts["total_today"] >= total_limit:
        return False, "daily_total_limit_reached"

    availability = provider_available(provider, config)

    if not availability["configured"]:
        return False, "provider_key_missing"

    if not availability["model"]:
        return False, "provider_model_missing"

    if availability["remaining"] <= 0:
        return False, "provider_daily_limit_reached"

    return True, "ok"

def http_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout_sec: int) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": response.status,
                "json": json.loads(raw),
                "raw": raw[:2000],
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "error": raw[:2000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": str(exc),
        }

def call_gemini(text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    provider = "gemini"
    model = config.get("GEMINI_MODEL") or "gemini-2.0-flash"
    key = config.get("GEMINI_API_KEY") or ""
    timeout_sec = int_value(config.get("EZZIO_CLOUD_TIMEOUT_SEC"), 60)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    prompt = f"{system}\n\n{text}".strip()
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 700,
        },
    }

    response = http_json(
        url=url,
        headers={"Content-Type": "application/json"},
        payload=payload,
        timeout_sec=timeout_sec,
    )

    if not response.get("ok"):
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "error": response.get("error"),
            "status": response.get("status"),
        }

    data = response.get("json") or {}
    text_out = ""

    try:
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", [])
        text_out = "".join(part.get("text", "") for part in parts)
    except Exception:
        text_out = ""

    return {
        "ok": bool(text_out),
        "provider": provider,
        "model": model,
        "reply": text_out.strip(),
        "raw_status": response.get("status"),
    }

def call_openai_compatible(provider: str, base_url: str, api_key: str, model: str, text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    timeout_sec = int_value(config.get("EZZIO_CLOUD_TIMEOUT_SEC"), 60)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    if provider == "openrouter":
        site_url = config.get("OPENROUTER_SITE_URL") or "http://127.0.0.1:8000"
        app_name = config.get("OPENROUTER_APP_NAME") or "E-ZZIO"
        headers["HTTP-Referer"] = site_url
        headers["X-Title"] = app_name

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }

    response = http_json(
        url=base_url.rstrip("/") + "/chat/completions",
        headers=headers,
        payload=payload,
        timeout_sec=timeout_sec,
    )

    if not response.get("ok"):
        return {
            "ok": False,
            "provider": provider,
            "model": model,
            "status": response.get("status"),
            "error": response.get("error"),
        }

    data = response.get("json") or {}
    reply = ""

    try:
        choices = data.get("choices") or []
        reply = choices[0].get("message", {}).get("content", "")
    except Exception:
        reply = ""

    return {
        "ok": bool(reply),
        "provider": provider,
        "model": model,
        "reply": reply.strip(),
        "raw_status": response.get("status"),
    }

def call_provider(provider: str, text: str, system: str, config: Dict[str, str]) -> Dict[str, Any]:
    allowed, reason = allowed_to_send(provider, config)

    if not allowed:
        return {
            "ok": False,
            "provider": provider,
            "blocked": True,
            "reason": reason,
        }

    clean_text = redact_text(text) if bool_value(config.get("EZZIO_CLOUD_REDACT_SECRETS")) else text
    clean_system = redact_text(system) if bool_value(config.get("EZZIO_CLOUD_REDACT_SECRETS")) else system

    if provider == "gemini":
        result = call_gemini(clean_text, clean_system, config)
    elif provider == "groq":
        result = call_openai_compatible(
            provider="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=config.get("GROQ_API_KEY") or "",
            model=config.get("GROQ_MODEL") or "",
            text=clean_text,
            system=clean_system,
            config=config,
        )
    elif provider == "openrouter":
        result = call_openai_compatible(
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=config.get("OPENROUTER_API_KEY") or "",
            model=config.get("OPENROUTER_MODEL") or "",
            text=clean_text,
            system=clean_system,
            config=config,
        )
    else:
        result = {
            "ok": False,
            "provider": provider,
            "error": "unknown_provider",
        }

    record_usage(provider=provider, model=result.get("model", ""), ok=bool(result.get("ok")))

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
    usable = [item["provider"] for item in providers()["providers"] if item.get("usable")]

    return [provider for provider in order if provider in usable] + [provider for provider in order if provider not in usable]

def default_system() -> str:
    return (
        "Tu es le cerveau cloud optionnel d'E-ZZIO. "
        "Réponds en français. Sois précis, utile, sobre et professionnel. "
        "Respecte local-first, CPU/RAM only, GPU untouched, zéro publicité, zéro tracking. "
        "Ne prétends pas pouvoir agir sur le PC : E-ZZIO local garde le contrôle des actions."
    )

def cloud_chat(text: str, provider: str = "auto", system: str = "", use_cache: bool = True) -> Dict[str, Any]:
    started = time.time()
    config = cfg()
    system_prompt = system.strip() or default_system()
    ttl = int_value(config.get("EZZIO_CLOUD_CACHE_TTL_SEC"), 86400)
    selected = choose_providers(config, prefer=provider)

    attempts = []

    for name in selected:
        model = {
            "gemini": config.get("GEMINI_MODEL") or "",
            "groq": config.get("GROQ_MODEL") or "",
            "openrouter": config.get("OPENROUTER_MODEL") or "",
        }.get(name, "")

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
                "version": "v2.23-free-cloud-brain-broker",
                "provider": name,
                "model": result.get("model"),
                "reply": result.get("reply"),
                "attempts": attempts,
                "elapsed_ms": int((time.time() - started) * 1000),
                "cache_hit": False,
                "policy": {
                    "cloud_optional": True,
                    "local_controls_actions": True,
                    "secrets_redacted": True,
                    "gpu": "untouched",
                    "no_ads": True,
                },
            }

            if use_cache:
                cache_set(key, output)

            return output

    return {
        "ok": False,
        "created_at": now(),
        "version": "v2.23-free-cloud-brain-broker",
        "provider": None,
        "model": None,
        "reply": "Aucun fournisseur cloud gratuit disponible ou autorisé. Fallback local recommandé.",
        "attempts": attempts,
        "elapsed_ms": int((time.time() - started) * 1000),
        "cache_hit": False,
    }

def hybrid_chat(text: str, provider: str = "auto", force_cloud: bool = False) -> Dict[str, Any]:
    low = (text or "").lower()

    wants_cloud = force_cloud or any(word in low for word in [
        "cloud",
        "api",
        "raisonnement profond",
        "analyse complexe",
        "modèle externe",
        "cherche avec api",
        "cerveau externe",
    ])

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
        return {
            "ok": False,
            "version": "v2.23-free-cloud-brain-broker",
            "mode": "error",
            "reply": f"Erreur fallback local : {exc}",
            "error": str(exc),
        }

def route(text: str, provider: str = "auto") -> Dict[str, Any]:
    config = cfg()
    data = providers()
    low = (text or "").lower()

    cloud_reason = []
    if any(word in low for word in ["cloud", "api", "raisonnement profond", "analyse complexe", "gros code", "long contexte"]):
        cloud_reason.append("demande_complexe_ou_cloud")

    if any(word in low for word in ["secret", "clé api", "token", "password", "mot de passe"]):
        cloud_reason.append("secret_detected_prefer_local")

    allow_send = bool_value(config.get("EZZIO_CLOUD_ALLOW_SEND"))

    decision = "local"
    if cloud_reason and "secret_detected_prefer_local" not in cloud_reason and allow_send:
        decision = "cloud"

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.23-free-cloud-brain-broker",
        "decision": decision,
        "reasons": cloud_reason or ["local_first_default"],
        "allow_send": allow_send,
        "providers": data.get("providers"),
        "policy": {
            "local_first": True,
            "cloud_optional": True,
            "secret_redaction": True,
            "no_ads": True,
            "gpu": "untouched",
        },
    }
