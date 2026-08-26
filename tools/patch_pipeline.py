import os
import shutil
import py_compile
import traceback
from typing import Dict, Any
from tools.guard import is_path_allowed


class PatchPipeline:
    """Pipeline industriel pour modifier des fichiers avec validation syntaxique et rollback."""

    @classmethod
    def apply_patch(cls, file_path: str, new_content: str) -> Dict[str, Any]:
        """Remplace atomiquement le contenu d'un fichier avec validation et auto-rollback."""
        target_path = os.path.abspath(file_path)
        filename = os.path.basename(target_path)

        # Guard : confinement au projet + liste noire unifiée (voir guard.py)
        allowed, msg = is_path_allowed(target_path)
        if not allowed:
            return {"success": False, "error": f"SÉCURITÉ: {msg}"}

        if target_path.endswith(".sqlite3"):
            return {"success": False, "error": f"SÉCURITÉ: Modification de '{filename}' strictement interdite."}

        backup_path = target_path + ".bak"
        tmp_path = target_path + ".tmp"
        file_exists = os.path.exists(target_path)

        try:
            if file_exists:
                shutil.copy2(target_path, backup_path)

            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Auto-Check Syntaxique (Règle 9 : Détection/Correction)
            if target_path.endswith(".py"):
                try:
                    py_compile.compile(tmp_path, doraise=True)
                except py_compile.PyCompileError as e:
                    os.remove(tmp_path)
                    return {"success": False, "error": f"Erreur de syntaxe interceptée (Rollback effectué) :\n{str(e)}"}

            os.replace(tmp_path, target_path)
            return {"success": True, "message": f"Fichier {file_path} patché avec succès."}

        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if file_exists and os.path.exists(backup_path):
                shutil.copy2(backup_path, target_path)
            return {"success": False, "error": f"Erreur critique I/O : {traceback.format_exc()}"}


patch_pipeline = PatchPipeline()
