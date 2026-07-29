import os
from pathlib import Path

SAFE_ROOT = Path("G:/AI/E-zzio/workspace").resolve()

class ActionToolbox:
    def _safe_path(self, user_path):
        SAFE_ROOT.mkdir(parents=True, exist_ok=True)
        candidate = (SAFE_ROOT / str(user_path)).resolve()
        if not str(candidate).startswith(str(SAFE_ROOT)):
            raise ValueError("Chemin refusé : hors sandbox E-ZZIO/workspace")
        return candidate

    def create_file(self, filename, content):
        path = self._safe_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        return f"Fichier créé dans la sandbox : {path}"

    def create_folder(self, foldername):
        path = self._safe_path(foldername)
        path.mkdir(parents=True, exist_ok=True)
        return f"Dossier prêt dans la sandbox : {path}"

    def list_files(self, path="."):
        safe = self._safe_path(path)
        if not safe.exists():
            return f"Chemin introuvable dans la sandbox : {safe}"
        return "\n".join(os.listdir(safe))

toolbox = ActionToolbox()
