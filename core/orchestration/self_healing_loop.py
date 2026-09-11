"""E-ZZIO — boucle d'auto-correction bornée (max 3 tentatives, sans auto-commit)."""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ezzio.self_healing")

MAX_RETRIES = 3
FAIL_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.MULTILINE)


@dataclass
class HealingReport:
    target: str
    attempts: int = 0
    fixed: bool = False
    applied_diff: Optional[str] = None
    last_error: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)


def run_pytest_capture(*targets: str, timeout: int = 300) -> Dict[str, Any]:
    """Exécute pytest, capture stdout/stderr/retours (jamais levant)."""
    cmd = [sys.executable, "-m", "pytest", *targets, "-q", "-p", "no:randomly",
           "--tb=short"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              cwd="G:/AI/E-zzio", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "failures": [],
                "error": f"timeout pytest >{timeout}s: {str(exc)[:200]}"}
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    failures = sorted(set(FAIL_RE.findall(out)))
    return {"ok": proc.returncode == 0,
            "failures": [f"{k} {t}" for k, t in failures],
            "output_tail": out[-3000:], "returncode": proc.returncode}


def build_healing_prompt(test_id: str, failure_excerpt: str,
                         file_hint: str = "") -> str:
    return (
        "Tu es le sous-agent de code E-ZZIO. Corrige UNIQUEMENT le défaut "
        "ci-dessous par un patch unifié minimal (format @@ -x,y +x,y @@). "
        "Aucun refactoring, aucun fichier entier réémis.\n\n"
        f"TEST : {test_id}\nFICHIER : {file_hint}\n"
        f"ÉCHEC :\n{failure_excerpt[:2000]}"
    )


class SelfHealingLoop:
    """CAP 3 tentatives. Propose le diff, ne committe jamais seul."""

    def __init__(self, max_retries: int = MAX_RETRIES):
        self.max_retries = max(1, min(max_retries, MAX_RETRIES))

    def heal(self, *targets: str, apply: bool = False,
             file_hint: str = "") -> HealingReport:
        report = HealingReport(target=" ".join(targets) or "tests/")
        for attempt in range(1, self.max_retries + 1):
            report.attempts = attempt
            res = run_pytest_capture(*targets)
            if res["ok"]:
                report.fixed = True
                return report
            first = res["failures"][0] if res["failures"] else "échec inconnu"
            report.last_error = first
            prompt = build_healing_prompt(first, res["output_tail"], file_hint)
            report.history.append({"attempt": attempt, "failure": first,
                                   "prompt_chars": len(prompt)})
            logger.warning("[SELF-HEAL] tentative %d/%d : %s",
                           attempt, self.max_retries, first)
            if not apply:
                break  # dry-run : diagnostic seul, aucune écriture
        return report
