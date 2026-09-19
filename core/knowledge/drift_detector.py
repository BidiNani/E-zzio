"""
E-ZZIO OS — Sovereign Forensic Drift Detector v1
Compares the live physical filesystem state against the frozen Self-Knowledge Map (_forensic/knowledge/).
Strictly READ-ONLY vis-à-vis source files and knowledge artifacts.
All outputs are isolated in _forensic/drift/.
"""

import ast
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ezzio.drift_detector")


class DriftVerdict(StrEnum):
    NO_DRIFT = "NO_DRIFT"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"
    MAP_STALE = "MAP_STALE"
    UNKNOWN = "UNKNOWN"


class FileDriftStatus(StrEnum):
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    NEW = "NEW"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DriftResult:
    verdict: DriftVerdict
    generated_at_utc: str
    metrics: dict[str, Any]
    reconciliation: dict[str, Any]
    file_changes_summary: dict[str, int]
    symbol_changes_count: int
    api_changes_count: int
    db_changes_count: int
    artifacts_written: list[str]
    evidence_path: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "generated_at_utc": self.generated_at_utc,
            "metrics": self.metrics,
            "reconciliation": self.reconciliation,
            "file_changes_summary": self.file_changes_summary,
            "symbol_changes_count": self.symbol_changes_count,
            "api_changes_count": self.api_changes_count,
            "db_changes_count": self.db_changes_count,
            "artifacts_written": self.artifacts_written,
            "evidence_path": self.evidence_path,
            "message": self.message,
        }


class ForensicDriftDetector:
    """
    Forensic Drift Detector v1.
    Strictly READ-ONLY on project files.
    Calculates exact physical divergence against the Self-Knowledge Map.
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        knowledge_dir: str | Path | None = None,
        drift_dir: str | Path | None = None,
    ):
        if root_dir is not None:
            self._root_dir = Path(root_dir).resolve()
        else:
            self._root_dir = Path(__file__).resolve().parent.parent.parent

        if knowledge_dir is not None:
            self._knowledge_dir = Path(knowledge_dir).resolve()
        else:
            self._knowledge_dir = (self._root_dir / "_forensic" / "knowledge").resolve()

        if drift_dir is not None:
            self._drift_dir = Path(drift_dir).resolve()
        else:
            self._drift_dir = (self._root_dir / "_forensic" / "drift").resolve()

        self._map_manifest: dict[str, Any] = {}
        self._map_hashes: dict[str, str] = {}
        self._map_symbols: dict[str, Any] = {}
        self._map_apis: dict[str, Any] = {}
        self._map_databases: dict[str, Any] = {}
        self._map_master: dict[str, Any] = {}
        self._load_status: str = "UNINITIALIZED"

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def knowledge_dir(self) -> Path:
        return self._knowledge_dir

    @property
    def drift_dir(self) -> Path:
        return self._drift_dir

    def _normalize_path(self, path_str: str) -> str:
        p = path_str.replace("\\", "/").strip()
        if p.startswith("./"):
            p = p[2:]
        return p

    def _compute_sha256(self, filepath: Path) -> str:
        try:
            if filepath.is_symlink() and not filepath.exists():
                try:
                    target = os.readlink(filepath)
                    return hashlib.sha256(f"SYMLINK:{target}".encode()).hexdigest()
                except Exception:
                    return hashlib.sha256(b"BROKEN_SYMLINK").hexdigest()

            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except PermissionError:
            try:
                target = os.readlink(filepath)
                return hashlib.sha256(f"SYMLINK:{target}".encode()).hexdigest()
            except Exception:
                return "PERMISSION_DENIED"
        except Exception:
            return "UNKNOWN_HASH"

    def load_knowledge_map(self) -> bool:
        """Loads Self-Knowledge Map artifacts fail-closed."""
        if not self._knowledge_dir.is_dir():
            self._load_status = "KNOWLEDGE_DIR_MISSING"
            return False

        try:
            with open(self._knowledge_dir / "FILE_MANIFEST.json", encoding="utf-8") as f:
                self._map_manifest = json.load(f)
            with open(self._knowledge_dir / "FILE_HASHES.json", encoding="utf-8") as f:
                self._map_hashes = json.load(f)
            with open(self._knowledge_dir / "SYMBOL_INDEX.json", encoding="utf-8") as f:
                self._map_symbols = json.load(f)
            with open(self._knowledge_dir / "API_MAP.json", encoding="utf-8") as f:
                self._map_apis = json.load(f)
            with open(self._knowledge_dir / "DATABASE_MAP.json", encoding="utf-8") as f:
                self._map_databases = json.load(f)
            with open(self._knowledge_dir / "MASTER_KNOWLEDGE.json", encoding="utf-8") as f:
                self._map_master = json.load(f)
            self._load_status = "LOADED"
            return True
        except Exception as e:
            self._load_status = f"CORRUPT_MAP: {e}"
            return False

    def detect_drift(self, fast_mode: bool = False, write_artifacts: bool = True) -> DriftResult:
        """
        Executes complete physical vs map drift analysis.
        Fail-closed: returns CRITICAL_DRIFT or MAP_STALE on broken prerequisites.
        """
        now_utc = datetime.now(UTC).isoformat()

        if not self.load_knowledge_map():
            verdict = DriftVerdict.MAP_STALE if "MISSING" in self._load_status else DriftVerdict.CRITICAL_DRIFT
            return DriftResult(
                verdict=verdict,
                generated_at_utc=now_utc,
                metrics={},
                reconciliation={"passed": False, "reason": self._load_status},
                file_changes_summary={},
                symbol_changes_count=0,
                api_changes_count=0,
                db_changes_count=0,
                artifacts_written=[],
                evidence_path=str(self._knowledge_dir),
                message=f"Map loading failed: {self._load_status}",
            )

        # 1. Scan physical filesystem snapshot
        physical_files_map: dict[str, Path] = {}

        try:
            drift_rel = self._normalize_path(str(self._drift_dir.relative_to(self._root_dir)))
        except ValueError:
            drift_rel = "_forensic/drift"

        for root, _dirs, files in os.walk(self._root_dir):
            rel_root = self._normalize_path(os.path.relpath(root, self._root_dir))
            if rel_root == ".":
                rel_root = ""

            # Exclude drift output directory
            if rel_root == drift_rel or rel_root.startswith(drift_rel + "/"):
                continue

            for fname in files:
                rel_file = f"{rel_root}/{fname}" if rel_root else fname
                rel_file = self._normalize_path(rel_file)
                if rel_file.startswith(drift_rel + "/"):
                    continue
                full_p = Path(root) / fname
                physical_files_map[rel_file] = full_p

        physical_files_set: set[str] = set(physical_files_map.keys())
        map_files_set: set[str] = set(self._map_hashes.keys())

        # 2. File Drift Classification with consistent set partitioning (eliminating TOCTOU race)
        unchanged_files: list[dict[str, Any]] = []
        modified_files: list[dict[str, Any]] = []
        missing_files: list[dict[str, Any]] = []
        new_files: list[dict[str, Any]] = []
        unknown_files: list[dict[str, Any]] = []

        # Missing files: in map baseline, but absent from physical snapshot
        missing_set = map_files_set - physical_files_set
        for rel_path in sorted(missing_set):
            map_sha256 = self._map_hashes[rel_path]
            missing_files.append({
                "path": rel_path,
                "map_sha256": map_sha256,
                "status": FileDriftStatus.MISSING.value,
                "category": self._map_manifest.get(rel_path, {}).get("category", "unknown"),
            })

        # Known files: present in both map baseline and physical snapshot
        known_set = map_files_set & physical_files_set
        for rel_path in sorted(known_set):
            map_sha256 = self._map_hashes[rel_path]
            full_path = physical_files_map[rel_path]
            current_sha256 = self._compute_sha256(full_path)
            if current_sha256 in ("PERMISSION_DENIED", "UNKNOWN_HASH"):
                unknown_files.append({
                    "path": rel_path,
                    "map_sha256": map_sha256,
                    "physical_sha256": current_sha256,
                    "status": FileDriftStatus.UNKNOWN.value,
                })
            elif current_sha256 == map_sha256:
                unchanged_files.append({
                    "path": rel_path,
                    "sha256": map_sha256,
                    "status": FileDriftStatus.UNCHANGED.value,
                })
            else:
                curr_size = full_path.stat().st_size if full_path.exists() else 0
                map_size = self._map_manifest.get(rel_path, {}).get("size_bytes", 0)
                modified_files.append({
                    "path": rel_path,
                    "map_sha256": map_sha256,
                    "physical_sha256": current_sha256,
                    "map_size_bytes": map_size,
                    "physical_size_bytes": curr_size,
                    "size_delta": curr_size - map_size,
                    "status": FileDriftStatus.MODIFIED.value,
                    "category": self._map_manifest.get(rel_path, {}).get("category", "unknown"),
                })

        # New files: present in physical snapshot, but absent from map baseline
        new_set = physical_files_set - map_files_set
        for rel_file in sorted(new_set):
            full_p = physical_files_map[rel_file]
            curr_size = full_p.stat().st_size if full_p.exists() else 0
            new_files.append({
                "path": rel_file,
                "physical_sha256": self._compute_sha256(full_p),
                "size_bytes": curr_size,
                "status": FileDriftStatus.NEW.value,
            })

        # 3. Symbol Drift Analysis
        symbol_changes: list[dict[str, Any]] = []
        affected_py_files = set()
        for f in modified_files:
            if f["path"].endswith(".py"):
                affected_py_files.add(f["path"])
        for f in new_files:
            if f["path"].endswith(".py"):
                affected_py_files.add(f["path"])
        for f in missing_files:
            if f["path"].endswith(".py"):
                affected_py_files.add(f["path"])

        for py_rel in affected_py_files:
            py_full = self._root_dir / py_rel.replace("/", os.sep)
            if not py_full.exists():
                for sym_id, _s_data in self._map_symbols.get("classes", {}).items():
                    if sym_id.startswith(py_rel + "::"):
                        symbol_changes.append({"symbol_id": sym_id, "kind": "class", "change": "DELETED", "file": py_rel})
                for sym_id, _s_data in self._map_symbols.get("functions", {}).items():
                    if sym_id.startswith(py_rel + "::"):
                        symbol_changes.append({"symbol_id": sym_id, "kind": "function", "change": "DELETED", "file": py_rel})
            else:
                try:
                    with open(py_full, encoding="utf-8", errors="replace") as pf:
                        tree = ast.parse(pf.read(), filename=py_rel)
                    current_classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
                    current_funcs = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

                    map_classes = {s_data["name"] for sym_id, s_data in self._map_symbols.get("classes", {}).items() if sym_id.startswith(py_rel + "::")}
                    map_funcs = {s_data["name"] for sym_id, s_data in self._map_symbols.get("functions", {}).items() if sym_id.startswith(py_rel + "::")}

                    for c in current_classes - map_classes:
                        symbol_changes.append({"symbol_id": f"{py_rel}::{c}", "kind": "class", "change": "ADDED", "file": py_rel})
                    for c in map_classes - current_classes:
                        symbol_changes.append({"symbol_id": f"{py_rel}::{c}", "kind": "class", "change": "REMOVED", "file": py_rel})

                    for fn in current_funcs - map_funcs:
                        symbol_changes.append({"symbol_id": f"{py_rel}::{fn}", "kind": "function", "change": "ADDED", "file": py_rel})
                    for fn in map_funcs - current_funcs:
                        symbol_changes.append({"symbol_id": f"{py_rel}::{fn}", "kind": "function", "change": "REMOVED", "file": py_rel})
                except Exception as ast_err:
                    symbol_changes.append({"file": py_rel, "change": "PARSE_ERROR", "error": str(ast_err)})

        # 4. API Drift Analysis
        api_changes: list[dict[str, Any]] = []
        for f in modified_files:
            if "router" in f["path"].lower() or "server.py" in f["path"].lower():
                api_changes.append({
                    "file": f["path"],
                    "status": "AFFECTED_BY_FILE_MODIFICATION",
                    "map_routes_impact": [r for r in self._map_apis.get("http_routes", []) if r.get("file") == f["path"]],
                })

        # 5. Database Drift Analysis
        db_changes: list[dict[str, Any]] = []
        for db_rel, db_info in self._map_databases.get("databases", {}).items():
            db_full = self._root_dir / db_rel.replace("/", os.sep)
            if not db_full.exists():
                db_changes.append({"database": db_rel, "status": "MISSING_DATABASE_FILE"})
            else:
                try:
                    conn = sqlite3.connect(f"file:{db_full}?mode=ro", uri=True)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    curr_tables = {row[0] for row in cursor.fetchall()}
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
                    curr_triggers = {row[0] for row in cursor.fetchall()}
                    conn.close()

                    map_tables = set(db_info.get("tables", {}).keys())
                    map_triggers = {t.get("name") if isinstance(t, dict) else str(t) for t in db_info.get("triggers", [])}

                    if curr_tables != map_tables:
                        db_changes.append({
                            "database": db_rel,
                            "change": "TABLES_MISMATCH",
                            "added_tables": list(curr_tables - map_tables),
                            "removed_tables": list(map_tables - curr_tables),
                        })
                    if curr_triggers != map_triggers:
                        db_changes.append({
                            "database": db_rel,
                            "change": "TRIGGERS_MISMATCH",
                            "added_triggers": list(curr_triggers - map_triggers),
                            "removed_triggers": list(map_triggers - curr_triggers),
                        })
                except Exception as db_err:
                    db_changes.append({"database": db_rel, "status": "ACCESS_ERROR", "error": str(db_err)})

        # 6. Mathematical Reconciliation
        total_map_files = len(self._map_hashes)
        total_physical_files = len(physical_files_set)

        count_unchanged = len(unchanged_files)
        count_modified = len(modified_files)
        count_missing = len(missing_files)
        count_new = len(new_files)
        count_unknown = len(unknown_files)

        sum_map_parts = count_unchanged + count_modified + count_missing + count_unknown
        eq1_passed = (total_map_files == sum_map_parts)

        known_physical = count_unchanged + count_modified + count_unknown
        sum_physical_parts = known_physical + count_new
        eq2_passed = (total_physical_files == sum_physical_parts)

        reconciliation_data = {
            "equation_1_map_files": {
                "formula": "map_files == unchanged + modified + missing + unknown",
                "map_files": total_map_files,
                "unchanged": count_unchanged,
                "modified": count_modified,
                "missing": count_missing,
                "unknown": count_unknown,
                "sum": sum_map_parts,
                "passed": eq1_passed,
            },
            "equation_2_physical_files": {
                "formula": "physical_files == (unchanged + modified + unknown) + new",
                "physical_files": total_physical_files,
                "known_physical": known_physical,
                "new": count_new,
                "sum": sum_physical_parts,
                "passed": eq2_passed,
            },
            "all_reconciliations_passed": eq1_passed and eq2_passed,
        }

        # 7. Final Verdict Computation
        if not (eq1_passed and eq2_passed):
            verdict = DriftVerdict.CRITICAL_DRIFT
            msg = "Reconciliation equations failed! Count mismatch between physical filesystem and knowledge map."
        elif count_unknown > 0:
            verdict = DriftVerdict.UNKNOWN
            msg = f"Detection completed with {count_unknown} inaccessible files."
        elif count_modified > 0 or count_missing > 0 or count_new > 0 or len(symbol_changes) > 0 or len(db_changes) > 0:
            verdict = DriftVerdict.DRIFT_DETECTED
            msg = (
                f"Drift detected: {count_modified} modified, {count_new} new, "
                f"{count_missing} missing file(s), {len(symbol_changes)} symbol change(s)."
            )
        else:
            verdict = DriftVerdict.NO_DRIFT
            msg = "No drift detected. Physical filesystem matches Self-Knowledge Map 100%."

        metrics = {
            "physical_files_examined": total_physical_files,
            "knowledge_map_files": total_map_files,
            "unchanged_files_count": count_unchanged,
            "modified_files_count": count_modified,
            "new_files_count": count_new,
            "missing_files_count": count_missing,
            "unknown_files_count": count_unknown,
            "symbol_changes_count": len(symbol_changes),
            "api_changes_count": len(api_changes),
            "database_changes_count": len(db_changes),
        }

        file_changes_summary = {
            "unchanged": count_unchanged,
            "modified": count_modified,
            "new": count_new,
            "missing": count_missing,
            "unknown": count_unknown,
        }

        written_artifacts = []
        if write_artifacts:
            self._drift_dir.mkdir(parents=True, exist_ok=True)

            p1 = self._drift_dir / "DRIFT_FILE_CHANGES.json"
            with open(p1, "w", encoding="utf-8") as f:
                json.dump({
                    "summary": file_changes_summary,
                    "modified_files": modified_files,
                    "new_files": new_files,
                    "missing_files": missing_files,
                    "unknown_files": unknown_files,
                }, f, indent=2)
            written_artifacts.append("DRIFT_FILE_CHANGES.json")

            p2 = self._drift_dir / "DRIFT_SYMBOL_CHANGES.json"
            with open(p2, "w", encoding="utf-8") as f:
                json.dump({"count": len(symbol_changes), "changes": symbol_changes}, f, indent=2)
            written_artifacts.append("DRIFT_SYMBOL_CHANGES.json")

            p3 = self._drift_dir / "DRIFT_API_CHANGES.json"
            with open(p3, "w", encoding="utf-8") as f:
                json.dump({"count": len(api_changes), "changes": api_changes}, f, indent=2)
            written_artifacts.append("DRIFT_API_CHANGES.json")

            p4 = self._drift_dir / "DRIFT_DATABASE_CHANGES.json"
            with open(p4, "w", encoding="utf-8") as f:
                json.dump({"count": len(db_changes), "changes": db_changes}, f, indent=2)
            written_artifacts.append("DRIFT_DATABASE_CHANGES.json")

            p5 = self._drift_dir / "DRIFT_VERIFICATION.json"
            with open(p5, "w", encoding="utf-8") as f:
                json.dump(reconciliation_data, f, indent=2)
            written_artifacts.append("DRIFT_VERIFICATION.json")

            report_dict = {
                "verdict": verdict.value,
                "generated_at_utc": now_utc,
                "metrics": metrics,
                "reconciliation": reconciliation_data,
                "file_changes_summary": file_changes_summary,
                "symbol_changes_count": len(symbol_changes),
                "api_changes_count": len(api_changes),
                "db_changes_count": len(db_changes),
                "artifacts_index": written_artifacts + ["DRIFT_SUMMARY.md", "DRIFT_REPORT.json"],
            }
            p6 = self._drift_dir / "DRIFT_REPORT.json"
            with open(p6, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2)
            written_artifacts.append("DRIFT_REPORT.json")

            summary_md = f"""# E-ZZIO OS — Forensic Drift Detection Summary
**Generated At (UTC)**: {now_utc}
**Calculated Verdict**: `{verdict.value}`

---

## 📊 High-Level Metrics
| Metric | Value | Description |
| :--- | :--- | :--- |
| **Physical Files Examined** | **{total_physical_files}** | Total files currently on disk |
| **Knowledge Map Baseline** | **{total_map_files}** | Baseline files registered in Map v1.0.0 |
| **Unchanged Files** | **{count_unchanged}** | Exact SHA-256 and size match |
| **Modified Files** | **{count_modified}** | SHA-256 mismatch vs Map |
| **New Files** | **{count_new}** | Files present on disk, absent in Map |
| **Missing Files** | **{count_missing}** | Files in Map, deleted on disk |
| **Symbol Changes** | **{len(symbol_changes)}** | AST-detected class/function diffs |
| **API Changes** | **{len(api_changes)}** | Affected router/server files |
| **Database Schema Diffs**| **{len(db_changes)}** | Table/trigger alterations |

---

## ⚖️ Mathematical Reconciliation
* **Equation 1 (Map Files)**: `{total_map_files} == {count_unchanged} + {count_modified} + {count_missing} + {count_unknown}` -> **{'PASSED' if eq1_passed else 'FAILED'}**
* **Equation 2 (Physical Files)**: `{total_physical_files} == {known_physical} + {count_new}` -> **{'PASSED' if eq2_passed else 'FAILED'}**

---

## 📜 Verdict Rationale
{msg}
"""
            p7 = self._drift_dir / "DRIFT_SUMMARY.md"
            with open(p7, "w", encoding="utf-8") as f:
                f.write(summary_md)
            written_artifacts.append("DRIFT_SUMMARY.md")

        return DriftResult(
            verdict=verdict,
            generated_at_utc=now_utc,
            metrics=metrics,
            reconciliation=reconciliation_data,
            file_changes_summary=file_changes_summary,
            symbol_changes_count=len(symbol_changes),
            api_changes_count=len(api_changes),
            db_changes_count=len(db_changes),
            artifacts_written=written_artifacts,
            evidence_path=str(self._drift_dir),
            message=msg,
        )
