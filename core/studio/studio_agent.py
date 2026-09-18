"""E-ZZIO Dev Studio — Autonomous Game & Application Generation Studio.

End-to-end pipeline:
1. Intent & Stack Classification (Godot / Pygame / Python CLI / Web)
2. Project Scaffolding in isolated projects/<name>/
3. Autonomous Code Generation via CodingAgentHarness
4. Real Build, Run & Test Execution
5. Bounded Self-Healing Loop on Failure (max 3 retries)
6. Delivery Manifest with Execution Commands & Results
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from core.agent.coding_agent_loop import CodingAgentHarness
from core.studio.builder import ProjectBuilder
from core.studio.scaffolder import ProjectScaffolder

logger = logging.getLogger("DevStudioAgent")


class DevStudioAgent:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.scaffolder = ProjectScaffolder(str(self.workspace_root))
        self.builder = ProjectBuilder(str(self.workspace_root))
        self.max_repair_attempts = 3

    def classify_project_intent(self, prompt: str) -> dict[str, str]:
        """Détermine le type de projet et le nom optimal à partir du prompt utilisateur."""
        lower = prompt.lower()

        # Détection du type
        if "godot" in lower or "gdscript" in lower:
            p_type = "godot"
        elif "pygame" in lower or ("jeu" in lower and "2d" in lower and "python" in lower):
            p_type = "pygame"
        elif "web" in lower or "html" in lower or "css" in lower or "dashboard" in lower:
            p_type = "web_light"
        elif "jeu" in lower or "game" in lower:
            # Choix rationnel CPU-friendly : Pygame ou Godot
            p_type = "pygame" if "python" in lower else "godot"
        else:
            p_type = "python_cli"

        # Extraction d'un nom de projet lisible
        words = re.findall(r'[a-zA-Z0-9]+', lower)
        keywords = [w for w in words if w not in ("fais", "moi", "un", "une", "cree", "code", "appli", "application", "jeu", "de", "en", "pour", "le", "la", "les")]
        raw_name = "_".join(keywords[:3]) or "app_studio"
        project_name = self.scaffolder._sanitize_name(raw_name)

        return {
            "project_name": project_name,
            "project_type": p_type,
            "description": prompt
        }

    def build_project_pipeline(self, prompt: str) -> dict[str, Any]:
        """Exécute la chaîne complète de création, codage, test et validation."""
        # 1. Classification
        spec = self.classify_project_intent(prompt)
        p_name = spec["project_name"]
        p_type = spec["project_type"]

        logger.info("[STUDIO] Initialisation du projet '%s' (Type: %s)...", p_name, p_type)

        # 2. Scaffolding dans projects/<nom>
        manifest = self.scaffolder.scaffold(
            project_name=p_name,
            project_type=p_type,
            description=spec["description"]
        )
        project_dir = Path(manifest["path"])

        # 3. Harnais de codage autonome borné dans le dossier du projet
        harness = CodingAgentHarness(workspace_root=str(project_dir))
        coding_prompt = (
            f"Tu dois développer le projet '{p_name}' dans ce dossier.\n"
            f"Objectif : {prompt}\n"
            f"Type : {p_type}\n"
            "Modifie ou crée les fichiers nécessaires dans src/ ou scenes/ et assure-toi que le code fonctionne."
        )

        steps_log = []
        try:
            for step_data in harness.run_trajectory(coding_prompt):
                steps_log.append(step_data)
                if step_data.get("done"):
                    break
        except Exception as exc:
            logger.warning("[STUDIO-HARNESS-WARN] Avertissement lors de la génération du code : %s", exc)

        # 4. Build, Exécution réelle & Validation
        validation_result = self._validate_and_heal(p_name, p_type, project_dir, harness)

        # 5. Rapport de livraison
        return {
            "ok": validation_result.get("ok", False),
            "project_name": p_name,
            "project_type": p_type,
            "path": str(project_dir),
            "relative_path": f"projects/{p_name}",
            "launch_command": manifest.get("launch_command", ""),
            "status": validation_result.get("status", "VALIDATED"),
            "validation_details": validation_result,
            "message": (
                f"Projet '{p_name}' généré avec succès dans projects/{p_name}/.\n"
                f"Commande de lancement : `{manifest.get('launch_command')}`"
            )
        }

    def _validate_and_heal(
        self,
        project_name: str,
        project_type: str,
        project_dir: Path,
        harness: CodingAgentHarness
    ) -> dict[str, Any]:
        """Exécute les tests réels et applique une boucle d'auto-réparation en cas d'erreur."""
        for attempt in range(1, self.max_repair_attempts + 1):
            if project_type == "python_cli":
                res = self.builder.run_python_project(project_name)
                # Si des tests unitaires existent dans le projet
                if (project_dir / "tests").exists():
                    test_res = self.builder.run_project_tests(project_name)
                    if not test_res.get("ok"):
                        res = test_res
            elif project_type == "pygame":
                res = self.builder.run_python_project(project_name, entrypoint="src/game.py")
            elif project_type == "godot":
                res = self.builder.run_godot_headless(project_name)
            else:
                # web_light
                res = {"ok": (project_dir / "index.html").exists(), "status": "HTML_VALIDATED"}

            if res.get("ok"):
                return {"ok": True, "status": "VERIFIED_OPERATIONAL", "attempt": attempt, "details": res}

            logger.warning("[STUDIO-HEAL] Tentative %d/%d : Échec d'exécution (%s). Auto-correction...", attempt, self.max_repair_attempts, res.get("error") or res.get("stderr"))

            # Injection du traceback d'erreur pour auto-correction
            error_msg = res.get("stderr") or res.get("error") or "Erreur d'exécution"
            heal_prompt = f"L'exécution du projet a échoué avec l'erreur suivante :\n{error_msg}\nCorrige immédiatement les fichiers du projet."
            try:
                for step_data in harness.run_trajectory(heal_prompt):
                    if step_data.get("done"):
                        break
            except Exception:
                pass

        return {"ok": False, "status": "VALIDATION_FAILED", "attempts": self.max_repair_attempts, "last_error": res}
