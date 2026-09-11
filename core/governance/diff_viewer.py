"""
E-ZZIO Core V9.2 — HITL V2 Differential Inspection Engine.
Génère des vues différentielles unifiées (Unified Diff) et syntaxiquement formatées
pour permettre une inspection humaine sans ambiguïté avant décision (APPROVE / REJECT).
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DiffInspectionResult:
    target_path: Optional[str]
    diff_unified: str
    lines_added: int
    lines_removed: int
    is_identical: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_path": self.target_path,
            "diff_unified": self.diff_unified,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "is_identical": self.is_identical,
            "summary": self.summary,
        }


class HITLDiffViewer:
    """Moteur de calcul de diff pour l'arbitrage HITL souverain."""

    @staticmethod
    def generate_text_diff(
        original_text: str,
        new_text: str,
        from_file: str = "original",
        to_file: str = "proposed",
    ) -> DiffInspectionResult:
        from_lines = original_text.splitlines(keepends=True)
        to_lines = new_text.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                from_lines,
                to_lines,
                fromfile=from_file,
                tofile=to_file,
                lineterm="",
            )
        )

        lines_added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        lines_removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        diff_str = "\n".join(diff)

        is_identical = len(diff) == 0
        summary = f"+{lines_added} / -{lines_removed} lines" if not is_identical else "Identical (no change)"

        return DiffInspectionResult(
            target_path=to_file,
            diff_unified=diff_str,
            lines_added=lines_added,
            lines_removed=lines_removed,
            is_identical=is_identical,
            summary=summary,
        )

    @classmethod
    def generate_file_diff(cls, file_path: Path | str, proposed_content: str | bytes) -> DiffInspectionResult:
        p = Path(file_path)
        is_binary = isinstance(proposed_content, bytes) or (p.exists() and cls._is_binary_file(p))

        if is_binary:
            import hashlib
            orig_hash = hashlib.sha256(p.read_bytes()).hexdigest().upper() if p.exists() else "NONE (NEW FILE)"
            prop_bytes = proposed_content if isinstance(proposed_content, bytes) else proposed_content.encode("utf-8")
            prop_hash = hashlib.sha256(prop_bytes).hexdigest().upper()
            summary = f"Binary mutation: {len(prop_bytes)} bytes (SHA256: {prop_hash[:12]}...)"
            diff_text = f"Binary files {p.name} differ:\n  Original SHA-256: {orig_hash}\n  Proposed SHA-256: {prop_hash}\n  Proposed size: {len(prop_bytes)} bytes"
            return DiffInspectionResult(
                target_path=str(p),
                diff_unified=diff_text,
                lines_added=0,
                lines_removed=0,
                is_identical=(orig_hash == prop_hash),
                summary=summary,
            )

        original_text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        from_file = f"a/{p.name}" if p.exists() else "/dev/null (NEW FILE)"
        to_file = f"b/{p.name}" if proposed_content else "/dev/null (DELETED)"
        return cls.generate_text_diff(
            original_text=original_text,
            new_text=str(proposed_content),
            from_file=from_file,
            to_file=to_file,
        )

    @staticmethod
    def _is_binary_file(path: Path) -> bool:
        try:
            with open(path, "tr", encoding="utf-8") as f:
                f.read(1024)
                return False
        except (UnicodeDecodeError, Exception):
            return True

    @classmethod
    def generate_payload_diff(cls, params_payload: str | Dict[str, Any]) -> str:
        """Génère un affichage lisible et inspectable du payload de la demande d'approbation."""
        if isinstance(params_payload, str):
            try:
                data = json.loads(params_payload)
            except Exception:
                return params_payload
        else:
            data = params_payload

        # Si le payload contient du code ou un patch
        if "patch" in data and "target" in data:
            return cls.generate_file_diff(data["target"], data["patch"]).diff_unified
        if "content" in data and "target_path" in data:
            return cls.generate_file_diff(data["target_path"], data["content"]).diff_unified

        return json.dumps(data, indent=2, ensure_ascii=False)


diff_viewer = HITLDiffViewer()