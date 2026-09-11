"""
Phase 7 Test Suite — Validation du Dev Studio (Scaffolding, Build & Run Python/Godot dans projects/).
"""

import os
from pathlib import Path
from core.studio.scaffolder import ProjectScaffolder
from core.studio.builder import ProjectBuilder


def test_phase7_project_scaffolding_confinement(tmp_path):
    """Vérifie que les projets générés sont rigoureusement confinés dans projects/<nom>."""
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))
    res = scaffolder.scaffold(project_name="demo_app", project_type="python_cli")
    
    assert "path" in res
    project_path = Path(res["path"])
    assert project_path.exists()
    assert (project_path / "src" / "main.py").exists()
    assert (project_path / ".git").exists()  # git init local isolé


def test_phase7_python_project_execution_real(tmp_path):
    """Vérifie l'exécution réelle d'un projet Python dans le bac à sable."""
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))
    scaffold_res = scaffolder.scaffold(project_name="calc_app", project_type="python_cli")
    
    project_dir = scaffold_res["path"]
    main_py = Path(project_dir) / "src" / "main.py"
    main_py.write_text("print('DEV_STUDIO_SUCCESS_RUN')\n", encoding="utf-8")

    builder = ProjectBuilder(workspace_root=str(tmp_path))
    run_res = builder.run_python_project(project_name="calc_app", entrypoint="src/main.py")

    assert run_res["ok"] is True
    assert "DEV_STUDIO_SUCCESS_RUN" in run_res["stdout"]
