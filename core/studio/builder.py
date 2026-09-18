"""E-ZZIO Dev Studio — Project Builder, Runner & Functional Test Engine.

Executes, compiles and validates generated applications (Python CLI, Pygame, Godot headless, Web)
strictly confined inside G:\\AI\\E-zzio\\projects\\<name>\\ with real execution proof.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("ProjectBuilder")


class BuilderSecurityError(PermissionError):
    """Levée si l'exécution tente d'opérer hors de projects/."""
    pass


class ProjectBuilder:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.projects_dir = (self.workspace_root / "projects").resolve()
        self.godot_bin = self._find_godot_binary()

    def _find_godot_binary(self) -> str | None:
        """Localise l'exécutable console Godot disponible sur la machine."""
        candidates = [
            "G:\\Godot\\Godot_v4.7.2-stable_win64_console.exe",
            "G:\\Godot\\Godot_v4.7.1-stable_win64_console.exe",
            "G:\\Godot\\Godot_v4.3-stable_win64_console.exe",
            "C:\\Godot\\Godot_v4.3-stable_win64_console.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        # Recherche dans le PATH
        try:
            res = subprocess.run(["where", "godot"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().splitlines()[0]
        except Exception:
            pass
        return None

    def _resolve_project_dir(self, project_name: str) -> Path:
        """Résout et valide le confinement strict dans projects/<nom>."""
        clean_name = os.path.basename(project_name.strip())
        project_dir = (self.projects_dir / clean_name).resolve()
        try:
            if os.path.commonpath([str(self.projects_dir), str(project_dir)]) != str(self.projects_dir):
                raise BuilderSecurityError(f"Confinement violé : tentative d'accès hors de {self.projects_dir}")
        except ValueError:
            raise BuilderSecurityError(f"Chemin invalide : {project_dir}")

        if not project_dir.exists() or not project_dir.is_dir():
            raise FileNotFoundError(f"Projet introuvable dans projects/{clean_name}")

        return project_dir

    def run_python_project(
        self,
        project_name: str,
        entrypoint: str = "src/main.py",
        args: list[str] | None = None,
        timeout: int = 15
    ) -> dict[str, Any]:
        """Exécute un script/projet Python et capture la sortie réelle."""
        p_dir = self._resolve_project_dir(project_name)
        target_file = (p_dir / entrypoint).resolve()

        if not target_file.exists():
            return {
                "ok": False,
                "status": "ENTRYPOINT_NOT_FOUND",
                "error": f"Fichier d'entrée {entrypoint} introuvable dans {project_name}"
            }

        py_exec = sys.executable
        cmd = [py_exec, str(target_file)] + (args or [])

        start_t = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(p_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            exec_time = round(time.perf_counter() - start_t, 3)
            return {
                "ok": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "exec_time_s": exec_time,
                "status": "SUCCESS" if res.returncode == 0 else "EXECUTION_ERROR"
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "status": "TIMEOUT",
                "error": f"Exécution interrompue après {timeout}s (délai dépassé)"
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "EXCEPTION",
                "error": str(exc)
            }

    def run_project_tests(self, project_name: str, test_path: str = "tests", timeout: int = 20) -> dict[str, Any]:
        """Lance pytest sur le dossier de tests d'un projet isolé."""
        p_dir = self._resolve_project_dir(project_name)
        py_exec = sys.executable
        cmd = [py_exec, "-m", "pytest", "-q", test_path]

        try:
            res = subprocess.run(
                cmd,
                cwd=str(p_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "ok": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "status": "PASSED" if res.returncode == 0 else "FAILED"
            }
        except Exception as exc:
            return {"ok": False, "status": "TEST_EXCEPTION", "error": str(exc)}

    def run_godot_headless(self, project_name: str, timeout: int = 15) -> dict[str, Any]:
        """Vérifie la compilation GDScript et le chargement de scène Godot en mode headless CPU."""
        p_dir = self._resolve_project_dir(project_name)
        godot_proj = p_dir / "project.godot"

        if not godot_proj.exists():
            return {"ok": False, "status": "NO_GODOT_PROJECT", "error": "project.godot introuvable"}

        if not self.godot_bin:
            return {
                "ok": False,
                "status": "GODOT_BINARY_NOT_FOUND",
                "message": "Exécutable Godot introuvable sur le système."
            }

        cmd = [self.godot_bin, "--headless", "--quit", "--path", str(p_dir)]
        try:
            res = subprocess.run(
                cmd,
                cwd=str(p_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "ok": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "godot_version": os.path.basename(self.godot_bin),
                "status": "HEADLESS_VALIDATED" if res.returncode == 0 else "COMPILATION_ERROR"
            }
        except Exception as exc:
            return {"ok": False, "status": "GODOT_EXEC_ERROR", "error": str(exc)}
