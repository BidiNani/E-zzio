"""
runtime/audit/v722_runtime_probe.py — Sonde de Télémétrie Réelle V7.22
Interroge chaque modèle actif d'Ollama, mesure la latence d'exécution (ms)
et met à jour dynamiquement model_performance.json.
"""
import time
import json
import ollama
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
CAPABILITIES_PATH = ROOT_DIR / "runtime" / "models" / "model_capabilities.json"
METRICS_PATH = ROOT_DIR / "runtime" / "metrics" / "model_performance.json"

def run_runtime_probe():
    print("[*] -----------------------------------------------------------------")
    print("[*] E-ZZIO V7.22 — Exécution du Model Runtime Probe...")
    print("[*] -----------------------------------------------------------------")

    if not CAPABILITIES_PATH.exists():
        print("[!] Erreur : model_capabilities.json introuvable.")
        return

    caps_data = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))
    models = list(caps_data.get("models", {}).keys())

    # Chargement ou initialisation des métriques existantes
    metrics_data = {"schema_version": "V1.0-TELEMETRY", "models": {}}
    if METRICS_PATH.exists():
        try:
            metrics_data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    test_prompt = "Ping. Reply with OK."

    for model_name in models:
        print(f"  [SONDE] Test du modèle : {model_name}...", end="", flush=True)
        
        # Isolation du modèle d'embedding (ne supporte pas le chat textuel de la même manière)
        if "embed" in model_name:
            print(" [SKIP] (Modèle d'embedding vectoriel)")
            continue

        model_stats = metrics_data["models"].get(model_name, {
            "total_calls": 0, "success_count": 0, "error_count": 0, "avg_latency_ms": 0.0
        })

        start_time = time.perf_counter()
        success = False
        try:
            # Appel léger de test d'inférence
            response = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": test_prompt}],
                options={"num_predict": 5}
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            success = True
            print(f" [OK] -> Latence mesurée : {elapsed_ms:.2f} ms")
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            success = False
            print(f" [ERREUR] -> {str(e)[:50]}")

        # Mise à jour des compteurs empiriques
        model_stats["total_calls"] += 1
        if success:
            model_stats["success_count"] += 1
            # Calcul de la moyenne mobile de latence
            prev_avg = model_stats.get("avg_latency_ms", 0.0)
            total = model_stats["success_count"]
            model_stats["avg_latency_ms"] = round(((prev_avg * (total - 1)) + elapsed_ms) / total, 2)
        else:
            model_stats["error_count"] += 1

        model_stats["last_tested"] = datetime.now(timezone.utc).isoformat()
        metrics_data["models"][model_name] = model_stats

    # Sauvegarde des métriques actualisées
    metrics_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    METRICS_PATH.write_text(json.dumps(metrics_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Télémétrie runtime mise à jour avec succès : {METRICS_PATH.name}")

if __name__ == "__main__":
    run_runtime_probe()
