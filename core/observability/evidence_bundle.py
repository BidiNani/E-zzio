"""
core/observability/evidence_bundle.py — Export reproducible Evidence Bundles for missions.
Generates structured JSON artifacts under runtime/evidence/<mission_id>/
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from typing import Any


class EvidenceBundleBuilder:
    """Construit et persiste un paquet de preuves complet et reproductible pour une mission."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio", evidence_base_dir: str | None = None):
        self.workspace_root = os.path.abspath(workspace_root)
        self.evidence_base_dir = os.path.abspath(
            evidence_base_dir or os.path.join(self.workspace_root, "runtime", "evidence")
        )

    def create_bundle(
        self,
        mission_id: str,
        mission_data: dict[str, Any] | None = None,
        timeline: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        checkpoints: list[dict[str, Any]] | None = None,
        validation: dict[str, Any] | None = None,
        audit_refs: list[str] | None = None,
        changed_files: list[str] | None = None,
        tests: dict[str, Any] | None = None,
        final_status: str = "COMPLETED",
    ) -> dict[str, str]:
        """Écrit tous les artefacts requis dans runtime/evidence/<mission_id>/ et retourne les chemins."""
        bundle_dir = os.path.join(self.evidence_base_dir, mission_id)
        os.makedirs(bundle_dir, exist_ok=True)

        environment_data = {
            "os": platform.platform(),
            "python_version": sys.version,
            "executable": sys.executable,
            "working_directory": self.workspace_root,
            "timestamp": time.time(),
        }

        files_to_write = {
            "mission.json": mission_data or {"mission_id": mission_id, "status": final_status},
            "timeline.json": timeline or [{"timestamp": time.time(), "event": "bundle_created"}],
            "decisions.json": decisions or [],
            "checkpoints.json": checkpoints or [],
            "validation.json": validation or {"verified": True, "proof_type": "STRUCTURAL"},
            "audit_refs.json": audit_refs or [],
            "changed_files.json": changed_files or [],
            "tests.json": tests or {"tests_run": 0, "tests_passed": 0},
            "environment.json": environment_data,
            "final.json": {
                "mission_id": mission_id,
                "final_status": final_status,
                "exported_at": time.time(),
                "artifact_count": 10,
            },
        }

        exported_paths = {}
        for filename, data in files_to_write.items():
            path = os.path.join(bundle_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            exported_paths[filename] = path

        return exported_paths
