"""
E-ZZIO V7.53 — Full Cognitive Forensic Scanner (Read-Only)
Inventaire exhaustif de G:\AI\E-zzio : hachage SHA-256, inspection SQLite (.db),
analyse structurelle JSON/JSONL/MD/TXT/Python.
"""
import os
import sys
import pathlib
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

ROOT_DIR = pathlib.Path(r"G:\AI\E-zzio")
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "full_cognitive_inventory.json"
EXCLUDE_DIRS = {'.git', '__pycache__', '.venv', 'node_modules', 'venv', '.idea'}

def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def inspect_sqlite(db_path):
    info = {"tables": {}, "total_rows": 0, "error": None}
    try:
        # Connexion en mode lecture seule stricte
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                count = cursor.fetchone()[0]
                cursor.execute(f"PRAGMA table_info([{table}])")
                columns = [col[1] for col in cursor.fetchall()]
                info["tables"][table] = {"row_count": count, "columns": columns}
                info["total_rows"] += count
            except Exception as e:
                info["tables"][table] = {"error": str(e)}
        conn.close()
    except Exception as e:
        info["error"] = str(e)
    return info

def inspect_json(file_path):
    info = {"record_count": 0, "keys": [], "has_timestamps": False, "has_provenance": False, "error": None}
    try:
        size = file_path.stat().st_size
        if size > 50 * 1024 * 1024:  # Évite les OOM sur les fichiers > 50MB
            info["error"] = "File too large for deep JSON parse (>50MB)"
            return info
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            if file_path.suffix.lower() == ".jsonl":
                count = 0
                sample_keys = set()
                for line in f:
                    count += 1
                    if count <= 5:  # Échantillon sur les 5 premières lignes
                        try:
                            data = json.loads(line)
                            if isinstance(data, dict):
                                sample_keys.update(data.keys())
                        except:
                            pass
                info["record_count"] = count
                info["keys"] = list(sample_keys)
            else:
                data = json.load(f)
                if isinstance(data, list):
                    info["record_count"] = len(data)
                    if data and isinstance(data[0], dict):
                        info["keys"] = list(data[0].keys())
                elif isinstance(data, dict):
                    info["record_count"] = 1
                    info["keys"] = list(data.keys())
        
        keys_str = str(info["keys"]).lower()
        info["has_timestamps"] = any(k in keys_str for k in ["time", "date", "timestamp", "created"])
        info["has_provenance"] = any(k in keys_str for k in ["hash", "user_id", "source", "provenance", "author"])
    except Exception as e:
        info["error"] = str(e)
    return info

def run_inventory():
    print(f"[*] Démarrage de l'inventaire cognitif complet sur : {ROOT_DIR}")
    
    inventory = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": 0,
        "total_size_bytes": 0,
        "formats": {},
        "files": [],
        "hash_registry": {} # Pour la détection de doublons exacts
    }

    target_extensions = {".md", ".json", ".jsonl", ".db", ".sqlite", ".txt", ".py"}

    for root, dirs, files in os.walk(ROOT_DIR):
        # Filtrage des dossiers exclus
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            file_path = pathlib.Path(root) / file
            ext = file_path.suffix.lower()
            
            if ext not in target_extensions:
                continue
                
            inventory["total_files"] += 1
            try:
                size = file_path.stat().st_size
            except:
                size = 0
                
            inventory["total_size_bytes"] += size
            
            if ext not in inventory["formats"]:
                inventory["formats"][ext] = {"count": 0, "total_size": 0}
            inventory["formats"][ext]["count"] += 1
            inventory["formats"][ext]["total_size"] += size

            # Calcul du SHA-256 pour détection de doublons
            file_hash = compute_sha256(file_path)
            if file_hash:
                if file_hash not in inventory["hash_registry"]:
                    inventory["hash_registry"][file_hash] = []
                inventory["hash_registry"][file_hash].append(str(file_path.relative_to(ROOT_DIR)))

            file_meta = {
                "path": str(file_path.relative_to(ROOT_DIR)),
                "size_bytes": size,
                "sha256": file_hash,
                "extension": ext
            }

            # Inspected deep-dive
            if ext in {".db", ".sqlite"}:
                file_meta["sqlite_inspection"] = inspect_sqlite(file_path)
            elif ext in {".json", ".jsonl"}:
                file_meta["json_inspection"] = inspect_json(file_path)
                
            inventory["files"].append(file_meta)

    # Nettoyage / Synthèse des doublons exacts (où len > 1)
    duplicates = {h: paths for h, paths in inventory["hash_registry"].items() if len(paths) > 1}
    inventory["exact_duplicates_found"] = len(duplicates)
    inventory["duplicates_details"] = duplicates

    # Sauvegarde du rapport complet
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2)

    print(f"[OK] Inventaire complet terminé.")
    print(f"-> Fichiers analysés : {inventory['total_files']}")
    print(f"-> Poids total : {round(inventory['total_size_bytes'] / (1024*1024), 2)} MB")
    print(f"-> Doublons exacts détectés (par hash) : {len(duplicates)}")
    print(f"-> Rapport enregistré dans : {OUTPUT_REPORT}")

if __name__ == "__main__":
    run_inventory()
