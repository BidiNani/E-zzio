"""
E-ZZIO V7.58 — Cognitive Extractor (Forensic Dry-Run 2)
Cible l'exhaustivité (.txt, .json) et intègre le Pare-Feu Cognitif.
"""
import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognitive_engine.memory_validator import MemoryValidator

REPORT_FILE = ROOT_DIR / "runtime" / "audit" / "system" / "extraction_dry_run_report.json"
TARGET_EXTENSIONS = {".md", ".jsonl", ".db", ".sqlite", ".txt", ".json"}
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules"}

class ExtractorDryRun:
    def __init__(self):
        self.validator = MemoryValidator()
        self.stats = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "DRY_RUN",
            "files_scanned": 0,
            "metrics": {
                "PROTECTED": 0,
                "QUALIFIED": 0,
                "REJECTED": 0,
                "ERRORS": 0
            },
            "extraction_potential": {
                "jsonl_records": 0,
                "sqlite_rows": 0,
                "md_documents": 0,
                "json_documents": 0,
                "txt_documents": 0
            },
            "details": {
                "protected_files": [],
                "qualified_files": [],
                "rejected_reasons": {}
            }
        }

    def compute_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception:
            return "HASH_ERROR"

    def simulate_jsonl(self, file_path: Path):
        count = 0
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for _ in f: count += 1
            self.stats["extraction_potential"]["jsonl_records"] += count
        except Exception as e:
            raise Exception(f"Erreur JSONL : {e}")

    def simulate_sqlite(self, file_path: Path):
        count = 0
        try:
            uri = f"file:{file_path}?mode=ro"
            with sqlite3.connect(uri, uri=True) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                        count += cursor.fetchone()[0]
                    except:
                        pass
            self.stats["extraction_potential"]["sqlite_rows"] += count
        except Exception as e:
            raise Exception(f"Erreur SQLite : {e}")

    def process_file(self, file_path: Path):
        self.stats["files_scanned"] += 1
        rel_path = file_path.relative_to(ROOT_DIR).as_posix()
        
        validation = self.validator.evaluate_source(file_path)
        
        if not validation.get("promoted", False):
            self.stats["metrics"]["REJECTED"] += 1
            reason = validation.get("reason", "Unknown")
            self.stats["details"]["rejected_reasons"][reason] = self.stats["details"]["rejected_reasons"].get(reason, 0) + 1
            return

        file_hash = self.compute_hash(file_path)
        record = {
            "path": rel_path,
            "hash": file_hash,
            "memory_type": validation.get("memory_type", "generic"),
            "confidence": validation.get("confidence", 0.5)
        }

        if validation.get("protected", False):
            self.stats["metrics"]["PROTECTED"] += 1
            self.stats["details"]["protected_files"].append(record)
        else:
            self.stats["metrics"]["QUALIFIED"] += 1
            self.stats["details"]["qualified_files"].append(record)

        try:
            ext = file_path.suffix.lower()
            if ext == ".jsonl":
                self.simulate_jsonl(file_path)
            elif ext in {".db", ".sqlite"}:
                self.simulate_sqlite(file_path)
            elif ext == ".md":
                self.stats["extraction_potential"]["md_documents"] += 1
            elif ext == ".json":
                self.stats["extraction_potential"]["json_documents"] += 1
            elif ext == ".txt":
                self.stats["extraction_potential"]["txt_documents"] += 1
        except Exception as e:
            self.stats["metrics"]["ERRORS"] += 1

    def run(self):
        print(f"[*] Démarrage de l'extraction V7.58 (DRY-RUN)")
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in TARGET_EXTENSIONS:
                    self.process_file(file_path)

        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

        print("-" * 50)
        print(" RAPPORT D'EXTRACTION V7.58 (DRY-RUN)")
        print("-" * 50)
        print(f" Fichiers cibles scannés  : {self.stats['files_scanned']}")
        print(f" Identité (PROTECTED)     : {self.stats['metrics']['PROTECTED']} / 19 Attendus")
        print(f" Mémoire (QUALIFIED)      : {self.stats['metrics']['QUALIFIED']}")
        print(f" Bruit & Tests (REJECTED) : {self.stats['metrics']['REJECTED']}")
        print(f" Erreurs                  : {self.stats['metrics']['ERRORS']}")
        print("-" * 50)
        print(f" Lignes JSONL conservées  : {self.stats['extraction_potential']['jsonl_records']}")
        print(f" Rapport sauvegardé dans  : {REPORT_FILE}")

if __name__ == "__main__":
    extractor = ExtractorDryRun()
    extractor.run()
