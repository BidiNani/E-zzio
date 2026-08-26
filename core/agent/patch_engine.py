"""E-ZZIO Coding Agent — Surgical Patch & Diff Engine."""
from __future__ import annotations
import os

class PatchEngine:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    def apply_search_replace(self, rel_path: str, search_block: str, replace_block: str) -> str:
        """Applique un patch chirurgical par recherche et remplacement de bloc exact."""
        full_path = rel_path if os.path.isabs(rel_path) else os.path.join(self.workspace_root, rel_path)
        
        if not os.path.exists(full_path):
            return f"[ERROR] Fichier cible introuvable pour patch : {rel_path}"

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if search_block not in content:
            return f"[ERROR] Le bloc de recherche exact est introuvable dans {rel_path}. Échec du patch."

        new_content = content.replace(search_block, replace_block, 1)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"[SUCCESS] Patch chirurgical appliqué avec succès sur {rel_path}"
