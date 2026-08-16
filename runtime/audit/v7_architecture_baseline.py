import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def classify_file(path: Path) -> str:
    parts = str(path).lower()
    if "archive" in parts or "backup" in parts or "history" in parts or "trace" in parts:
        return "ARCHIVE"
    if "test" in parts or "test_" in path.name:
        return "TEST"
    if "data" in parts or "ledger" in parts or "logs" in parts or path.suffix in {".jsonl", ".db", ".log", ".txt"}:
        return "DATA"
    if "temp" in parts or "cache" in parts:
        return "TEMPORARY"
    if "legacy" in parts or "v6" in parts:
        return "LEGACY"
    if "runtime" in parts or "core" in parts or "governance" in parts or "bridge" in parts:
        return "ACTIVE"
    return "UNKNOWN"

def run_baseline():
    print("[*] Génération de la Baseline Architecturale V7.11.0.6...")
    inventory = {"ACTIVE": [], "ARCHIVE": [], "LEGACY": [], "TEST": [], "DATA": [], "TEMPORARY": [], "UNKNOWN": []}
    
    for path in ROOT_DIR.rglob("*"):
        if path.is_dir() or any(ex in path.parts for ex in {".git", "venv", "node_modules", "runtime/audit/intelligence_scan"}):
            continue
        
        category = classify_file(path)
        rel_path = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
        inventory[category].append(rel_path)

    # Sauvegarde du manifeste de baseline
    (REGISTRY_OUT / "architecture_baseline.json").write_text(json.dumps(inventory, indent=2))

    # Génération Rapport Markdown
    md_path = REGISTRY_OUT / "V7_11_0_6_BASELINE_REPORT.md"
    lines = ["# V7.11.0.6 — Architecture Baseline Report", f"**Date :** {datetime.now().isoformat()}", ""]
    for cat, files in inventory.items():
        lines.append(f"## {cat} ({len(files)} fichiers)")
        # On n'affiche que les 10 premiers pour ne pas saturer
        for f in files[:10]: lines.append(f"- `{f}`")
        if len(files) > 10: lines.append(f"- ... (et {len(files)-10} autres)")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Baseline générée dans {REGISTRY_OUT}")

if __name__ == "__main__":
    run_baseline()
