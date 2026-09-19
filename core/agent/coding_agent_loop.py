"""E-ZZIO Coding Agent — Optimized Autonomous Loop with Context Truncation for Local Models."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Generator
from typing import Any

from core.agent.agent_guard import CodingAgentBudget
from core.agent.agent_provider import AgentProviderAdapter
from core.agent.complex_task_orchestrator import ComplexTaskEngine
from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger
from core.agent.tools_registry import ToolRegistry

from typing import List


class CodingAgentHarness:
    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio", backend: str = "cloud_gemini", local_model: str = "ornith-1.5:9b"):
        self.workspace = workspace_root
        self.registry = ToolRegistry(workspace_root)
        self.provider = AgentProviderAdapter(backend=backend, local_model=local_model)
        self.evidence_logger = EvidenceLogger(workspace_root)
        self.complex_engine = ComplexTaskEngine(workspace_root)

    def evaluate_task_complexity(self, task_description: str) -> str:
        """Évalue la complexité d'une tâche et route vers le modèle adapté."""
        desc = task_description.lower()
        if any(kw in desc for kw in ["refactor", "ast", "architecture", "restructure", "deadlock"]):
            return "gemini-3.1-pro"
        elif any(kw in desc for kw in ["cherche", "où est", "trouve", "recherche", "explore", "liste"]):
            return "gemini-3.5-flash-lite"
        return "gemini-3.7-flash"

    def _optimize_observation(self, observation: str) -> str:
        """Tronque intelligemment l'observation si elle est trop lourde pour un modèle local."""
        max_chars = 2000 if self.provider.backend == "local_ollama" else 10000
        if len(observation) > max_chars:
            return observation[:max_chars] + f"\n\n[... TRUNCATED {len(observation) - max_chars} CHARS FOR LOCAL EFFICIENCY ...]"
        return observation

    def run_trajectory(
        self,
        objective: str,
        max_steps: int = 5,
        task_id: str | None = None,
        budget: CodingAgentBudget | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        t_id = task_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        active_budget = budget or CodingAgentBudget(max_iterations=max_steps)
        evidence = CodingTaskEvidence(
            task_id=t_id,
            plan=objective,
            model_used=getattr(self.provider, "local_model", "cloud_gemini"),
            provider=self.provider.backend,
        )

        codebase_map = self.registry.execute("get_codebase_map", {})

        system_context = (
            "Tu es l'agent de code souverain d'E-ZZIO.\n"
            f"Cartographie du dépôt :\n{codebase_map}\n\n"
            "RÈGLE D'OR POUR LES OUTILS :\n"
            "Si tu as besoin d'utiliser un outil, réponds UNIQUEMENT au format JSON strict, sans texte autour :\n"
            '{"tool": "nom_de_l_outil", "args": {...}}\n\n'
            "Outils disponibles :\n"
            "- get_codebase_map: {}\n"
            "- read_file: {\"path\": \"chemin\"}\n"
            "- apply_patch: {\"path\": \"chemin\", \"search\": \"texte\", \"replace\": \"texte\"}\n"
            "- run_powershell: {\"command\": \"commande\"}\n\n"
            "Si l'objectif est atteint, réponds simplement en texte naturel."
        )

        history = [
            {"role": "user", "parts": [{"text": f"Objectif : {objective}"}]}
        ]

        task_success = False
        for step in range(1, max_steps + 1):
            ok_iter, b_msg = active_budget.record_iteration()
            if not ok_iter:
                yield {"step": step, "thought": b_msg, "action": None, "observation": b_msg}
                break

            prompt_text = history[-1]["parts"][0]["text"]

            res = self.provider.chat(text=prompt_text, system_prompt=system_context)
            answer = res.get("response", "").strip()

            yield {
                "step": step,
                "thought": answer,
                "action": None,
                "observation": None
            }

            tool_call = None
            try:
                clean_json = answer
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                elif "{" in clean_json and "}" in clean_json:
                    start = clean_json.find("{")
                    end = clean_json.rfind("}") + 1
                    clean_json = clean_json[start:end]

                parsed = json.loads(clean_json)
                if isinstance(parsed, dict) and "tool" in parsed:
                    tool_call = parsed
            except Exception:
                pass

            if not tool_call:
                task_success = True
                break

            t_name = tool_call.get("tool")
            t_args = tool_call.get("args", {})

            # Traçabilité budget
            if t_name in ["apply_patch", "write_file"] and "path" in t_args:
                evidence.files_changed.append(t_args["path"])
                active_budget.record_file(t_args["path"])
            elif t_name == "run_powershell":
                active_budget.record_command()
                evidence.commands.append({"command": t_args.get("command", ""), "exit_code": 0})

            raw_observation = self.registry.execute(t_name, t_args)

            # Application de l'optimisation de contexte
            observation = self._optimize_observation(raw_observation)

            yield {
                "step": step,
                "thought": answer,
                "action": tool_call,
                "observation": observation
            }

            history.append({"role": "model", "parts": [{"text": answer}]})
            history.append({"role": "user", "parts": [{"text": f"Résultat de {t_name} :\n{observation}\nPoursuis l'objectif."}]})

        # Finalisation et persistance des preuves
        evidence.complete("SUCCESS" if task_success else "PARTIAL")
        self.evidence_logger.record_evidence(evidence)

    def run_complex_mission(
        self,
        objective: str,
        target_files: List[str] | None = None,
        patch_actions: List[dict[str, str]] | None = None,
        auto_repair: bool = True,
    ) -> dict[str, Any]:
        """Exécute une mission complexe de bout en bout avec orchestration complète."""
        return self.complex_engine.execute_complex_task(
            objective=objective,
            target_files=target_files,
            patch_actions=patch_actions,
            auto_repair=auto_repair,
        )
