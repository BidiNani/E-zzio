"""E-ZZIO Cloud Brain Broker — Canonical Cloud Execution Authority with Identity Cache & Streaming."""
from __future__ import annotations
import json
import urllib.request
from typing import Any, Dict, Generator
from core.identity.canonical_identity import CanonicalIdentity
from core.security.unified_vault import key_vault

TARGET_MODEL = "gemini-3.7-flash"

# Cache global du socle identitaire pour éliminer les I/O disque par requête
_CACHED_SYSTEM_PROMPT: str | None = None


def build_system_prompt() -> str:
    """L'identité système provient exclusivement de CanonicalIdentity avec cache mémorisé."""
    global _CACHED_SYSTEM_PROMPT
    if _CACHED_SYSTEM_PROMPT is None:
        _CACHED_SYSTEM_PROMPT = CanonicalIdentity().build_system_prompt()
    return _CACHED_SYSTEM_PROMPT


def _fail_closed(message: str) -> Dict[str, Any]:
    return {
        "response": message,
        "answer": message,
        "message": message,
        "content": message,
        "reply": message,
        "model": "none",
        "primary_model": "none",
        "deep_model": "none",
        "attempted_models": [],
        "fallback_models": [],
        "used_fallback": False,
        "route_score": 0,
        "route_hits": ["cloud_fail_closed"],
        "gpu_policy": "disabled_for_ezzio",
        "num_gpu": 0,
        "ok": False,
    }


def _get_gemini_keys() -> list[str]:
    """Récupère exclusivement les clés Gemini du Vault."""
    try:
        keys = key_vault.get_all_keys_for_provider("gemini")
    except Exception as exc:
        raise RuntimeError(
            f"[FAIL-CLOSED] Impossible d'interroger le Vault Gemini : {exc}"
        ) from exc
    if not keys:
        raise RuntimeError(
            "[SECURITY FAIL-CLOSED] Aucune clé GEMINI valide dans le Vault."
        )
    return [str(k).strip() for k in keys if str(k).strip()]


def cloud_chat(
    text: str,
    session_id: str = "",
    system_prompt: str = "",
    speed: str = "fast",
) -> Dict[str, Any]:
    """Exécution Cloud canonique synchrone (non-streamé)."""
    if not text or not str(text).strip():
        return _fail_closed("[FAIL-CLOSED] Requête vide refusée.")

    try:
        keys = _get_gemini_keys()
    except Exception as exc:
        return _fail_closed(str(exc))

    canonical_prompt = system_prompt.strip() or build_system_prompt()
    last_error = ""

    for key in keys:
        payload = {
            "system_instruction": {
                "parts": [{"text": canonical_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": str(text)}]
                }
            ]
        }

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{TARGET_MODEL}:generateContent?key={key}"
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            data = json.loads(raw)
            candidates = data.get("candidates") or []
            if not candidates:
                last_error = "Gemini n'a retourné aucun candidate."
                continue

            candidate = candidates[0] or {}
            parts = candidate.get("content", {}).get("parts", [])
            answer_parts = [str(p.get("text", "")) for p in parts if isinstance(p, dict) and p.get("text")]
            message = "".join(answer_parts).strip()

            if not message:
                last_error = "Gemini a retourné une réponse vide."
                continue

            return {
                "response": message,
                "answer": message,
                "content": message,
                "message": message,
                "reply": message,
                "source": "Gemini 3.5 Flash-Lite",
                "authority": "CanonicalIdentity",
                "provider": "gemini",
                "model": TARGET_MODEL,
                "primary_model": TARGET_MODEL,
                "deep_model": TARGET_MODEL,
                "attempted_models": [TARGET_MODEL],
                "fallback_models": [],
                "used_fallback": False,
                "route_hits": ["gemini_monomodel_strict", "canonical_identity", "fail_closed"],
                "gpu_policy": "disabled_for_ezzio",
                "num_gpu": 0,
                "ok": True,
            }
        except Exception as exc:
            last_error = str(exc)
            continue

    return _fail_closed(f"[FAIL-CLOSED] Gemini unavailable : {last_error}")


def cloud_stream_chat(
    text: str,
    session_id: str = "",
    system_prompt: str = "",
    speed: str = "fast",
) -> Generator[str, None, None]:
    """Exécution Cloud en streaming SSE (Server-Sent Events) optimisée TTFB."""
    if not text or not str(text).strip():
        yield "[FAIL-CLOSED] Requête vide refusée."
        return

    try:
        keys = _get_gemini_keys()
    except Exception as exc:
        yield f"[FAIL-CLOSED] {exc}"
        return

    canonical_prompt = system_prompt.strip() or build_system_prompt()

    for key in keys:
        payload = {
            "system_instruction": {
                "parts": [{"text": canonical_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": str(text)}]
                }
            ]
        }

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{TARGET_MODEL}:streamGenerateContent?alt=sse&key={key}"
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as resp:
                for line in resp:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if line_str.startswith("data: "):
                        json_str = line_str[6:]
                        try:
                            chunk_data = json.loads(json_str)
                            candidates = chunk_data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    if isinstance(p, dict) and p.get("text"):
                                         yield p["text"]
                        except json.JSONDecodeError:
                            continue
            return
        except Exception:
            continue

    yield "[FAIL-CLOSED] Streaming indisponible : épuisement du pool multi-clés."
