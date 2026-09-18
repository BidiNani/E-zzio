"""E-ZZIO Dev Studio — Project Scaffolder & Isolated Sandbox Generator.

Creates isolated application and game project templates in G:\\AI\\E-zzio\\projects\\<name>
with independent local git repositories and zero impact on the core engine.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("ProjectScaffolder")


class ScaffolderSecurityError(PermissionError):
    """Levée en cas de tentative de création de projet hors du dossier projects/."""
    pass


class ProjectScaffolder:
    SUPPORTED_TYPES = {"python_cli", "pygame", "godot", "web_light"}

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.projects_dir = (self.workspace_root / "projects").resolve()
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """Nettoie le nom de projet et bloque toute tentative d'évasion."""
        if ".." in name or "/" in name or "\\" in name:
            raise ScaffolderSecurityError(f"[SECURITY DENY] Caractères de traversée de chemin interdits dans le nom : {name}")
        clean = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name.strip())
        return clean.strip("_") or "untitled_project"

    def scaffold(self, project_name: str, project_type: str = "python_cli", description: str = "") -> dict[str, Any]:
        """Crée l'arborescence minimale et initialise le projet dans projects/<nom>."""
        safe_name = self._sanitize_name(project_name)
        target_dir = (self.projects_dir / safe_name).resolve()

        # Confinement strict : target_dir doit être un sous-dossier direct de projects_dir
        try:
            if os.path.commonpath([str(self.projects_dir), str(target_dir)]) != str(self.projects_dir):
                raise ScaffolderSecurityError(f"Confinement violé : tentative de création hors de {self.projects_dir}")
        except ValueError:
            raise ScaffolderSecurityError(f"Chemin invalide pour le projet : {target_dir}")

        if project_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Type de projet '{project_type}' non supporté. Types valides : {self.SUPPORTED_TYPES}")

        target_dir.mkdir(parents=True, exist_ok=True)

        if project_type == "python_cli":
            manifest = self._scaffold_python_cli(target_dir, safe_name, description)
        elif project_type == "pygame":
            manifest = self._scaffold_pygame(target_dir, safe_name, description)
        elif project_type == "godot":
            manifest = self._scaffold_godot(target_dir, safe_name, description)
        elif project_type == "web_light":
            manifest = self._scaffold_web_light(target_dir, safe_name, description)
        else:
            manifest = {}

        # Initialisation git locale indépendante
        self._init_local_git(target_dir)

        return manifest

    def _init_local_git(self, project_dir: Path) -> None:
        """Initialise un dépôt git local indépendant du noyau E-ZzIO."""
        if not (project_dir / ".git").exists():
            try:
                subprocess.run(["git", "init", "-q"], cwd=str(project_dir), capture_output=True, timeout=5)
            except Exception:
                pass

    def _scaffold_python_cli(self, path: Path, name: str, desc: str) -> dict[str, Any]:
        src_dir = path / "src"
        tests_dir = path / "tests"
        src_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)

        main_py = src_dir / "main.py"
        if not main_py.exists():
            main_py.write_text(
                f'"""Projet : {name}\nDescription : {desc or "Application CLI Python"}\n"""\n\n'
                'def run() -> str:\n'
                f'    return "Bienvenue dans {name} !"\n\n'
                'if __name__ == "__main__":\n'
                '    print(run())\n',
                encoding="utf-8"
            )

        test_py = tests_dir / "test_main.py"
        if not test_py.exists():
            test_py.write_text(
                'import sys, os\n'
                'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))\n'
                'from main import run\n\n'
                'def test_run():\n'
                '    assert "Bienvenue" in run()\n',
                encoding="utf-8"
            )

        readme = path / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name}\n\n{desc}\n\n## Lancer\n`python src/main.py`\n", encoding="utf-8")

        return {
            "project_name": name,
            "project_type": "python_cli",
            "path": str(path),
            "entrypoint": "src/main.py",
            "launch_command": "python src/main.py",
            "test_command": "pytest tests/"
        }

    def _scaffold_pygame(self, path: Path, name: str, desc: str) -> dict[str, Any]:
        src_dir = path / "src"
        assets_dir = path / "assets"
        src_dir.mkdir(exist_ok=True)
        assets_dir.mkdir(exist_ok=True)

        game_py = src_dir / "game.py"
        if not game_py.exists():
            game_py.write_text(
                f'"""Jeu 2D : {name} (Pygame)\nDescription : {desc}\n"""\n'
                'import sys\n\n'
                'def init_game():\n'
                '    # Initialisation logique pour test et exécution\n'
                f'    return {{"title": "{name}", "state": "ready", "score": 0}}\n\n'
                'if __name__ == "__main__":\n'
                '    print(f"Lancement de {name}...")\n',
                encoding="utf-8"
            )

        req_txt = path / "requirements.txt"
        if not req_txt.exists():
            req_txt.write_text("pygame-ce>=2.5.0\n", encoding="utf-8")

        readme = path / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name} (Jeu Pygame)\n\n{desc}\n\n## Lancer\n`python src/game.py`\n", encoding="utf-8")

        return {
            "project_name": name,
            "project_type": "pygame",
            "path": str(path),
            "entrypoint": "src/game.py",
            "launch_command": "python src/game.py",
            "test_command": "python -c 'from src.game import init_game; assert init_game()[\"state\"] == \"ready\"'"
        }

    def _scaffold_godot(self, path: Path, name: str, desc: str) -> dict[str, Any]:
        scenes_dir = path / "scenes"
        scripts_dir = path / "scripts"
        resources_dir = path / "resources"
        scenes_dir.mkdir(exist_ok=True)
        scripts_dir.mkdir(exist_ok=True)
        resources_dir.mkdir(exist_ok=True)

        # 1. Configuration officielle project.godot (Godot 4.x)
        godot_proj = path / "project.godot"
        if not godot_proj.exists():
            godot_proj.write_text(
                '; Engine configuration file.\n'
                'config_version=5\n\n'
                '[application]\n\n'
                f'config/name="{name}"\n'
                'config/features=PackedStringArray("4.3", "Forward Plus")\n'
                'run/main_scene="res://scenes/main.tscn"\n\n'
                '[display]\n\n'
                'window/size/viewport_width=1280\n'
                'window/size/viewport_height=720\n'
                'window/stretch/mode="canvas_items"\n',
                encoding="utf-8"
            )

        # 2. Ressource personnalisée pour découplage des données (GameConfig.gd)
        cfg_script = scripts_dir / "game_config.gd"
        if not cfg_script.exists():
            cfg_script.write_text(
                'class_name GameConfig\n'
                'extends Resource\n\n'
                '@export var move_speed: float = 300.0\n'
                '@export var max_health: int = 100\n'
                '@export var score_multiplier: float = 1.0\n',
                encoding="utf-8"
            )

        # 3. Fichier de ressource .tres
        cfg_tres = resources_dir / "default_config.tres"
        if not cfg_tres.exists():
            cfg_tres.write_text(
                '[gd_resource type="Resource" script_class="GameConfig" load_steps=2 format=3]\n\n'
                '[ext_resource type="Script" path="res://scripts/game_config.gd" id="1_cfg"]\n\n'
                '[resource]\n'
                'script = ExtResource("1_cfg")\n'
                'move_speed = 350.0\n'
                'max_health = 100\n'
                'score_multiplier = 1.5\n',
                encoding="utf-8"
            )

        # 4. Script Player avec signaux et typage strict (Player.gd)
        player_script = scripts_dir / "player.gd"
        if not player_script.exists():
            player_script.write_text(
                'class_name Player\n'
                'extends CharacterBody2D\n\n'
                'signal health_changed(new_health: int)\n'
                'signal player_died\n\n'
                '@export var config: GameConfig\n'
                'var current_health: int = 100\n\n'
                'func _ready() -> void:\n'
                '    if config:\n'
                '        current_health = config.max_health\n\n'
                'func take_damage(amount: int) -> void:\n'
                '    current_health = max(0, current_health - amount)\n'
                '    health_changed.emit(current_health)\n'
                '    if current_health == 0:\n'
                '        player_died.emit()\n',
                encoding="utf-8"
            )

        # 5. Script Main Scene avec écoute de signaux découplés (Main.gd)
        main_script = scripts_dir / "main.gd"
        if not main_script.exists():
            main_script.write_text(
                'extends Node2D\n\n'
                '@onready var player: Player = $Player\n\n'
                'func _ready() -> void:\n'
                '    if player:\n'
                '        player.health_changed.connect(_on_player_health_changed)\n'
                '        player.player_died.connect(_on_player_died)\n'
                '    print("Jeu Godot initialisé avec architecture découplée.")\n\n'
                'func _on_player_health_changed(new_health: int) -> void:\n'
                '    print("Santé du joueur : ", new_health)\n\n'
                'func _on_player_died() -> void:\n'
                '    print("Partie terminée.")\n',
                encoding="utf-8"
            )

        # 6. Scène principale Godot (main.tscn)
        main_scene = scenes_dir / "main.tscn"
        if not main_scene.exists():
            main_scene.write_text(
                '[gd_scene load_steps=3 format=3]\n\n'
                '[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]\n'
                '[ext_resource type="Script" path="res://scripts/player.gd" id="2_player"]\n\n'
                '[node name="Main" type="Node2D"]\n'
                'script = ExtResource("1_main")\n\n'
                '[node name="Player" type="CharacterBody2D" parent="."]\n'
                'script = ExtResource("2_player")\n',
                encoding="utf-8"
            )

        readme = path / "README.md"
        if not readme.exists():
            readme.write_text(f"# {name} (Jeu Godot 4 Idiomatique)\n\n{desc}\n\n## Lancer\n`godot project.godot`\n", encoding="utf-8")

        return {
            "project_name": name,
            "project_type": "godot",
            "path": str(path),
            "entrypoint": "project.godot",
            "launch_command": "godot project.godot",
            "test_command": "godot --headless --quit"
        }

    def _scaffold_web_light(self, path: Path, name: str, desc: str) -> dict[str, Any]:
        html_file = path / "index.html"
        if not html_file.exists():
            html_file.write_text(
                '<!DOCTYPE html>\n'
                '<html lang="fr">\n'
                '<head>\n'
                '    <meta charset="UTF-8">\n'
                f'    <title>{name}</title>\n'
                '    <link rel="stylesheet" href="style.css">\n'
                '</head>\n'
                '<body>\n'
                f'    <main><h1>{name}</h1><p>{desc}</p></main>\n'
                '    <script src="app.js"></script>\n'
                '</body>\n'
                '</html>\n',
                encoding="utf-8"
            )

        css_file = path / "style.css"
        if not css_file.exists():
            css_file.write_text(
                'body { font-family: sans-serif; background: #0f172a; color: #f8fafc; display: grid; place-content: center; min-height: 100vh; margin: 0; }\n',
                encoding="utf-8"
            )

        js_file = path / "app.js"
        if not js_file.exists():
            js_file.write_text(
                f'console.log("{name} initialisé avec succès.");\n',
                encoding="utf-8"
            )

        return {
            "project_name": name,
            "project_type": "web_light",
            "path": str(path),
            "entrypoint": "index.html",
            "launch_command": "python -m http.server 8080",
            "test_command": "python -c 'import pathlib; assert (pathlib.Path(\"index.html\")).exists()'"
        }
