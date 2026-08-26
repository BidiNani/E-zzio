"""Broker Cloud centralisé - Mono-Modèle Stricte (gemini-3.5-flash-lite) & Multi-Key Fail-Closed."""

import json
import urllib.request
from typing import Any, Dict
from core.security.unified_vault import key_vault

# RÈGLE ABSOLUE : Modèle unique autorisé. Zéro cascade vers d'autres modèles.
TARGET_MODEL = "gemini-3.5-flash-lite"

def build_system_prompt() -> str:
    return (
        "[DIRECTIVE SYSTÈMES E-ZZIO]\n"
        "- TON IDENTITÉ : Tu es E-ZZIO, l'intelligence centrale et complice conçue par BidiNani (Enrik).\n"
        "- TON INTERLOCUTEUR : Tu t'adresses UNIQUEMENT à ton créateur, BidiNani.\n"
        "- RÈGLES DE STYLE : Direct, technique, complice, vif, en français naturel et impeccable.\n"
        "- INTERDICTIONS STRICTES : Ne te présente jamais comme un 'cerveau cloud optionnel' et ne récite aucun disclaimer."
    )

def cloud_chat(text: str, session_id: str = "", system_prompt: str = "", speed: str = "fast") -> Dict[str, Any]:
    sys_p = system_prompt or build_system_prompt()
    
    # Récupération de toutes les clés disponibles dans le Vault multi-clés
    keys = key_vault.get_all_keys_for_provider("gemini")
    
    if not keys:
        err = "[FAIL-CLOSED] Gemini unavailable : Aucune clé Gemini valide trouvée dans le Vault multi-clés."
        return {
            "response": err, "answer": err, "message": err, "content": err,
            "model": "none", "primary_model": "none", "deep_model": "none",
            "attempted_models": [], "fallback_models": [], "used_fallback": False, "ok": False
        }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"Instructions :\n{sys_p}\n\nRequête :\n{text}"}]}]
    }
    data = json.dumps(payload).encode("utf-8")

    # Rotation exclusive sur les clés du Vault avec TARGET_MODEL uniquement (Pas de cascade)
    for key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{TARGET_MODEL}:generateContent?key={key}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = "".join(p.get("text", "") for p in parts).strip()
                    if reply:
                        return {
                            "response": reply,
                            "answer": reply,
                            "message": reply,
                            "content": reply,
                            "model": TARGET_MODEL,
                            "primary_model": TARGET_MODEL,
                            "deep_model": TARGET_MODEL,
                            "attempted_models": [TARGET_MODEL],
                            "fallback_models": [],
                            "used_fallback": False,
                            "route_score": 100,
                            "route_hits": ["gemini_monomodel_strict"],
                            "gpu_policy": "disabled_for_ezzio",
                            "num_gpu": 0,
                            "ok": True
                        }
        except Exception:
            # Échec sur cette clé -> passage à la clé suivante du Vault
            continue

    # Si toutes les clés du Vault échouent sur gemini-3.5-flash-lite -> FAIL-CLOSED STRICT
    fail_msg = f"[FAIL-CLOSED] Gemini unavailable : Épuisement du pool multi-clés sur {TARGET_MODEL}. Aucune inférence locale autorisée."
    return {
        "response": fail_msg,
        "answer": fail_msg,
        "message": fail_msg,
        "content": fail_msg,
        "model": "none",
        "primary_model": "none",
        "deep_model": "none",
        "attempted_models": [],
        "fallback_models": [],
        "used_fallback": False,
        "ok": False
    }
