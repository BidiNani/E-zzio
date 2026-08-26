"""Broker Cloud centralisé — Consommateur d'Inférence & Canonical Identity Fail-Closed."""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict
from core.identity.canonical_identity import CanonicalIdentity

_CANONICAL_IDENTITY: CanonicalIdentity | None = None


def _get_secret_safely(key_name: str) -> str | None:
    try:
        from core.security import unified_vault
        for getter in ["get_secret", "get_vault_secret"]:
            if hasattr(unified_vault, getter):
                val = getattr(unified_vault, getter)(key_name)
                if val:
                    return str(val)
        if hasattr(unified_vault, "vault") and hasattr(unified_vault.vault, "get_secret"):
            val = unified_vault.vault.get_secret(key_name)
            if val:
                return str(val)
    except Exception:
        pass
    return os.getenv(key_name)


def get_canonical_system_prompt(source: str = "api", mode: str = "operational") -> str:
    """Règle Fail-Closed stricte : l'identité provient exclusivement de CanonicalIdentity."""
    global _CANONICAL_IDENTITY
    if _CANONICAL_IDENTITY is None:
        try:
            root_dir = Path(__file__).resolve().parent.parent
            _CANONICAL_IDENTITY = CanonicalIdentity(root_dir=root_dir)
        except Exception as exc:
            raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Initialisation de CanonicalIdentity impossible : {exc}") from exc

    try:
        return _CANONICAL_IDENTITY.build_system_prompt(source=source, mode=mode)
    except Exception as exc:
        raise RuntimeError(f"[IDENTITY FAIL-CLOSED] Échec de génération du prompt canonique : {exc}") from exc


def cloud_chat(
    text: str,
    session_id: str = "",
    system_prompt: str = "",
    model: str = "gemini-2.5-flash",
    speed: str = "fast",
    provider: str = "gemini",
    **kwargs
) -> Dict[str, Any]:
    """Exécute l'inférence avec l'identité canonique imposée (aucune substitution permise)."""
    source_tag = "discord" if session_id and str(session_id).startswith("disc_") else "api"
    sys_p = get_canonical_system_prompt(source=source_tag, mode="operational")

    api_keys = []
    primary_key = _get_secret_safely("GEMINI_API_KEY")
    if primary_key:
        api_keys.append(primary_key)

    for idx in range(1, 10):
        k = _get_secret_safely(f"GEMINI_API_KEY_{idx}")
        if k and k not in api_keys:
            api_keys.append(k)

    if not api_keys:
        raise RuntimeError("[SECURITY FAIL-CLOSED] Aucune clé GEMINI_API_KEY valide dans le coffre.")

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "systemInstruction": {"parts": [{"text": sys_p}]},
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    start_time = time.perf_counter()
    last_exc = None

    for key in api_keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                    candidates = data.get("candidates", [])
                    reply = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        reply = "".join(p.get("text", "") for p in parts)

                    return {
                        "response": reply.strip(),
                        "answer": reply.strip(),
                        "content": reply.strip(),
                        "message": reply.strip(),
                        "model": model,
                        "elapsed_ms": elapsed_ms,
                        "ok": True,
                        "used_fallback": False,
                    }
        except urllib.error.HTTPError as http_err:
            last_exc = f"HTTP {http_err.code}: {http_err.read().decode('utf-8', errors='ignore')}"
            continue
        except Exception as exc:
            last_exc = str(exc)
            continue

    raise RuntimeError(f"[BROKER FAIL-CLOSED] Échec d'exécution sur le modèle {model} : {last_exc}")
