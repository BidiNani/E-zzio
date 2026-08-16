import json
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
BASELINE = json.loads((ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY" / "architecture_baseline.json").read_text())

def generate_plan():
    plan = {"move_to_archive": [], "move_to_legacy": [], "move_to_temp": []}
    
    # Mapping catégories
    for path_str in BASELINE["ARCHIVE"]: plan["move_to_archive"].append(path_str)
    for path_str in BASELINE["LEGACY"]: plan["move_to_legacy"].append(path_str)
    for path_str in BASELINE["TEMPORARY"]: plan["move_to_temp"].append(path_str)
    
    (ROOT_DIR / "runtime" / "audit" / "V7_CLEANUP_PLAN.json").write_text(json.dumps(plan, indent=2))
    print("[OK] Manifeste de nettoyage généré : runtime/audit/V7_CLEANUP_PLAN.json")

if __name__ == "__main__":
    generate_plan()
