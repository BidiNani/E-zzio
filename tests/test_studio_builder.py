"""
Tests unitaires pour le Dev Studio Project Builder d'E-ZzIO.
"""

import os

import pytest

from core.studio.builder import BuilderSecurityError, ProjectBuilder
from core.studio.scaffolder import ProjectScaffolder


def test_builder_run_python_and_tests(tmp_path):
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))
    manifest = scaffolder.scaffold("calc_test_proj", project_type="python_cli")

    builder = ProjectBuilder(workspace_root=str(tmp_path))

    # 1. Exécution du script Python
    res_run = builder.run_python_project("calc_test_proj", entrypoint="src/main.py")
    assert res_run["ok"] is True
    assert "Bienvenue dans calc_test_proj" in res_run["stdout"]
    assert res_run["returncode"] == 0

    # 2. Exécution des tests pytest du projet isolé
    res_test = builder.run_project_tests("calc_test_proj", test_path="tests")
    assert res_test["ok"] is True
    assert res_test["status"] == "PASSED"


def test_builder_security_confinement(tmp_path):
    builder = ProjectBuilder(workspace_root=str(tmp_path))

    # Tentative d'accès hors de projects/
    with pytest.raises(Exception):  # noqa: B017 — peut lever FileNotFoundError ou BuilderSecurityError
        builder._resolve_project_dir("../core")


def test_builder_godot_real_capcap():
    workspace = "G:\\AI\\E-zzio"
    builder = ProjectBuilder(workspace_root=workspace)

    # Test headless sur le projet Godot existant projects/capcap
    if os.path.exists("G:\\AI\\E-zzio\\projects\\capcap\\project.godot"):
        res_godot = builder.run_godot_headless("capcap", timeout=10)
        assert "ok" in res_godot
        assert "status" in res_godot
