"""
E-ZZIO V7.59.7 — Timeline File Birth & Mutation (Forensic Audit)
Scande les répertoires cibles et classe les fichiers selon leur appartenance
à la fenêtre temporelle nocturne (21:00 - 03:00) pour reconstituer l'historique de forge.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, time

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_DIRS = ["core", "runtime", "registry", "state", "bridge", "config"]
EXCLUDE_PATTERNS = [".venv", "__pycache__", "cache", "logs", ".tmp", ".bak", ".sqlite-wal", ".sqlite-shm"]
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "timeline_birth_mutation_report.json"


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return "ERROR_READING_FILE"


def is_nocturnal_window(dt: datetime) -> bool:
    # Fenêtre 21:00 à 03:00 (+ jour suivant)
    t = dt.time()
    return t >= time(21, 0) or t < time(3, 0)


def run_timeline_audit():
    print("[*] Lancement de l'archéologie temporelle (Fenêtre 21:00 - 03:00)...")
    class_a_creations = []
    class_b_mutations = []
    class_c_artifacts = []

    for target in TARGET_DIRS:
        dir_path = ROOT_DIR / target
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(ROOT_DIR).as_posix()

                # Exclusion stricte du bruit système
                if any(ex in rel_path.lower() for ex in EXCLUDE_PATTERNS):
                    continue

                try:
                    stat = path.stat()
                    ctime = datetime.fromtimestamp(stat.st_ctime)
                    mtime = datetime.fromtimestamp(stat.st_mtime)

                    file_info = {
                        "path": rel_path,
                        "size": stat.st_size,
                        "creation_time": ctime.isoformat(),
                        "last_write_time": mtime.isoformat(),
                        "extension": path.suffix.lower(),
                    }

                    # Classification selon la fenêtre nocturne 21h-03h
                    is_nocturnal_creation = is_nocturnal_window(ctime)
                    is_nocturnal_mutation = is_nocturnal_window(mtime)

                    if is_nocturnal_creation:
                        file_info["sha256"] = compute_sha256(path)
                        class_a_creations.append(file_info)
                    elif is_nocturnal_mutation:
                        file_info["sha256"] = compute_sha256(path)
                        class_b_mutations.append(file_info)

                    # Classe C : Artefacts structurels pertinents (.json, .jsonl, .md, .py, .ps1)
                    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ps1"}:
                        class_c_artifacts.append(file_info)

                except Exception:
                    continue

    report = {
        "window": "21:00 - 03:00",
        "class_a_nocturnal_creations_count": len(class_a_creations),
        "class_b_nocturnal_mutations_count": len(class_b_mutations),
        "class_c_structural_artifacts_count": len(class_c_artifacts),
        "class_a_creations": class_a_creations,
        "class_b_mutations": class_b_mutations,
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" TIMELINE FILE BIRTH & MUTATION REPORT (V7.59.7)")
    print("=" * 65)
    print(f" Classe A (Créations nocturnes 21h-03h) : {len(class_a_creations)}")
    print(f" Classe B (Mutations nocturnes 21h-03h) : {len(class_b_mutations)}")
    print(f" Classe C (Artefacts structurels totaux) : {len(class_c_artifacts)}")
    print("-" * 65)
    if class_a_creations:
        print(" Aperçu des Créations Nocturnes (Classe A) :")
        for item in class_a_creations[:10]:
            print(f"   - [{item['creation_time'][:19]}] {item['path']}")
    else:
        print(" -> Aucune création directe dans la fenêtre 21h-03h (les fichiers ont pu être déplacés ou copiés).")
    print("=" * 65)
    print(f" Rapport complet exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    run_timeline_audit()
