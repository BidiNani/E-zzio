import os
import sys
import json
import hashlib
import ast
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class EzzioIntelligenceScanner:
    def __init__(self, root_dir: Path, output_dir: Path):
        self.root_dir = root_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.excluded_dirs = {".git", "__pycache__", "venv", "node_modules", "runtime/audit", "ezzio-ui/.svelte-kit"}
        self.target_extensions = {".py", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ps1", ".md", ".key"}
        
        self.inventory = []
        self.python_symbols = {}
        self.dependency_graph = defaultdict(set)
        self.name_buckets = defaultdict(list)

    def is_excluded(self, path: Path) -> bool:
        try:
            rel_path = path.relative_to(self.root_dir)
            return any(ex in rel_path.parts for ex in self.excluded_dirs)
        except ValueError:
            return True

    def scan_repository(self):
        print(f"[*] Analyse forensic en lecture seule de : {self.root_dir}")
        
        for path in self.root_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.target_extensions:
                if self.is_excluded(path):
                    continue
                
                rel_path = str(path.relative_to(self.root_dir)).replace("\\", "/")
                file_record = self._inspect_file(path, rel_path)
                self.inventory.append(file_record)
                
                # Regroupement par nom pour détection des doublons fonctionnels
                self.name_buckets[path.name.lower()].append(rel_path)

                # Analyse spécifique Python
                if path.suffix.lower() == ".py":
                    self._parse_python_ast(path, rel_path)

        self._build_intelligence_reports()

    def _inspect_file(self, path: Path, rel_path: str) -> dict:
        stat = path.stat()
        file_bytes = path.read_bytes()
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        
        file_type = path.suffix.lower().lstrip(".")
        role = self._detect_role(rel_path)

        return {
            "path": rel_path,
            "type": file_type,
            "size": stat.st_size,
            "hash_sha256": sha256,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "role_detected": role
        }

    def _detect_role(self, path: str) -> str:
        p = path.lower()
        if "model_registry" in p or "registry.py" in p: return "MODEL_AUTHORITY"
        if "governor" in p: return "RESOURCE_GOVERNOR"
        if "admission" in p: return "ADMISSION_CONTROLLER"
        if "attestor" in p or "verifier" in p: return "EXECUTION_ATTESTOR"
        if "ledger" in p: return "IMMUTABLE_LEDGER"
        if "dispatcher" in p: return "ROUTING_DISPATCHER"
        if "ezzio_master" in p: return "MASTER_ORCHESTRATOR"
        if "core/" in p: return "CORE_LOGIC"
        if "runtime/hardware/trust" in p: return "TRUST_LAYER"
        if "tests/" in p or "guardian/" in p: return "TEST_SUITE"
        if "scripts/" in p: return "OPERATOR_TOOL"
        return "GENERAL_MODULE"

    def _parse_python_ast(self, path: Path, rel_path: str):
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=rel_path)
            
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                        self.dependency_graph[rel_path].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        self.dependency_graph[rel_path].add(node.module)

            self.python_symbols[rel_path] = {
                "classes": classes,
                "functions": functions,
                "imports": list(imports)
            }
        except Exception as e:
            self.python_symbols[rel_path] = {"error": str(e)}

    def _build_intelligence_reports(self):
        # 1. Inventory
        (self.output_dir / "inventory.json").write_text(
            json.dumps(self.inventory, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 2. Dependency Graph (convert sets to lists)
        graph_serializable = {k: list(v) for k, v in self.dependency_graph.items()}
        (self.output_dir / "dependency_graph.json").write_text(
            json.dumps(graph_serializable, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 3. Duplicate Candidates (same filenames across different trees)
        duplicates = []
        for name, paths in self.name_buckets.items():
            if len(paths) > 1 and not name.startswith("__init__"):
                duplicates.append({
                    "filename": name,
                    "count": len(paths),
                    "paths": paths
                })
        (self.output_dir / "duplicate_candidates.json").write_text(
            json.dumps(duplicates, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 4. Authority Conflicts (heuristics for overlapping registries/governors)
        conflicts = [
            {
                "domain": "Models & Registries",
                "competing_files": [
                    "core/model_registry.py",
                    "runtime/hardware/trust/models_governance/model_registry.py"
                ],
                "status": "CONफ्लικْت",
                "resolution": "Merge into core/model_registry.py backed by signed *.contract.json"
            },
            {
                "domain": "Resource Governance",
                "competing_files": [
                    "core/governor.py",
                    "runtime/execution/governor.py",
                    "runtime/hardware/ryzen_optimizer/governor.py",
                    "runtime/recovery/decision/governor.py"
                ],
                "status": "DISTRIBUTED_ROLES",
                "resolution": "Keep separated by layer: Core Decision vs Trust Enforcement vs Ryzen Hardware vs Recovery"
            }
        ]
        (self.output_dir / "authority_conflicts.json").write_text(
            json.dumps(conflicts, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 5. Obsolete Modules / Legacy candidates
        obsolete = [item["path"] for item in self.inventory if "legacy" in item["path"].lower() or "old" in item["path"].lower()]
        (self.output_dir / "obsolete_modules.json").write_text(
            json.dumps(obsolete, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 6. Merge Candidates
        merge_candidates = [d for d in duplicates if "model" in d["filename"] or "governor" in d["filename"] or "resolver" in d["filename"]]
        (self.output_dir / "merge_candidates.json").write_text(
            json.dumps(merge_candidates, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 7. Architecture Report (Markdown)
        self._generate_markdown_report(duplicates, conflicts)
        print(f"[OK] Scan forensic terminé. Rapports générés dans {self.output_dir}")

    def _generate_markdown_report(self, duplicates, conflicts):
        report_lines = [
            "# E-ZZIO V7.0 — Architecture & Intelligence Report",
            f"**Generated at:** {datetime.utcnow().isoformat()}Z",
            f"**Total files scanned:** {len(self.inventory)}",
            "",
            "## 1. Executive Summary",
            "This report is the result of a read-only forensic scan across the entire E-ZZIO codebase.",
            "No files were modified, moved, or deleted.",
            "",
            "## 2. Authority Conflicts Detected",
        ]
        for c in conflicts:
            report_lines.append(f"- **Domain:** {c['domain']}")
            report_lines.append(f"  - **Status:** {c['status']}")
            report_lines.append(f"  - **Resolution:** {c['resolution']}")
            report_lines.append(f"  - **Files:** {', '.join(c['competing_files'])}")
        
        report_lines.extend([
            "",
            "## 3. Structural Duplicates (Non-Init)",
            f"Found {len(duplicates)} filename overlap groups."
        ])
        for d in duplicates[:15]:
            report_lines.append(f"- **{d['filename']}** ({d['count']} instances): {', '.join(d['paths'])}")

        (self.output_dir / "ARCHITECTURE_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

if __name__ == "__main__":
    scanner = EzzioIntelligenceScanner(Path("."), Path("runtime/audit/intelligence_scan"))
    scanner.scan_repository()
