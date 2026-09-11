"""
Tests unitaires et d'intégration pour le DevStudioAgent d'E-ZzIO.
"""

import os
import shutil
import pytest
from core.studio.studio_agent import DevStudioAgent


def test_dev_studio_intent_classification():
    agent = DevStudioAgent(workspace_root="G:\\AI\\E-zzio")

    # 1. Détection jeu Godot
    godot_spec = agent.classify_project_intent("E-zzio, fais-moi un jeu de snake en Godot")
    assert godot_spec["project_type"] == "godot"
    assert "snake" in godot_spec["project_name"]

    # 2. Détection jeu Pygame
    pygame_spec = agent.classify_project_intent("Code-moi un jeu de pong 2d en python pygame")
    assert pygame_spec["project_type"] == "pygame"
    assert "pong" in pygame_spec["project_name"]

    # 3. Détection app web légère
    web_spec = agent.classify_project_intent("Crée une application web de dashboard météo en HTML CSS")
    assert web_spec["project_type"] == "web_light"

    # 4. Détection outil CLI Python par défaut
    cli_spec = agent.classify_project_intent("Fais-moi un outil de suivi de dépenses en CLI")
    assert cli_spec["project_type"] == "python_cli"


def test_dev_studio_end_to_end_pipeline(tmp_path):
    workspace = str(tmp_path)
    agent = DevStudioAgent(workspace_root=workspace)

    # Lancement d'un pipeline complet "Calculateur de TVA"
    prompt = "Code-moi une calculatrice de TVA en CLI"
    res = agent.build_project_pipeline(prompt)

    assert res["ok"] is True
    assert res["status"] == "VERIFIED_OPERATIONAL"
    assert os.path.exists(res["path"])
    assert "calculatrice_tva" in res["project_name"]
    assert "python src/main.py" in res["launch_command"]
