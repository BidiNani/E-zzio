import json
from pathlib import Path

def filter_critical_duplicates():
    scan_dir = Path("runtime/audit/full_scan")
    dups_path = scan_dir / "duplicate_candidates.json"
    
    if not dups_path.exists():
        print("[ERR] duplicate_candidates.json introuvable.")
        return

    duplicates = json.loads(dups_path.read_text(encoding="utf-8"))
    
    critical_groups = []
    for group in duplicates:
        # On filtre pour ne garder que les groupes hors test_isolation
        filtered_files = [f for f in group["files"] if "test_isolation" not in f and "audit" not in f]
        if len(filtered_files) > 1:
            group["files"] = filtered_files
            critical_groups.append(group)

    print(f"\n[CRITICAL DUPES] {len(critical_groups)} groupes de doublons structurels hors tests identifiés :")
    for g in critical_groups:
        print(f"\n  - Groupe: {g['group']}")
        for f in g["files"]:
            print(f"      -> {f}")

    # Sauvegarde du plan de refactorisation ciblé
    plan_dir = Path("runtime/audit/refactor_plan")
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "critical_duplicates.json").write_text(json.dumps(critical_groups, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Rapport critique enregistré dans runtime/audit/refactor_plan/critical_duplicates.json")

if __name__ == "__main__":
    filter_critical_duplicates()
