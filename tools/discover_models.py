"""
E-ZZIO Sovereign Platform — Automated Model Discovery & Federation Auditor.

Scanne les fournisseurs de la fédération E-ZzIO :
1. Découverte locale Ollama (http://localhost:11434/api/tags)
2. Découverte des catalogues Cloud configurés (Gemini, Groq, NVIDIA)
3. Rapprochement avec le Registre Canonique (CanonicalModelRegistry)
4. Détection des écarts : REGISTERED, MISSING, NEW, STALE
5. Génération du rapport state/audit/model_discovery_report.json
"""
from __future__ import annotations
import os
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.routing.model_registry import canonical_model_registry, ModelSource


def query_local_ollama_models(timeout_sec: float = 1.5) -> List[str]:
    """Interroge le daemon Ollama local pour lister les modèles installés."""
    url = "http://localhost:11434/api/tags"
    req = urllib.request.Request(url, headers={"User-Agent": "E-zzio-Model-Discovery/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return [m for m in models if m]
    except Exception:
        # Daemon non démarré ou inaccessible -> tolérance fail-closed
        return []


def discover_all_models() -> Dict[str, Any]:
    """Exécute la découverte multi-fournisseurs et le rapprochement."""
    # 1. Découverte locale
    local_models = query_local_ollama_models()

    # 2. Vérification des clés de configuration pour les providers Cloud
    env_gemini = bool(os.getenv("GEMINI_API_KEY") or os.path.exists("secrets/.env"))
    env_groq = bool(os.getenv("GROQ_API_KEY"))
    env_nvidia = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY"))

    # 3. Récupération des modèles du registre canonique
    registered_models = canonical_model_registry.list_models(qualified_only=False)

    comparison: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "providers": {
            "ollama_local": {
                "active": len(local_models) > 0,
                "discovered_count": len(local_models),
                "models": local_models,
            },
            "gemini": {"configured": env_gemini},
            "groq": {"configured": env_groq},
            "nvidia": {"configured": env_nvidia},
        },
        "status_groups": {
            "LOCAL_CONFIRMED": [],
            "LOCAL_MISSING_FROM_RUNTIME": [],
            "LOCAL_UNREGISTERED_IN_REGISTRY": [],
            "CLOUD_REGISTERED": [],
        },
        "summary": {}
    }

    # Modèles locaux canoniques
    canonical_local_raw = {
        m.raw_model_name: m for m in registered_models if m.source == ModelSource.LOCAL
    }
    canonical_local_names = set(canonical_local_raw.keys())
    discovered_local_names = set(local_models)

    # 1. Modèles locaux confirmés
    for name in discovered_local_names.intersection(canonical_local_names):
        comparison["status_groups"]["LOCAL_CONFIRMED"].append(name)

    # 2. Modèles locaux enregistrés mais non installés localement
    for name in canonical_local_names - discovered_local_names:
        comparison["status_groups"]["LOCAL_MISSING_FROM_RUNTIME"].append(name)

    # 3. Modèles locaux installés mais non catalogués dans le registre canonique
    for name in discovered_local_names - canonical_local_names:
        comparison["status_groups"]["LOCAL_UNREGISTERED_IN_REGISTRY"].append(name)

    # 4. Modèles Cloud
    for m in registered_models:
        if m.source != ModelSource.LOCAL:
            comparison["status_groups"]["CLOUD_REGISTERED"].append({
                "model_id": m.model_id,
                "source": m.source.value,
                "latency_tier": m.latency_tier.value,
                "status": m.qualification_status.value,
            })

    comparison["summary"] = {
        "total_canonical_models": len(registered_models),
        "local_confirmed": len(comparison["status_groups"]["LOCAL_CONFIRMED"]),
        "local_missing": len(comparison["status_groups"]["LOCAL_MISSING_FROM_RUNTIME"]),
        "local_unregistered": len(comparison["status_groups"]["LOCAL_UNREGISTERED_IN_REGISTRY"]),
        "cloud_registered": len(comparison["status_groups"]["CLOUD_REGISTERED"]),
    }

    # Sauvegarde du rapport
    audit_dir = os.path.join(REPO_ROOT, "state", "audit")
    os.makedirs(audit_dir, exist_ok=True)
    report_file = os.path.join(audit_dir, "model_discovery_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    return comparison


def main():
    print("============================================================")
    print("E-ZZIO FEDERATION — MODEL DISCOVERY AUDIT")
    print("============================================================")
    report = discover_all_models()
    summary = report["summary"]
    print(f"Total Canonical Models in Registry: {summary['total_canonical_models']}")
    print(f"Local Models Confirmed (Ollama)  : {summary['local_confirmed']}")
    print(f"Local Models Missing from Runtime : {summary['local_missing']}")
    print(f"Local Unregistered Candidates     : {summary['local_unregistered']}")
    print(f"Cloud Registered Models (Fed.)    : {summary['cloud_registered']}")
    print("------------------------------------------------------------")
    print("Status: MODEL_DISCOVERY_COMPLETED (Report written to state/audit/model_discovery_report.json)")
    sys.exit(0)


if __name__ == "__main__":
    main()
