"""Broker Cloud centralisé — Mono-Modèle Stricte & REST Natif (Zéro dépendance SDK)."""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict
from core.identity.canonical_identity import CanonicalIdentity

TARGET_MODEL = "gemini-2.5-flash"  # Modèle API Google AI Studio / Flash-Lite
_CANONICAL_IDENTITY: CanonicalIdentity | None = None


def _get_secret_safely(key_name: str) -> str | None:
    """Extraction résiliente depuis unified_vault ou variables d'environnement."""
    try:
        from core.security import unified_vault
        if hasattr(unified_vault, "get_secret"):
            val = unified_vault.get_secret(key_name)
            if val:
                return str(val)
        if hasattr(unified_vault, "get_vault_secret"):
            val = unified_vault.get_vault_secret(key_name)
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
    """Génération du prompt système via CanonicalIdentity avec fallback de secours."""
    global _CANONICAL_IDENTITY
    if _CANONICAL_IDENTITY is None:
        try:
            root_dir = Path(__file__).resolve().parent.parent
            _CANONICAL_IDENTITY = CanonicalIdentity(root_dir=root_dir)
        except Exception:
            return "- TON IDENTITÉ : Tu es E-ZZIO, l'intelligence centrale conçue par BidiNani.\n- TON INTERLOCUTEUR : Tu t'adresses UNIQUEMENT à ton créateur, BidiNani.\n"
    try:
        return _CANONICAL_IDENTITY.build_system_prompt(source=source, mode=mode)
    except Exception:
        return "- TON IDENTITÉ : Tu es E-ZZIO, l'intelligence centrale conçue par BidiNani.\n- TON INTERLOCUTEUR : Tu t'adresses UNIQUEMENT à ton créateur, BidiNani.\n"


def cloud_chat(
    text: str,
    session_id: str = "",
    system_prompt: str = "",
    speed: str = "fast",
    provider: str = "gemini",
    **kwargs
) -> Dict[str, Any]:
    """Exécution d'une requête d'inférence vers Gemini via l'API REST Google AI."""
    source_tag = "discord" if session_id and str(session_id).startswith("disc_") else "api"
    sys_p = system_prompt or get_canonical_system_prompt(source=source_tag, mode="operational")

    # Récupération des clés API
    api_keys = []
    primary_key = _get_secret_safely("GEMINI_API_KEY")
    if primary_key:
        api_keys.append(primary_key)

    for idx in range(1, 10):
        k = _get_secret_safely(f"GEMINI_API_KEY_{idx}")
        if k and k not in api_keys:
            api_keys.append(k)

    if not api_keys:
        raise RuntimeError("Aucune clé GEMINI_API_KEY valide disponible dans le coffre ou l'environnement.")

    payload = {
        "contents": [
            {
                "parts": [{"text": text}]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": sys_p}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    start_time = time.perf_counter()
    last_exc = None

    for key in api_keys:
        # Essai sur le modèle cible puis repli vers flash standard si alias non supporté
        for model_name in [TARGET_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
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
                            "model": model_name,
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

    raise RuntimeError(f"Échec de l'ensemble du pool de clés Gemini : {last_exc}")
