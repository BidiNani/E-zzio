from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def find_registry_files() -> List[Path]:
    candidates = []
    for p in PROJECT_ROOT.glob("**/*registry*.json"):
        if not any(excluded in p.parts for excluded in {".venv", "venv", ".git", "__pycache__", "snapshots", "backup", "backups"}):
            candidates.append(p)
    for p in PROJECT_ROOT.glob("**/models*.json"):
        if not any(excluded in p.parts for excluded in {".venv", "venv", ".git", "__pycache__", "snapshots", "backup", "backups"}):
            candidates.append(p)
    return candidates

def inspect_registry_payload(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return {"valid_json": True, "data": data}
    except Exception as e:
        return {"valid_json": False, "error": str(e)}

def main():
    print("=" * 80)
    print(" AUDIT D'ÉTAT — MODEL REGISTRY PERSISTENCE SNAPSHOT")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    registry_files = find_registry_files()
    print(f"[+] Fichiers de registre JSON détectés : {len(registry_files)}")

    for f in registry_files:
        rel = f.relative_to(PROJECT_ROOT)
        print(f"\n📁 REGISTRE : {rel}")
        res = inspect_registry_payload(f)
        if not res["valid_json"]:
            print(f"  ❌ Erreur lecture JSON : {res['error']}")
            continue

        raw = res["data"]
        # Inspection de la structure
        records = []
        if isinstance(raw, dict):
            if "models" in raw and isinstance(raw["models"], (dict, list)):
                records = list(raw["models"].values()) if isinstance(raw["models"], dict) else raw["models"]
            elif "_models" in raw and isinstance(raw["_models"], (dict, list)):
                records = list(raw["_models"].values()) if isinstance(raw["_models"], dict) else raw["_models"]
            else:
                # Dictionnaire direct de records
                records = list(raw.values()) if all(isinstance(v, dict) for v in raw.values()) else [raw]
        elif isinstance(raw, list):
            records = raw

        print(f"  📊 Nombre d'enregistrements : {len(records)}")
        active_count = 0
        for r in records:
            if isinstance(r, dict):
                provider = r.get("provider", "unknown")
                model_id = r.get("model_id", r.get("id", "unknown"))
                tier = r.get("tier", "UNKNOWN")
                lifecycle = r.get("lifecycle", r.get("state", "UNKNOWN"))
                score = r.get("qualification_score", r.get("score", "N/A"))
                latency = r.get("latency_ms", "N/A")
                
                is_active = str(lifecycle).upper() == "ACTIVE"
                if is_active:
                    active_count += 1
                status_icon = "🟢 [ACTIVE]" if is_active else f"⚪ [{lifecycle}]"
                print(f"    • {status_icon} {provider}/{model_id} | Tier: {tier} | Score: {score} | Latency: {latency}ms")
        
        print(f"  🏆 Modèles ACTIVE dans ce registre : {active_count}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()