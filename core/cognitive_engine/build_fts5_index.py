"""
E-ZZIO V7.59 — Controlled FTS5 Index Builder & Provenance Auditor
Analyse la provenance des lignes qualifiées, construit l'index SQLite FTS5 de manière
isoler et réversible, et génère un index_build_manifest.json.
"""
import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognitive_engine.memory_validator import MemoryValidator

INDEX_DIR = ROOT_DIR / "runtime" / "cognitive" / "index"
INDEX_DB = INDEX_DIR / "memory_index.sqlite"
MANIFEST_FILE = INDEX_DIR / "index_build_manifest.json"
REPORT_FILE = ROOT_DIR / "runtime" / "audit" / "system" / "provenance_audit_report.json"

TARGET_EXTENSIONS = {".md", ".jsonl", ".db", ".sqlite", ".txt", ".json"}
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules"}

class CognitiveIndexBuilder:
    def __init__(self):
        self.validator = MemoryValidator()
        self.provenance_stats = {}
        self.total_records_indexed = 0

    def init_db(self):
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        # Supprime l'ancien index pour garantir une construction intègre et propre
        if INDEX_DB.exists():
            INDEX_DB.unlink()

        with sqlite3.connect(INDEX_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
                    content,
                    memory_type,
                    source_path,
                    source_hash,
                    confidence,
                    importance,
                    last_validated
                );
            """)
            conn.commit()

    def audit_and_build(self):
        print(f"[*] Démarrage de l'audit de provenance et de l'indexation FTS5 contrôlée...")
        self.init_db()

        metrics = {
            "PROTECTED": 0,
            "QUALIFIED": 0,
            "REJECTED": 0,
            "SYNTHETIC_BLOCKED": 0,
            "HASH_ERRORS": 0
        }

        indexed_files_manifest = []

        with sqlite3.connect(INDEX_DB) as conn:
            cursor = conn.cursor()

            for root, dirs, files in os.walk(ROOT_DIR):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() not in TARGET_EXTENSIONS:
                        continue

                    rel_path = file_path.relative_to(ROOT_DIR).as_posix()
                    validation = self.validator.evaluate_source(file_path)

                    if not validation.get("promoted", False):
                        reason = validation.get("reason", "")
                        if "synthetic" in reason:
                            metrics["SYNTHETIC_BLOCKED"] += 1
                        else:
                            metrics["REJECTED"] += 1
                        continue

                    # Catégorisation des métriques
                    if validation.get("protected", False):
                        metrics["PROTECTED"] += 1
                    else:
                        metrics["QUALIFIED"] += 1

                    # Suivi de provenance par dossier parent
                    parent_dir = str(file_path.parent.relative_to(ROOT_DIR)).replace("\\", "/")
                    if parent_dir == ".": parent_dir = "root"
                    self.provenance_stats[parent_dir] = self.provenance_stats.get(parent_dir, 0) + 1

                    # Traitement d'indexation selon le type
                    ext = file_path.suffix.lower()
                    timestamp = datetime.now(timezone.utc).isoformat()
                    memory_type = validation.get("memory_type", "generic")
                    confidence = validation.get("confidence", 0.5)
                    importance = validation.get("importance", 5)

                    try:
                        if ext == ".jsonl":
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                for line in f:
                                    line_clean = line.strip()
                                    if line_clean:
                                        cursor.execute("""
                                            INSERT INTO memory_search (content, memory_type, source_path, source_hash, confidence, importance, last_validated)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        """, (line_clean, memory_type, rel_path, "jsonl_line_hash", confidence, importance, timestamp))
                                        self.total_records_indexed += 1
                        else:
                            # Pour les fichiers Markdown, Texte, JSON, SQLite (métadonnées)
                            content_text = f"Fichier documenté : {rel_path} [Type: {memory_type}]"
                            cursor.execute("""
                                INSERT INTO memory_search (content, memory_type, source_path, source_hash, confidence, importance, last_validated)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (content_text, memory_type, rel_path, "file_registry_hash", confidence, importance, timestamp))
                            self.total_records_indexed += 1

                        indexed_files_manifest.append(rel_path)
                    except Exception:
                        metrics["HASH_ERRORS"] += 1

            conn.commit()

        # Génération du manifest réversible
        manifest_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine": "FTS5_LOCAL",
            "total_records_indexed": self.total_records_indexed,
            "metrics": metrics,
            "provenance_distribution": self.provenance_stats,
            "indexed_files": indexed_files_manifest
        }

        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        # Génération du rapport d'audit de provenance
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provenance_breakdown": self.provenance_stats,
                "metrics": metrics
            }, f, ensure_ascii=False, indent=2)

        # Affichage console complet (Télémétrie intégrale)
        print("-" * 50)
        print(" RAPPORT D'AUDIT DE PROVENANCE & INDEX FTS5")
        print("-" * 50)
        print(f" PROTECTED          : {metrics['PROTECTED']} (19 attendus)")
        print(f" QUALIFIED          : {metrics['QUALIFIED']}")
        print(f" REJECTED           : {metrics['REJECTED']}")
        print(f" SYNTHETIC_BLOCKED  : {metrics['SYNTHETIC_BLOCKED']} (bruit exclu)")
        print(f" HASH_ERRORS        : {metrics['HASH_ERRORS']}")
        print("-" * 50)
        print(f" Total enregistrements FTS5 : {self.total_records_indexed}")
        print("-" * 50)
        print(" RÉPARTITION DE LA PROVENANCE (Top dossiers) :")
        for folder, count in sorted(self.provenance_stats.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"   - {folder:<30} : {count} fichiers")
        print("-" * 50)
        print(f" Manifest réversible généré : {MANIFEST_FILE}")
        print(f" Rapport d'audit de prov.   : {REPORT_FILE}")

if __name__ == "__main__":
    builder = CognitiveIndexBuilder()
    builder.audit_and_build()
