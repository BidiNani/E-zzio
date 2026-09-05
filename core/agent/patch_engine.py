"""E-ZZIO Coding Agent — Surgical Patch & Diff Engine with Snapshot & Audit."""
from __future__ import annotations
import os
import time
import json
import shutil
from typing import Optional


class PatchEngine:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.snapshots_dir = os.path.join(self.workspace_root, "state", "snapshots")
        self.audit_dir = os.path.join(self.workspace_root, "state", "audit")
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.audit_dir, exist_ok=True)

    def _resolve_path(self, rel_path: str) -> str:
        return rel_path if os.path.isabs(rel_path) else os.path.join(self.workspace_root, rel_path)

    def _log_audit(self, action: str, rel_path: str, status: str, details: Optional[str] = None) -> None:
        audit_file = os.path.join(self.audit_dir, "auto_modifications.jsonl")
        entry = {
            "timestamp": time.time(),
            "action": action,
            "file": rel_path,
            "status": status,
            "details": details or "",
        }
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def create_snapshot(self, rel_path: str) -> Optional[str]:
        """Crée une copie de sauvegarde .bak du fichier avant modification."""
        full_path = self._resolve_path(rel_path)
        if not os.path.exists(full_path):
            return None
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        snap_path = os.path.join(self.snapshots_dir, f"{safe_name}_{int(time.time() * 1000)}.bak")
        shutil.copy2(full_path, snap_path)
        return snap_path

    def write_file(self, rel_path: str, content: str) -> str:
        """Écrit ou crée un fichier dans le workspace."""
        full_path = self._resolve_path(rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if os.path.exists(full_path):
            self.create_snapshot(rel_path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        self._log_audit("write_file", rel_path, "SUCCESS")
        return f"[SUCCESS] Fichier écrit : {rel_path}"

    def rollback(self, rel_path: str) -> bool:
        """Restaure le dernier snapshot disponible pour ce fichier."""
        full_path = self._resolve_path(rel_path)
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        matches = sorted([
            f for f in os.listdir(self.snapshots_dir)
            if f.startswith(safe_name) and f.endswith(".bak")
        ])
        if not matches:
            return False
        latest_snap = os.path.join(self.snapshots_dir, matches[-1])
        shutil.copy2(latest_snap, full_path)
        self._log_audit("rollback", rel_path, "RESTORED", details=f"From {matches[-1]}")
        return True

    def apply_search_replace(self, rel_path: str, search_block: str, replace_block: str) -> str:
        """Applique un patch chirurgical par recherche et remplacement de bloc exact avec snapshot automatique."""
        full_path = self._resolve_path(rel_path)

        if not os.path.exists(full_path):
            self._log_audit("apply_patch", rel_path, "FAILED", details="File not found")
            return f"[ERROR] Fichier cible introuvable pour patch : {rel_path}"

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if search_block not in content:
            self._log_audit("apply_patch", rel_path, "FAILED", details="Search block not found")
            return f"[ERROR] Le bloc de recherche exact est introuvable dans {rel_path}. Échec du patch."

        snap = self.create_snapshot(rel_path)
        new_content = content.replace(search_block, replace_block, 1)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        self._log_audit("apply_patch", rel_path, "APPLIED", details=f"Snapshot at {snap}")
        return f"[SUCCESS] Patch chirurgical appliqué avec succès sur {rel_path}. Snapshot: {snap}"
