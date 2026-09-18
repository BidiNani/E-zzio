"""
Tests unitaires pour le Dev Studio Project Scaffolder d'E-ZzIO.
"""

import os
import shutil

import pytest

from core.studio.scaffolder import ProjectScaffolder, ScaffolderSecurityError


def test_scaffolder_python_cli(tmp_path):
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))
    manifest = scaffolder.scaffold("calculatrice_cli", project_type="python_cli", description="Outil de calcul")

    assert manifest["project_name"] == "calculatrice_cli"
    assert manifest["project_type"] == "python_cli"
    assert os.path.exists(os.path.join(manifest["path"], "src", "main.py"))
    assert os.path.exists(os.path.join(manifest["path"], "tests", "test_main.py"))
    assert os.path.exists(os.path.join(manifest["path"], "README.md"))
    assert os.path.exists(os.path.join(manifest["path"], ".git"))


def test_scaffolder_godot_and_pygame(tmp_path):
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))

    # Test Godot
    manifest_godot = scaffolder.scaffold("snake_2d", project_type="godot", description="Jeu Snake")
    assert os.path.exists(os.path.join(manifest_godot["path"], "project.godot"))

    # Test Pygame
    manifest_pygame = scaffolder.scaffold("pong_retro", project_type="pygame", description="Pong")
    assert os.path.exists(os.path.join(manifest_pygame["path"], "src", "game.py"))


def test_scaffolder_security_confinement(tmp_path):
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))

    # Tentative d'évasion vers le noyau ou la racine
    with pytest.raises(Exception):
        scaffolder.scaffold("../../../core/malicious_payload", project_type="python_cli")
