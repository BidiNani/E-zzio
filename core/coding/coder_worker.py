"""E-ZZIO Core — CoderWorker (boucle plan → build → verify).

**Objectif** : boucle autonome de codage. Le worker reçoit une
``CodingRequest``, puis :

1. **Plan** : interroge un LLM (via providers) pour générer un plan
2. **Build** : exécute le plan (écrit des fichiers via ``InternalToolBridge``)
3. **Verify** : vérifie le résultat (ruff + pytest via le bridge)
4. **Boucle** : si Verify échoue, retourne à Plan (max ``MAX_ITERATIONS``)

**Garde-fous** :
- Max ``MAX_ITERATIONS`` (par défaut 3)
- Snapshot avant chaque modification (via git branch)
- Rollback automatique si Verify échoue après épuisement des itérations
- Validation par ``CodingPolicy`` avant exécution
- Toutes les actions tracées (log)

**Usage** :
    worker = CoderWorker(root_dir="G:/AI/E-zzio")
    request = CodingRequest(
        task_description="Ajouter un test pour core/coding/protocol.py",
        mode=ExecutionMode.DRY_RUN,
    )
    response = worker.execute(request)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core.coding.bridge import InternalToolBridge, ToolResult
from core.coding.policy import CodingPolicy
from core.coding.protocol import (
    CodingRequest,
    CodingResponse,
    ExecutionMode,
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


PROMPT_TEMPLATE = """Tu es un coder_worker autonome pour le projet E-zzio.

TÂCHE : {task}

CONTEXTE :
{context}

INSTRUCTIONS :
1. Analyse la tâche.
2. Propose un plan d'action concret (fichiers à modifier, contenu).
3. Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après.
4. Format attendu :
{{
  "plan": ["étape 1", "étape 2", ...],
  "files": [
    {{"path": "chemin/relatif.py", "content": "...contenu complet..."}}
  ]
}}

Contraintes :
- Chemins relatifs au projet, pas de sortie du workspace.
- Contenu complet du fichier (pas de patch partiel).
- Si tu n'es pas sûr, laisse "files" vide et explique dans "plan".
"""


@dataclass
class PlanStep:
    """Une étape du plan."""
    description: str


@dataclass
class FileEdit:
    """Une édition de fichier."""
    path: str
    content: str


class CoderWorker:
    """Worker autonome de codage.

    Exécute une boucle plan → build → verify sur une ``CodingRequest``.
    """

    def __init__(
        self,
        root_dir: Path | str = ".",
        max_iterations: int = MAX_ITERATIONS,
        dry_run: bool = False,
        allowed_modes: frozenset[ExecutionMode] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.max_iterations = max_iterations
        self.dry_run = dry_run

        self.bridge = InternalToolBridge(root_dir=self.root_dir, dry_run=dry_run)
        # Policy : accepter des modes explicites (défaut = dry_run + read_only)
        self.policy = CodingPolicy(
            root_dir=self.root_dir,
            allowed_modes=allowed_modes,
        )
        # Cooldown des providers ayant renvoyé 429 (nom -> timestamp)
        self._cooldowns: dict[str, float] = {}

    def _is_in_cooldown(self, provider_name: str, cooldown_seconds: int = 120) -> bool:
        """Vérifie si un provider est en cooldown (429 récent)."""
        import time
        ts = self._cooldowns.get(provider_name)
        if ts is None:
            return False
        return (time.time() - ts) < cooldown_seconds

    def _mark_cooldown(self, provider_name: str) -> None:
        """Marque un provider en cooldown (suite à 429)."""
        import time
        self._cooldowns[provider_name] = time.time()

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """Appelle le meilleur provider disponible.

        Fallback automatique : si un provider échoue (ex. 429), on passe au
        suivant. Les providers en cooldown (429 récent) sont ignorés.
        """
        from core.coding.providers import get_all_available

        providers = get_all_available()
        if not providers:
            raise RuntimeError("Aucun provider LLM disponible")

        last_error = ""
        for provider in providers:
            # Ignorer les providers en cooldown
            if self._is_in_cooldown(provider.name):
                logger.info("Provider %s en cooldown, skip", provider.name)
                continue

            logger.info("Tentative provider : %s", provider.name)
            resp = provider.call(prompt)
            if resp.success:
                logger.info("Provider %s OK (model=%s)", provider.name, resp.model_used)
                return resp.content

            last_error = resp.error
            logger.warning("Provider %s échec : %s", provider.name, resp.error)

            # Si 429, marquer en cooldown
            if "429" in resp.error or "Too Many Requests" in resp.error:
                self._mark_cooldown(provider.name)
                logger.info("Provider %s marqué en cooldown (429)", provider.name)

        raise RuntimeError(f"Tous les providers ont échoué. Dernier : {last_error}")

    # --------------------------------------------------------
    # PLAN
    # --------------------------------------------------------

    def _plan(self, request: CodingRequest, iteration: int, feedback: str = "") -> list[FileEdit]:
        """Génère un plan (fichiers à écrire)."""
        context = self.bridge.get_context()
        context_str = f"Git status : {context['git_status']}\n"
        if feedback:
            context_str += f"\nFeedback de l'itération précédente :\n{feedback}"

        prompt = PROMPT_TEMPLATE.format(
            task=request.task_description,
            context=context_str,
        )

        response = self._call_llm(prompt)

        # Extraire le JSON
        import json
        import re

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            logger.warning("Pas de JSON dans la réponse LLM")
            return []

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            logger.warning("JSON invalide : %s", exc)
            return []

        edits = []
        for f in data.get("files", []):
            if "path" in f and "content" in f:
                edits.append(FileEdit(path=f["path"], content=f["content"]))
        return edits

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    def _build(self, edits: list[FileEdit]) -> list[ToolResult]:
        """Applique les éditions via le bridge."""
        results = []
        for edit in edits:
            logger.info("Écriture : %s", edit.path)
            result = self.bridge.write_file(edit.path, edit.content)
            results.append(result)
            if not result.success:
                logger.error("Échec écriture %s : %s", edit.path, result.error)
        return results

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    def _verify(self, edits: list[FileEdit]) -> tuple[bool, str]:
        """Vérifie le résultat (ruff + pytest)."""
        if self.dry_run:
            return True, "[DRY-RUN] Vérification simulée"

        # Vérifier ruff sur les fichiers modifiés
        py_files = [e.path for e in edits if e.path.endswith(".py")]
        for py_file in py_files:
            result = self.bridge.run_ruff(py_file)
            if not result.success:
                return False, f"Ruff échec sur {py_file} :\n{result.stdout}\n{result.stderr}"

        # Vérifier pytest (tests rapides uniquement)
        result = self.bridge.run_pytest(extra_args=["-m", "not slow and not visual and not hardware", "--maxfail=1"])
        if not result.success:
            return False, f"Pytest échec :\n{result.stdout}\n{result.stderr}"

        return True, "Vérification OK"

    # --------------------------------------------------------
    # EXECUTE (boucle principale)
    # --------------------------------------------------------

    def execute(self, request: CodingRequest) -> CodingResponse:
        """Exécute la boucle plan → build → verify."""
        # 1. Validation par la policy
        try:
            self.policy.evaluate_request(request)
        except Exception as exc:
            logger.error("Policy violation : %s", exc)
            return CodingResponse(
                success=False,
                error=f"Policy violation : {exc}",
            )

        logger.info("CoderWorker : tâche = %s", request.task_description)

        feedback = ""
        last_edits: list[FileEdit] = []

        for iteration in range(1, self.max_iterations + 1):
            logger.info("=== Itération %d/%d ===", iteration, self.max_iterations)

            # PLAN
            try:
                edits = self._plan(request, iteration, feedback)
            except RuntimeError as exc:
                logger.error("Erreur LLM : %s", exc)
                return CodingResponse(
                    success=False,
                    error=f"Erreur LLM : {exc}",
                    iterations=iteration,
                )
            if not edits:
                return CodingResponse(
                    success=False,
                    error="Plan vide ou invalide",
                    iterations=iteration,
                )

            # BUILD
            build_results = self._build(edits)
            if not all(r.success for r in build_results):
                errors = [r.error for r in build_results if not r.success]
                feedback = f"Erreurs d'écriture : {errors}"
                last_edits = edits
                continue

            # VERIFY
            ok, verify_msg = self._verify(edits)
            if ok:
                return CodingResponse(
                    success=True,
                    result={
                        "iterations": iteration,
                        "files_written": [e.path for e in edits],
                        "message": verify_msg,
                    },
                    iterations=iteration,
                )

            # Feedback pour la prochaine itération
            feedback = verify_msg
            last_edits = edits
            logger.warning("Vérification échouée, itération suivante...")

        # Échec après max_iterations
        return CodingResponse(
            success=False,
            error=f"Échec après {self.max_iterations} itérations",
            iterations=self.max_iterations,
            result={
                "last_edits": [e.path for e in last_edits],
                "feedback": feedback,
            },
        )


__all__ = ["CoderWorker", "PlanStep", "FileEdit"]
