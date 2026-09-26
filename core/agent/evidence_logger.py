"""E-ZZIO Coding Agent — Structured Evidence & Trajectory Logger.

Enregistre de manière inviolable et auditable les preuves d'exécution de chaque tâche :
- TASK_ID, PLAN, FILES_CHANGED, COMMANDS, TESTS, RESULT, ROLLBACK_STATE, FINAL_DIFF
- Modèle utilisé, Fournisseur, Cost Class, Timestamps
- Persistance JSON et rapport Markdown synthétique dans state/evidence/
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from core.agent.command_executor import redact_secrets


@dataclass
class CodingTaskEvidence:
    task_id: str
    plan: str = ""
    files_changed: list[str] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    tests: list[dict[str, Any]] = field(default_factory=list)
    result: str = "PENDING"  # SUCCESS, FAILED, ROLLBACK, ABORTED
    rollback_state: bool = False
    final_diff: str = ""
    model_used: str = "unknown"
    provider: str = "unknown"
    cost_class: str = "FREE_ONLY"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_sec: float = 0.0
    human_approved: bool | None = None
    notes: str = ""

    def add_command_result(self, command: str, exit_code: int = 0, duration_ms: int = 0) -> None:
        """Ajoute le résultat d'une commande gouvernée dans les preuves."""
        self.commands.append({
            "command": redact_secrets(command),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        })

    def add_test_result(self, name: str, passed: bool, summary: str = "") -> None:
        """Ajoute le résultat d'un test dans les preuves."""
        self.tests.append({
            "name": name,
            "passed": passed,
            "summary": summary,
        })

    def add_file_changed(self, file_path: str) -> None:
        """Ajoute un fichier modifié sans doublon en préservant l'ordre."""
        if file_path not in self.files_changed:
            self.files_changed.append(file_path)

    def complete(self, result: str, final_diff: str = "", rollback_applied: bool = False) -> None:
        self.end_time = time.time()
        self.duration_sec = round(self.end_time - self.start_time, 3)
        self.result = result
        self.final_diff = redact_secrets(final_diff)
        self.rollback_state = rollback_applied
        deduped: list[str] = []
        for f in self.files_changed:
            if f not in deduped:
                deduped.append(f)
        self.files_changed = deduped


class EvidenceLogger:
    """Gestionnaire de persistance des preuves pour l'Agent de Code Souverain."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.evidence_dir = os.path.join(self.workspace_root, "state", "evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

    def get_evidence(self, task_id: str) -> dict[str, Any] | None:
        """Lit et désérialise une preuve d'exécution JSON sauvegardée."""
        json_filename = f"{task_id}_evidence.json"
        json_path = os.path.join(self.evidence_dir, json_filename)
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_evidences(self, limit: int = 10) -> list[dict[str, Any]]:
        """Scanne le répertoire d'evidence et retourne un index synthétique des preuves récentes."""
        summaries: list[dict[str, Any]] = []
        if not os.path.exists(self.evidence_dir):
            return summaries
        for filename in os.listdir(self.evidence_dir):
            if filename.endswith("_evidence.json"):
                path = os.path.join(self.evidence_dir, filename)
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    summaries.append({
                        "task_id": data.get("task_id"),
                        "result": data.get("result", "UNKNOWN"),
                        "duration_sec": data.get("duration_sec", 0.0),
                        "files_changed_count": len(data.get("files_changed", [])),
                        "commands_count": len(data.get("commands", [])),
                        "tests_count": len(data.get("tests", [])),
                        "provider": data.get("provider", "unknown"),
                        "model_used": data.get("model_used", "unknown"),
                        "cost_class": data.get("cost_class", "FREE_ONLY"),
                        "start_time": data.get("start_time", 0.0),
                    })
                except Exception:
                    continue
        summaries.sort(key=lambda x: x.get("start_time", 0.0), reverse=True)
        return summaries[:limit]

    def record_evidence(self, evidence: CodingTaskEvidence) -> dict[str, str]:
        """Persiste la preuve en JSON et en Markdown structuré.

        Returns:
            Dict avec chemins des fichiers générés {"json": path, "markdown": path}
        """
        # 1. Sauvegarde JSON
        json_filename = f"{evidence.task_id}_evidence.json"
        json_path = os.path.join(self.evidence_dir, json_filename)
        data = asdict(evidence)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 2. Génération Markdown
        md_filename = f"{evidence.task_id}_evidence.md"
        md_path = os.path.join(self.evidence_dir, md_filename)
        md_content = self._render_markdown(evidence)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {"json": json_path, "markdown": md_path}

    def _render_markdown(self, ev: CodingTaskEvidence) -> str:
        status_badge = "🟢 SUCCESS" if ev.result == "SUCCESS" else ("🔴 FAILED" if ev.result == "FAILED" else "🟡 " + ev.result)
        lines = [
            f"# E-ZZIO Task Execution Evidence — `{ev.task_id}`",
            "",
            f"**Status**: {status_badge} | **Duration**: `{ev.duration_sec}s` | **Rollback**: `{ev.rollback_state}`",
            f"**Provider**: `{ev.provider}` | **Model**: `{ev.model_used}` | **Cost Class**: `{ev.cost_class}`",
            "",
            "## 1. Plan & Objective",
            f"```text\n{ev.plan}\n```",
            "",
            "## 2. Modified Files",
        ]
        if ev.files_changed:
            for f in ev.files_changed:
                lines.append(f"- `{f}`")
        else:
            lines.append("_No files modified._")

        lines.extend([
            "",
            "## 3. Governed Commands",
        ])
        if ev.commands:
            for cmd in ev.commands:
                status = "✅" if cmd.get("exit_code") == 0 else "❌"
                lines.append(f"- {status} `{cmd.get('command')}` (exit {cmd.get('exit_code')}, {cmd.get('duration_ms', 0)}ms)")
        else:
            lines.append("_No commands executed._")

        lines.extend([
            "",
            "## 4. Tests & Verification",
        ])
        if ev.tests:
            for t in ev.tests:
                st = "✅ PASS" if t.get("passed") else "❌ FAIL"
                lines.append(f"- {st} `{t.get('name')}`: {t.get('summary', '')}")
        else:
            lines.append("_No tests registered._")

        if ev.final_diff:
            lines.extend([
                "",
                "## 5. Final Diff Review",
                "```diff",
                ev.final_diff[:4000],
                "```"
            ])

        lines.append("")
        return "\n".join(lines)
