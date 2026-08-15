"""
E-ZZIO V7.59.5 — Lore Lineage Probe (Read-Only Autopsy)
Analyse chirurgicale de registry/personality/lore.md :
- Hash SHA-256, tailles et métadonnées temporelles
- Analyse sémantique multi-domaines (Identité, Persona, RPG/Gameplay)
- Recherche de références croisées (provenance)
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_FILE = ROOT_DIR / "registry/personality/lore.md"
OUTPUT_REPORT = ROOT_DIR / "runtime/audit/system/lore_lineage_report.json"

SEMANTIC_DOMAINS = {
    "identity": ["bidi", "h3stiana", "fils", "origine", "racine"],
    "persona": ["arts visuel", "passion", "valeur", "créateur", "profil"],
    "rpg": ["wow", "wotlk", "3.3.5", "lich king", "ulduar", "icc", "naxx"],
    "gameplay": ["druid", "feral", "raid", "boss", "macro", "talent", "gear", "loot", "spec", "classe", "niveau"]
}

def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def find_references(file_name: str) -> list:
    refs = []
    for path in ROOT_DIR.rglob('*'):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".jsonl", ".txt"}:
            if path == TARGET_FILE:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    if file_name.lower() in f.read().lower():
                        refs.append(str(path.relative_to(ROOT_DIR)))
            except Exception:
                pass
    return refs

def probe_lore():
    if not TARGET_FILE.exists():
        print(f"[!] Fichier cible introuvable : {TARGET_FILE}")
        return

    print(f"[*] Lancement de l'autopsie de {TARGET_FILE.relative_to(ROOT_DIR)}...")

    stat = TARGET_FILE.stat()
    sha256 = compute_sha256(TARGET_FILE)
    
    with open(TARGET_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        content_lower = content.lower()

    # Analyse des domaines sémantiques et comptage des hits
    domain_hits = {}
    total_hits = 0
    for domain, keywords in SEMANTIC_DOMAINS.items():
        hits = [kw for kw in keywords if kw in content_lower]
        domain_hits[domain] = {
            "count": len(hits),
            "matched_keywords": hits
        }
        total_hits += len(hits)

    # Recherche de provenance (qui référence lore.md ?)
    incoming_refs = find_references(TARGET_FILE.name)

    # Détermination du Verdict
    rpg_count = domain_hits["rpg"]["count"] + domain_hits["gameplay"]["count"]
    persona_count = domain_hits["persona"]["count"] + domain_hits["identity"]["count"]

    if rpg_count >= 3 and persona_count >= 2:
        verdict = "MIXED"
        indexable = True
        confidence = 0.95
    elif rpg_count >= 3:
        verdict = "RPG_MEMORY"
        indexable = True
        confidence = 0.95
    elif persona_count >= 1:
        verdict = "PERSONA"
        indexable = True
        confidence = 0.90
    else:
        verdict = "UNKNOWN"
        indexable = False
        confidence = 0.50

    report = {
        "file": "registry/personality/lore.md",
        "sha256": sha256,
        "size_bytes": stat.st_size,
        "dates": {
            "created": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        },
        "semantic_analysis": domain_hits,
        "provenance_references": incoming_refs,
        "verdict": verdict,
        "indexable": indexable,
        "confidence": confidence,
        "content_preview": content[:300]
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Affichage rapport console formaté
    print("\n" + "=" * 60)
    print(" RPG MEMORY LINEAGE PROBE RESULT (V7.59.5)")
    print("=" * 60)
    print(f" File       : registry/personality/lore.md")
    print(f" SHA256     : {sha256}")
    print(f" Size       : {stat.st_size} octets")
    print(f" Modified   : {report['dates']['modified']}")
    print("-" * 60)
    print(" SEMANTIC DOMAINS HITS :")
    for dom, data in domain_hits.items():
        print(f"   - {dom.upper():<10} : {data['count']} hits ({', '.join(data['matched_keywords']) if data['matched_keywords'] else 'aucun'})")
    print("-" * 60)
    print(f" Provenance references (fichiers pointant vers lore.md) : {len(incoming_refs)}")
    for ref in incoming_refs[:5]:
        print(f"   * {ref}")
    print("-" * 60)
    print(f" VERDICT    : {verdict}")
    print(f" INDEXABLE  : {indexable}")
    print(f" CONFIDENCE : {confidence}")
    print("=" * 60)
    print(f" Rapport complet exporté : {OUTPUT_REPORT}")

if __name__ == "__main__":
    probe_lore()
