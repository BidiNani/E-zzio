import os
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def fetch_ollama_models():
    """Interroge l'API locale Ollama pour obtenir la liste exacte des modèles installés."""
    url = "http://localhost:11434/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "E-ZZIO-Reconciler"})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"[!] Avertissement : Impossible de joindre l'API Ollama ({str(e)}). Utilisation du cache ou mode dégradé.")
        return []

def run_reconciliation():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.15 — Réconciliation Ollama <-> Registre Interne...")
    print("[*] -----------------------------------------------------------------")

    installed_models = fetch_ollama_models()
    print(f"  [OK] Modèles Ollama détectés en direct : {installed_models}")

    # Chargement du registre statique actuel (core/model_registry.py ou équivalent)
    # Pour l'instant, on audite les pools déclarés connus
    static_declared = {
        "fast": ["llama3.2:3b", "phi4-mini:latest"],
        "normal": ["hermes3:8b", "qwen2.5-coder:7b"],
        "deep": ["qwen2.5-coder:7b"]
    }

    reconciliation_matrix = {}
    all_declared = set(m for group in static_declared.values() for m in group)
    installed_set = set(installed_models)

    # Analyse des écarts
    matched = all_declared.intersection(installed_set)
    phantom_models = all_declared - installed_set # Déclarés mais absents d'Ollama
    unregistered_installed = installed_set - all_declared # Présents mais non déclarés dans le pool statique

    matrix_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ollama_live_models": installed_models,
        "statically_declared": list(all_declared),
        "matched_and_ready": list(matched),
        "phantom_models_risk": list(phantom_models),
        "unregistered_discovered": list(unregistered_installed),
        "sync_status": "ALIGNED_WITH_WARNINGS" if phantom_models else "PERFECT_SYNCHRONIZATION"
    }

    report_path = REGISTRY_OUT / "model_reconciliation_report.json"
    report_path.write_text(json.dumps(matrix_report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"  [OK] Rapport de réconciliation généré : {report_path.name}")
    print(f"  [STATUS] Statut de synchro : {matrix_report['sync_status']}")
    if phantom_models:
        print(f"  [!] Modèles fantômes détectés (nécessitent un fallback) : {phantom_models}")
    if unregistered_installed:
        print(f"  [i] Modèles non enregistrés mais exploitables : {unregistered_installed}")

if __name__ == "__main__":
    run_reconciliation()
