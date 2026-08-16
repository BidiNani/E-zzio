import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"

TARGET_FILES = [
    "contracts.py",
    "policies.py",
    "governor.py",
    "manager.py",
    "ledger.py",
    "quarantine.py",
    "scaling.py",
    "retry.py",
    "collector.py",
    "events.py"
]

def locate_sources():
    print("[*] Démarrage de V7.11.2.4 — Active Runtime Source Locator...")
    results = {target: [] for target in TARGET_FILES}

    for path in ROOT_DIR.rglob("*.py"):
        if any(ex in path.parts for ex in {".git", "venv", "node_modules"}):
            continue
        
        if path.name in TARGET_FILES:
            rel_path = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
            try:
                h = hashlib.sha256(path.read_bytes()).hexdigest()
            except:
                h = "READ_ERROR"
            
            # Classifier la zone où le fichier a été trouvé
            zone = "UNKNOWN"
            rel_lower = rel_path.lower()
            if "quarantine" in rel_lower: zone = "QUARANTINE"
            elif "archive" in rel_lower: zone = "ARCHIVE"
            elif "legacy" in rel_lower: zone = "LEGACY"
            elif "test" in rel_lower: zone = "TEST"
            elif any(k in rel_lower for k in {"recovery", "telemetry"}): zone = "RECOVERY_TARGET_ZONE"
            else: zone = "ACTIVE_OTHER"

            results[path.name].append({
                "path": rel_path,
                "zone": zone,
                "sha256": h
            })

    payload = {
        "timestamp": datetime.now().isoformat(),
        "locations": results
    }

    out_json = REGISTRY_OUT / "source_locator_results.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(payload, out_json)
    print(f"[OK] Localisateur de sources terminé. Rapport : {REGISTRY_OUT / 'V7_11_2_4_SOURCE_LOCATOR_REPORT.md'}")

def build_markdown(payload: dict, json_path: Path):
    md_path = REGISTRY_OUT / "V7_11_2_4_SOURCE_LOCATOR_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.2.4 — Active Runtime Source Locator Report",
        f"**Date :** {payload['timestamp']}",
        "",
        "## 1. Localisation Physique Globale des 10 Modules Cibles",
        "| Fichier Cible | Emplacements Trouvés sur le Disque (Chemin & Zone) |",
        "| :--- | :--- |"
    ]

    for fname, locs in payload["locations"].items():
        if not locs:
        # Utilisation de balises HTML simples pour éviter tout plantage Markdown
            lines.append(f"| `{fname}` | ❌ **INTROUVABLE SUR TOUT LE DISQUE** |")
        else:
            loc_str = "<br>".join([f"`{l['path']}` *({l['zone']})*" for l in locs])
            lines.append(f"| `{fname}` | {loc_str} |")

    lines.extend([
        "",
        "## 2. Conclusion du Diagnostic Global",
        "Ce balayage exhaustif permet de trancher définitivement : soit les fichiers résident dans une zone inattendue (archives profondes, sous un autre nom), soit ils ont totalement disparu du dépôt physique et constituaient une dépendance fantôme.",
        "",
        f"**Rapport JSON :** `{json_path.name}`"
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    locate_sources()
