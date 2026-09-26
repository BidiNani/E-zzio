"""
core/workspace/workspace_intel.py — Sovereign Workspace Intelligence & Project Inspector (Phase A12).
Performs strictly read-only scanning, project structure discovery, and risk mapping.
STRICT INVARIANTS:
- Confined to authorized workspace root (blocks outside paths via commonpath).
- 'Test suite detected' is NEVER 'tests passed'.
- Critical file detection produces context hints, NEVER modification authorization.
- Does not replace UnifiedMemoryGateway or become Memory Authority.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger("WorkspaceIntelligence")

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".cs": "C#",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sql": "SQL",
}

DEPENDENCY_MANIFESTS = {
    "pyproject.toml": "Python (Poetry/Pip/Flit)",
    "requirements.txt": "Python (Pip)",
    "package.json": "Node.js (NPM/Yarn/Pnpm)",
    "Cargo.toml": "Rust (Cargo)",
    "go.mod": "Go (Modules)",
}


class WorkspaceIntelligence:
    """Analyseur statique et explorateur de contexte de projet confiné."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = os.path.normcase(os.path.abspath(workspace_root))

    def _is_within_workspace(self, target_path: str) -> bool:
        """Vérifie via os.path.commonpath le confinement absolu au workspace."""
        try:
            norm_target = os.path.normcase(os.path.abspath(target_path))
            return os.path.commonpath([self.workspace_root, norm_target]) == self.workspace_root
        except Exception:
            return False

    def scan(self, max_file_size_bytes: int = 10 * 1024 * 1024) -> dict[str, Any]:
        """Scan complet en lecture seule du workspace."""
        if not os.path.exists(self.workspace_root):
            raise FileNotFoundError(f"Workspace root does not exist: {self.workspace_root}")

        languages: dict[str, int] = {}
        manifests: list[str] = []
        entrypoints: list[str] = []
        critical_paths: list[str] = []
        test_files: list[str] = []
        ignored_paths: list[str] = []
        large_files: list[str] = []
        symlinks: list[str] = []

        ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}

        for root, dirs, files in os.walk(self.workspace_root):
            skipped = [d for d in dirs if d in ignore_dirs]
            for s in skipped:
                ignored_paths.append(os.path.relpath(os.path.join(root, s), self.workspace_root))
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            rel_root = os.path.relpath(root, self.workspace_root)
            if any(part in ignore_dirs for part in rel_root.split(os.sep)):
                ignored_paths.append(rel_root)
                continue

            for f in files:
                abs_f = os.path.join(root, f)
                rel_f = os.path.relpath(abs_f, self.workspace_root)

                # Confinement check
                if not self._is_within_workspace(abs_f):
                    continue

                if os.path.islink(abs_f):
                    symlinks.append(rel_f)

                # Large file detection
                try:
                    size = os.path.getsize(abs_f)
                    if size > max_file_size_bytes:
                        large_files.append(rel_f)
                except OSError:
                    continue

                # Extension & Language detection
                _, ext = os.path.splitext(f)
                ext_low = ext.lower()
                if ext_low in LANGUAGE_EXTENSIONS:
                    lang = LANGUAGE_EXTENSIONS[ext_low]
                    languages[lang] = languages.get(lang, 0) + 1

                # Manifest detection
                if f in DEPENDENCY_MANIFESTS or f.endswith(".csproj"):
                    manifests.append(rel_f)

                # Entrypoint detection
                if f.lower() in ("main.py", "app.py", "index.js", "server.js", "ezzio_cli.py", "web_server.py"):
                    entrypoints.append(rel_f)

                # Critical file detection (governance / security / state / router)
                f_low = rel_f.lower()
                if any(kw in f_low for kw in ("guard", "router", "policy", "budget", "ledger", "audit", "vault", "constitution")):
                    critical_paths.append(rel_f)

                # Test file detection
                if f.startswith("test_") and f.endswith(".py"):
                    test_files.append(rel_f)

        # Framework & Test Intelligence
        frameworks: list[str] = []
        test_commands: list[str] = []
        manifest_names = [os.path.basename(m) for m in manifests]

        if "pyproject.toml" in manifest_names or "requirements.txt" in manifest_names or "Python" in languages:
            frameworks.append("Python")
            if test_files:
                test_commands.append("pytest")
        if "package.json" in manifest_names:
            frameworks.append("Node.js")
            test_commands.append("npm test")
        if "Cargo.toml" in manifest_names:
            frameworks.append("Cargo / Rust")
            test_commands.append("cargo test")

        # Git status
        git_state = {"is_repo": False, "branch": "UNKNOWN", "clean": False}
        try:
            p_br = subprocess.run(["git", "branch", "--show-current"], cwd=self.workspace_root, capture_output=True, text=True, timeout=1)
            if p_br.returncode == 0:
                git_state["is_repo"] = True
                git_state["branch"] = p_br.stdout.strip()
                p_st = subprocess.run(["git", "status", "--porcelain"], cwd=self.workspace_root, capture_output=True, text=True, timeout=1)
                git_state["clean"] = len(p_st.stdout.strip()) == 0
        except Exception:
            pass

        return {
            "workspace_root": self.workspace_root,
            "git_state": git_state,
            "languages": languages,
            "frameworks": frameworks,
            "dependencies": manifests,
            "tests": {
                "test_suite_detected": len(test_commands) > 0,
                "test_file_count": len(test_files),
                "runner_commands": test_commands,
                "status": "DETECTED_NOT_RUN",  # HARD INVARIANT: detected != passed
            },
            "entrypoints": entrypoints,
            "critical_paths": critical_paths,
            "ignored_paths_count": len(ignored_paths),
            "large_files": large_files,
            "symlinks": symlinks,
            "risk_flags": [
                f"Contains {len(critical_paths)} critical security/governance components that require policy approval for modification."
            ] if critical_paths else [],
        }

    def generate_manifest(self, output_path: str | None = None) -> dict[str, Any]:
        """Génère workspace_manifest.json."""
        manifest = self.scan()
        if output_path:
            abs_out = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_out), exist_ok=True)
            with open(abs_out, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        return manifest

    def build_context_package(self) -> dict[str, Any]:
        """Produit un ensemble contextuel consommable par le Context Layer."""
        scan_data = self.scan()
        return {
            "workspace_context": {
                "root": scan_data["workspace_root"],
                "languages": list(scan_data["languages"].keys()),
                "frameworks": scan_data["frameworks"],
                "manifest_count": len(scan_data["dependencies"]),
            },
            "project_map": {
                "entrypoints": scan_data["entrypoints"],
                "dependencies": scan_data["dependencies"],
            },
            "test_map": scan_data["tests"],
            "risk_summary": {
                "critical_paths_count": len(scan_data["critical_paths"]),
                "sample_critical_paths": scan_data["critical_paths"][:10],
                "risk_flags": scan_data["risk_flags"],
            },
        }
