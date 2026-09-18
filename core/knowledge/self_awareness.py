"""
E-ZZIO OS — Sovereign Self-Awareness Gateway (Introspection Engine)
Provides structured, provable, read-only introspection capabilities grounded exclusively
in the Self-Knowledge Map artifacts (_forensic/knowledge/).
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("ezzio.self_awareness")


@dataclass(frozen=True)
class IntrospectionResult:
    """
    Standardized, traceable introspection response.
    Guarantees provenance of returned knowledge without conjecture.
    """
    status: str  # "FOUND", "UNKNOWN", "ERROR"
    data: Any
    source_artifact: str | None
    target: str
    confidence: float  # 1.0 = backed by verified map artifact, 0.0 = unknown
    evidence_path: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfAwarenessGateway:
    """
    READ-ONLY Introspection Gateway.
    Exposes sovereign queries over the 11 Self-Knowledge Map artifacts in _forensic/knowledge/.
    No mutation, deletion, or execution capabilities exist in this class.
    """

    CANONICAL_ARTIFACTS = {
        "manifest": "FILE_MANIFEST.json",
        "hashes": "FILE_HASHES.json",
        "symbols": "SYMBOL_INDEX.json",
        "imports": "IMPORT_GRAPH.json",
        "dependencies": "DEPENDENCY_GRAPH.json",
        "databases": "DATABASE_MAP.json",
        "apis": "API_MAP.json",
        "tests": "TEST_COVERAGE.json",
        "gaps": "ANALYSIS_GAPS.json",
        "architecture": "ARCHITECTURE.md",
        "master": "MASTER_KNOWLEDGE.json",
    }

    def __init__(self, knowledge_dir: str | Path | None = None):
        if knowledge_dir is not None:
            self._knowledge_dir = Path(knowledge_dir).resolve()
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self._knowledge_dir = (base_dir / "_forensic" / "knowledge").resolve()

        self._cache: dict[str, Any] = {}
        self._load_errors: dict[str, str] = {}
        self._load_all_artifacts()

    def _load_all_artifacts(self) -> None:
        """Loads and parses all JSON artifacts in memory with strict validation."""
        self._cache.clear()
        self._load_errors.clear()

        for key, fname in self.CANONICAL_ARTIFACTS.items():
            if fname.endswith(".md"):
                continue
            file_path = self._knowledge_dir / fname
            if not file_path.is_file():
                self._load_errors[key] = f"Artifact missing on disk: {fname}"
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    self._cache[key] = json.load(f)
            except Exception as e:
                self._load_errors[key] = f"JSON corruption/parse error in {fname}: {e}"

    @property
    def knowledge_dir(self) -> Path:
        """Returns the active knowledge directory path (read-only)."""
        return self._knowledge_dir

    def verify_integrity(self) -> IntrospectionResult:
        """
        Validates that all canonical artifacts are present, valid JSON, and match expected root structure.
        """
        if self._load_errors:
            return IntrospectionResult(
                status="ERROR",
                data={"errors": self._load_errors, "loaded_count": len(self._cache)},
                source_artifact=None,
                target="knowledge_integrity",
                confidence=0.0,
                evidence_path=str(self._knowledge_dir),
                message=f"Integrity check failed: {len(self._load_errors)} artifacts are missing or invalid."
            )

        master_data = self._cache.get("master", {})
        integrity_status = master_data.get("integrity_status", "UNKNOWN")

        return IntrospectionResult(
            status="FOUND" if integrity_status == "SELF-KNOWLEDGE MAP COMPLETE" else "UNKNOWN",
            data={
                "integrity_status": integrity_status,
                "loaded_artifacts_count": len(self._cache),
                "artifacts_verified": list(self.CANONICAL_ARTIFACTS.values())
            },
            source_artifact=self.CANONICAL_ARTIFACTS["master"],
            target="knowledge_integrity",
            confidence=1.0 if integrity_status == "SELF-KNOWLEDGE MAP COMPLETE" else 0.5,
            evidence_path=str(self._knowledge_dir / self.CANONICAL_ARTIFACTS["master"]),
            message=f"All {len(self.CANONICAL_ARTIFACTS)} canonical artifacts are verified and accessible."
        )

    def _normalize_path(self, path_str: str) -> str:
        """Normalizes path representation to POSIX forward slashes."""
        p = path_str.replace("\\", "/").strip()
        if p.startswith("./"):
            p = p[2:]
        return p

    def get_file_metadata(self, file_path: str) -> IntrospectionResult:
        """Retrieves exact metadata for a given relative or base file path."""
        manifest = self._cache.get("manifest")
        if not manifest:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
                target=file_path,
                confidence=0.0,
                message="Manifest artifact is unavailable."
            )

        norm_path = self._normalize_path(file_path)
        if norm_path in manifest:
            return IntrospectionResult(
                status="FOUND",
                data=manifest[norm_path],
                source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
                target=norm_path,
                confidence=1.0,
                evidence_path=norm_path
            )

        matching = [meta for path, meta in manifest.items() if path.endswith("/" + norm_path) or meta.get("filename") == norm_path]
        if len(matching) == 1:
            return IntrospectionResult(
                status="FOUND",
                data=matching[0],
                source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
                target=matching[0]["path"],
                confidence=1.0,
                evidence_path=matching[0]["path"]
            )
        elif len(matching) > 1:
            return IntrospectionResult(
                status="FOUND",
                data={"multiple_matches": [m["path"] for m in matching]},
                source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
                target=file_path,
                confidence=0.8,
                message=f"Ambiguous query: found {len(matching)} matches for '{file_path}'."
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
            target=file_path,
            confidence=0.0,
            message=f"File '{file_path}' is not present in the physical file manifest."
        )

    def get_file_hash(self, file_path: str) -> IntrospectionResult:
        """Retrieves verified SHA-256 hash for a specific file."""
        hashes = self._cache.get("hashes")
        if not hashes:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["hashes"],
                target=file_path,
                confidence=0.0,
                message="Hashes artifact is unavailable."
            )

        norm_path = self._normalize_path(file_path)
        if norm_path in hashes:
            return IntrospectionResult(
                status="FOUND",
                data={"sha256": hashes[norm_path], "path": norm_path},
                source_artifact=self.CANONICAL_ARTIFACTS["hashes"],
                target=norm_path,
                confidence=1.0,
                evidence_path=norm_path
            )

        matching = [(k, v) for k, v in hashes.items() if k.endswith("/" + norm_path) or Path(k).name == norm_path]
        if len(matching) == 1:
            k, v = matching[0]
            return IntrospectionResult(
                status="FOUND",
                data={"sha256": v, "path": k},
                source_artifact=self.CANONICAL_ARTIFACTS["hashes"],
                target=k,
                confidence=1.0,
                evidence_path=k
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["hashes"],
            target=file_path,
            confidence=0.0,
            message=f"No SHA-256 hash found for file '{file_path}'."
        )

    def find_files(self, query: str, category: str | None = None, limit: int = 50) -> IntrospectionResult:
        """Searches files in the manifest by substring/extension/category."""
        manifest = self._cache.get("manifest")
        if not manifest:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
                target=query,
                confidence=0.0
            )

        q_lower = query.lower()
        results = []
        for path, meta in manifest.items():
            if category and meta.get("category") != category:
                continue
            if q_lower in path.lower() or q_lower in meta.get("filename", "").lower():
                results.append({
                    "path": path,
                    "size_bytes": meta.get("size_bytes"),
                    "category": meta.get("category"),
                    "is_excluded": meta.get("is_excluded")
                })
                if len(results) >= limit:
                    break

        return IntrospectionResult(
            status="FOUND" if results else "UNKNOWN",
            data={"count": len(results), "files": results},
            source_artifact=self.CANONICAL_ARTIFACTS["manifest"],
            target=query,
            confidence=1.0 if results else 0.0,
            message=f"Found {len(results)} files matching query '{query}'."
        )

    def find_symbol(self, symbol_name: str, symbol_type: str | None = None) -> IntrospectionResult:
        """
        Searches Python classes, Python functions, or PowerShell functions by name.
        """
        symbols = self._cache.get("symbols")
        if not symbols:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["symbols"],
                target=symbol_name,
                confidence=0.0
            )

        matches = []
        s_lower = symbol_name.lower()

        if symbol_type in (None, "class", "classes"):
            for sym_id, c_data in symbols.get("classes", {}).items():
                if sym_id.lower().endswith("::" + s_lower) or c_data.get("name", "").lower() == s_lower:
                    matches.append({"kind": "python_class", "symbol_id": sym_id, "definition": c_data})

        if symbol_type in (None, "function", "functions"):
            for sym_id, f_data in symbols.get("functions", {}).items():
                if sym_id.lower().endswith("::" + s_lower) or f_data.get("name", "").lower() == s_lower:
                    matches.append({"kind": "python_function", "symbol_id": sym_id, "definition": f_data})

        if symbol_type in (None, "powershell", "powershell_function"):
            for sym_id, ps_name in symbols.get("powershell_functions", {}).items():
                if sym_id.lower().endswith("::" + s_lower) or ps_name.lower() == s_lower:
                    matches.append({"kind": "powershell_function", "symbol_id": sym_id, "name": ps_name})

        return IntrospectionResult(
            status="FOUND" if matches else "UNKNOWN",
            data={"count": len(matches), "symbols": matches},
            source_artifact=self.CANONICAL_ARTIFACTS["symbols"],
            target=symbol_name,
            confidence=1.0 if matches else 0.0,
            message=f"Found {len(matches)} symbol definition(s) for '{symbol_name}'."
        )

    def get_module_imports(self, module_path: str) -> IntrospectionResult:
        """Retrieves list of local modules imported by the specified module."""
        imports = self._cache.get("imports")
        if not imports:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["imports"],
                target=module_path,
                confidence=0.0
            )

        norm_path = self._normalize_path(module_path)
        adj = imports.get("adjacency", {})

        target_key = None
        if norm_path in adj:
            target_key = norm_path
        else:
            matching = [k for k in adj.keys() if k.endswith("/" + norm_path) or Path(k).name == norm_path]
            if len(matching) == 1:
                target_key = matching[0]

        if target_key:
            imported_modules = adj.get(target_key, [])
            return IntrospectionResult(
                status="FOUND",
                data={"module": target_key, "imports_count": len(imported_modules), "imported_modules": imported_modules},
                source_artifact=self.CANONICAL_ARTIFACTS["imports"],
                target=target_key,
                confidence=1.0,
                evidence_path=target_key
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["imports"],
            target=module_path,
            confidence=0.0,
            message=f"Module '{module_path}' not found in import graph."
        )

    def get_module_dependents(self, module_path: str) -> IntrospectionResult:
        """Retrieves list of other modules that import / depend on this module."""
        imports = self._cache.get("imports")
        if not imports:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["imports"],
                target=module_path,
                confidence=0.0
            )

        norm_path = self._normalize_path(module_path)
        rev_adj = imports.get("reverse_adjacency", {})

        target_key = None
        if norm_path in rev_adj:
            target_key = norm_path
        else:
            matching = [k for k in rev_adj.keys() if k.endswith("/" + norm_path) or Path(k).name == norm_path]
            if len(matching) == 1:
                target_key = matching[0]

        if target_key:
            dependents = rev_adj.get(target_key, [])
            return IntrospectionResult(
                status="FOUND",
                data={"module": target_key, "dependents_count": len(dependents), "dependent_modules": dependents},
                source_artifact=self.CANONICAL_ARTIFACTS["imports"],
                target=target_key,
                confidence=1.0,
                evidence_path=target_key
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["imports"],
            target=module_path,
            confidence=0.0,
            message=f"Module '{module_path}' not found in reverse import graph."
        )

    def get_api_routes(self, filter_query: str | None = None) -> IntrospectionResult:
        """Retrieves HTTP and WebSocket API routes mapped across E-ZZIO OS."""
        apis = self._cache.get("apis")
        if not apis:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["apis"],
                target="api_routes",
                confidence=0.0
            )

        http_routes = apis.get("http_routes", [])
        ws_routes = apis.get("websocket_routes", [])

        if filter_query:
            q_lower = filter_query.lower()
            http_routes = [r for r in http_routes if q_lower in r.get("path", "").lower() or q_lower in r.get("method", "").lower() or q_lower in r.get("file", "").lower()]
            ws_routes = [r for r in ws_routes if q_lower in r.get("path", "").lower() or q_lower in r.get("file", "").lower()]

        return IntrospectionResult(
            status="FOUND" if (http_routes or ws_routes) else "UNKNOWN",
            data={
                "http_routes_count": len(http_routes),
                "websocket_routes_count": len(ws_routes),
                "http_routes": http_routes,
                "websocket_routes": ws_routes
            },
            source_artifact=self.CANONICAL_ARTIFACTS["apis"],
            target=filter_query or "all_routes",
            confidence=1.0 if (http_routes or ws_routes) else 0.0
        )

    def get_database_info(self, table_or_db: str | None = None) -> IntrospectionResult:
        """Retrieves SQLite schema definitions, tables, triggers, and referencing code files."""
        db_map = self._cache.get("databases")
        if not db_map:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["databases"],
                target="database_info",
                confidence=0.0
            )

        databases = db_map.get("databases", {})
        table_usage = db_map.get("table_usage_by_file", {})

        if not table_or_db:
            return IntrospectionResult(
                status="FOUND",
                data={"databases": databases, "table_usage_by_file": table_usage},
                source_artifact=self.CANONICAL_ARTIFACTS["databases"],
                target="all_databases",
                confidence=1.0
            )

        t_lower = table_or_db.lower()
        found_tables = {}
        for db_file, db_data in databases.items():
            for tbl, tbl_info in db_data.get("tables", {}).items():
                if t_lower in tbl.lower():
                    found_tables[f"{db_file}::{tbl}"] = {
                        "table": tbl,
                        "database": db_file,
                        "schema": tbl_info,
                        "referenced_by_files": table_usage.get(tbl, [])
                    }

        if found_tables:
            return IntrospectionResult(
                status="FOUND",
                data={"tables": found_tables},
                source_artifact=self.CANONICAL_ARTIFACTS["databases"],
                target=table_or_db,
                confidence=1.0
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["databases"],
            target=table_or_db,
            confidence=0.0,
            message=f"No SQLite database or table found matching '{table_or_db}'."
        )

    def get_tests_for_module(self, module_path: str) -> IntrospectionResult:
        """Retrieves test suites covering a given source module."""
        test_cov = self._cache.get("tests")
        if not test_cov:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["tests"],
                target=module_path,
                confidence=0.0
            )

        norm_path = self._normalize_path(module_path)
        tgt_to_tests = test_cov.get("target_to_tests", {})

        target_key = None
        if norm_path in tgt_to_tests:
            target_key = norm_path
        else:
            matching = [k for k in tgt_to_tests.keys() if k.endswith("/" + norm_path) or Path(k).name == norm_path]
            if len(matching) == 1:
                target_key = matching[0]

        if target_key:
            test_files = tgt_to_tests.get(target_key, [])
            return IntrospectionResult(
                status="FOUND",
                data={"target_module": target_key, "tests_count": len(test_files), "test_files": test_files},
                source_artifact=self.CANONICAL_ARTIFACTS["tests"],
                target=target_key,
                confidence=1.0,
                evidence_path=target_key
            )

        return IntrospectionResult(
            status="UNKNOWN",
            data=None,
            source_artifact=self.CANONICAL_ARTIFACTS["tests"],
            target=module_path,
            confidence=0.0,
            message=f"No automated test files currently mapped for module '{module_path}'."
        )

    def get_analysis_gaps(self) -> IntrospectionResult:
        """Retrieves registered analysis gaps, reconciliation equations, and orphan counts."""
        gaps = self._cache.get("gaps")
        if not gaps:
            return IntrospectionResult(
                status="ERROR",
                data=None,
                source_artifact=self.CANONICAL_ARTIFACTS["gaps"],
                target="analysis_gaps",
                confidence=0.0
            )

        return IntrospectionResult(
            status="FOUND",
            data=gaps,
            source_artifact=self.CANONICAL_ARTIFACTS["gaps"],
            target="analysis_gaps",
            confidence=1.0
        )
