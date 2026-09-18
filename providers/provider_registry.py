"""
E-ZZIO V7.23.0.6 — Dynamic Provider Registry & Telemetry Fusion
Fusionne provider_capabilities.json et provider_performance.json.
Calcule un score de santé et de performance dynamique tout en vérifiant
l'autorisation Cloud (cloud_guard / EZZIO_CLOUD_ALLOW_SEND).
Expose des contrats standardisés pour le futur Unified Intelligence Router.
"""

import json
import os
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
CAPABILITIES_PATH = ROOT_DIR / "runtime" / "models" / "provider_capabilities.json"
PERFORMANCE_PATH = ROOT_DIR / "runtime" / "metrics" / "provider_performance.json"


def _is_cloud_authorized() -> bool:
    """Vérifie si l'émission cloud est globalement autorisée."""
    allow = os.getenv("EZZIO_CLOUD_ALLOW_SEND", "true").lower()
    return allow in ["true", "1", "yes"]


def _load_capabilities() -> dict:
    if CAPABILITIES_PATH.exists():
        try:
            return json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8")).get("providers", {})
        except Exception:
            pass
    return {}


def _load_performance() -> dict:
    if PERFORMANCE_PATH.exists():
        try:
            return json.loads(PERFORMANCE_PATH.read_text(encoding="utf-8")).get("providers", {})
        except Exception:
            pass
    return {}


def calculate_provider_score(provider_name: str, capability: str) -> float:
    """
    Calcule le score dynamique d'un fournisseur pour une capacité donnée.
    Pondération :
    - Capability Match : 40%
    - Taux de Succès  : 30%
    - Score Latence   : 20%
    - Quota / Dispo   : 10%
    """
    caps = _load_capabilities().get(provider_name, {})
    perf = _load_performance().get(provider_name, {})

    if not caps.get("enabled", False) or not perf.get("quota_available", True):
        return 0.0

    # 1. Capability Match (40 pts)
    roles = caps.get("roles", [])
    cap_score = 40.0 if capability in roles else 10.0

    # 2. Success Rate (30 pts)
    success_rate = perf.get("success_rate", 1.0)
    succ_score = success_rate * 30.0

    # 3. Latency Score (20 pts - Référence : 500ms = 20pts, 5000ms = 0pts)
    avg_lat = perf.get("avg_latency_ms", 1000.0)
    lat_score = max(0.0, 20.0 - (avg_lat / 250.0))

    # 4. Quota / Dispo (10 pts)
    quota_score = 10.0 if perf.get("quota_available", True) else 0.0

    return round(cap_score + succ_score + lat_score + quota_score, 2)


def get_provider_contract(provider_name: str) -> dict:
    """
    Expose le contrat standardisé pour un fournisseur à destination du Router.
    """
    caps = _load_capabilities().get(provider_name, {})
    perf = _load_performance().get(provider_name, {})
    authorized = _is_cloud_authorized()

    enabled = caps.get("enabled", False)
    quota_avail = perf.get("quota_available", True)

    return {
        "provider": provider_name,
        "enabled": enabled,
        "authorized": authorized,
        "quota_available": quota_avail,
        "usable": enabled and authorized and quota_avail,
        "default_model": caps.get("default_model", "auto"),
        "capabilities": caps.get("roles", []),
        "avg_latency_ms": perf.get("avg_latency_ms", 0.0),
        "success_rate": perf.get("success_rate", 1.0),
        "tier": caps.get("tier", "cloud"),
    }


def get_best_provider(capability: str) -> dict:
    """
    Détermine le meilleur fournisseur cloud utilisable pour une capacité demandée.
    """
    caps = _load_capabilities()
    authorized = _is_cloud_authorized()

    if not authorized:
        return {"provider": "none", "usable": False, "reason": "Cloud globalement non autorisé (EZZIO_CLOUD_ALLOW_SEND=false)"}

    scored_providers = []
    for p in caps.keys():
        contract = get_provider_contract(p)
        if contract["usable"]:
            score = calculate_provider_score(p, capability)
            scored_providers.append((p, score, contract))

    if not scored_providers:
        return {"provider": "none", "usable": False, "reason": "Aucun fournisseur cloud utilisable ou quotas épuisés"}

    # Tri par score décroissant
    scored_providers.sort(key=lambda x: x[1], reverse=True)
    best_p, best_score, best_contract = scored_providers[0]

    best_contract["selection_score"] = best_score
    return best_contract


if __name__ == "__main__":
    print("[E-ZZIO V7.23.0.6] Dynamic Provider Registry Fusion Test:")
    print(" 1. Contrat Gemini :", get_provider_contract("gemini"))
    print(" 2. Contrat Groq   :", get_provider_contract("groq"))
    print("\n 3. Sélection dynamique 'vision'      ->", get_best_provider("vision"))
    print(" 4. Sélection dynamique 'fast_chat'   ->", get_best_provider("fast_chat"))
    print(" 5. Sélection dynamique 'architecture' ->", get_best_provider("architecture"))

_instances = {}


def get_provider_instance(name: str):
    """Factory d'inversion de dépendance pour l'Intelligence Router."""
    global _instances
    if name not in _instances:
        if name == "gemini":
            from providers.gemini_provider import GeminiProvider

            _instances[name] = GeminiProvider()
        elif name == "groq":
            from providers.groq_provider import GroqProvider

            _instances[name] = GroqProvider()
        elif name == "ollama":
            from providers.ollama_provider import OllamaProvider

            _instances[name] = OllamaProvider()
    return _instances.get(name)
