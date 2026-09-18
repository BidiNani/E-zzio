"""E-ZZIO Coding Agent — Modular Skill Loader & Registry."""
from __future__ import annotations

import importlib.util
import json
import os
from typing import Any


class SkillManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.skills_dir = os.path.join(workspace_root, "core", "agent", "skills")
        self.loaded_skills: dict[str, Any] = {}

    def discover_skills(self) -> list[dict[str, Any]]:
        """Découvre toutes les skills ayant un manifeste valide."""
        skills_meta = []
        if not os.path.exists(self.skills_dir):
            return skills_meta

        for entry in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, entry)
            if os.path.isdir(skill_path):
                manifest_path = os.path.join(skill_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, encoding="utf-8") as f:
                            manifest = json.load(f)
                            manifest["_dir"] = skill_path
                            skills_meta.append(manifest)
                    except Exception as exc:
                        print(f"[SKILL ERROR] Impossible de lire le manifeste de {entry}: {exc}")
        return skills_meta

    def execute_skill(self, skill_name: str, args: dict[str, Any]) -> str:
        """Exécute une skill dynamique par son nom."""
        skills = self.discover_skills()
        target = next((s for s in skills if s.get("name") == skill_name), None)
        if not target:
            return f"[ERROR] Skill introuvable : {skill_name}"

        impl_file = target.get("implementation", "skill.py")
        # Confinement : l'implémentation doit rester un .py à l'intérieur du
        # répertoire de la skill (aucune traversée vers le workspace).
        if not isinstance(impl_file, str) or not impl_file.endswith(".py"):
            return f"[ERROR] Implémentation invalide pour la skill {skill_name}."
        impl_path = os.path.realpath(os.path.join(target["_dir"], impl_file))
        if os.path.commonpath([impl_path, os.path.realpath(target["_dir"])]) != os.path.realpath(target["_dir"]):
            return f"[ERROR] Traversée de répertoire refusée pour la skill {skill_name}."
        if not os.path.exists(impl_path):
            return f"[ERROR] Fichier d'implémentation manquant pour la skill {skill_name}."

        try:
            spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", impl_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "run"):
                    return str(mod.run(args, self.workspace_root))
                return "[ERROR] La skill ne possède pas de fonction 'run(args, workspace_root)'."
        except Exception as exc:
            return f"[SKILL EXCEPTION] {exc}"

        return "[ERROR] Échec du chargement de la skill."
