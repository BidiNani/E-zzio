"""
E-ZZIO V7.59.4.2 — Archaeology Scan
Scanne uniquement les dossiers sources (state, bridge, registry, memory) 
à la recherche de clusters sémantiques RPG (3+ mots-clés distincts).
Exclut strictement tout ce qui est audit, forensic, ou dump.
"""
import os
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")

# Dossiers sources de vérité cognitive
TARGET_DIRS = ["state", "bridge", "registry", "runtime/cognitive", "runtime/decisions", "runtime/memory"]
# Dossiers à ignorer absolument (bruit technique)
EXCLUDE_PATTERNS = ["audit", "forensic", "dump", ".venv", ".pytest", "test_isolation", "logs", "temp", "cache"]

RPG_CLUSTERS = {"wotlk", "druid", "feral", "raid", "icc", "macro", "talent", "gear", "warlock", "wow", "lich king"}

def scan():
    results = []
    print("[*] Scanning memory sources for RPG memory lineage...")

    for root, dirs, files in os.walk(ROOT_DIR):
        # Filtrage manuel des branches
        rel_root = Path(root).relative_to(ROOT_DIR).as_posix()
        if any(ex in rel_root for ex in EXCLUDE_PATTERNS):
            continue
        if not any(target in rel_root for target in TARGET_DIRS) and rel_root != ".":
            continue

        for file in files:
            if file.endswith(('.md', '.jsonl', '.txt', '.json', '.sqlite')):
                path = Path(root) / file
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                    
                    hits = [word for word in RPG_CLUSTERS if word in content]
                    unique_hits = set(hits)
                    
                    # Seuil de 3 hits distincts pour éviter les faux positifs de logs
                    if len(unique_hits) >= 3:
                        results.append({
                            "path": str(path.relative_to(ROOT_DIR)),
                            "hits_count": len(unique_hits),
                            "hits": list(unique_hits),
                            "snippet": content[:150]
                        })
                except Exception: continue

    output = ROOT_DIR / "runtime/audit/system/rpg_archaeology_lineage.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"[*] Audit complet. {len(results)} sources cognitives identifiées.")
    for r in results:
        print(f" -> {r['path']} (Hits: {r['hits_count']})")

if __name__ == "__main__":
    scan()
