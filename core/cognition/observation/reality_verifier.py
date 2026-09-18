"""E-ZZIO Core — Observable Reality Verifier (Phase 7.1).

Performs independent physical filesystem, syntax, and execution verification
before E-ZZIO accepts any action result from an external agent (Antigravity, Gemini, Groq, Ollama).
Guarantees that external agents cannot self-declare success.
"""

from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ObservationRecord:
    target_path: str | None
    observed_action: str  # "FILE_CREATED", "FILE_MODIFIED", "SYNTAX_VERIFIED", "COMMAND_EXECUTED"
    is_verified: bool
    observation_details: str
    pre_sha256: str | None = None
    post_sha256: str | None = None
    file_size_bytes: int = 0


class ObservableRealityVerifier:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir

    def verify_file_creation(self, file_path: Path, expected_non_empty: bool = True) -> ObservationRecord:
        """Asserts that a claimed file was physically created on disk with valid size."""
        resolved = file_path if file_path.is_absolute() else self.root_dir / file_path

        if not resolved.exists():
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="FILE_CREATED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: Claimed file '{resolved}' does not exist on disk (Ghost file).",
            )

        size = resolved.stat().st_size
        if expected_non_empty and size == 0:
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="FILE_CREATED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: Claimed file '{resolved}' exists but is 0 bytes (Empty file).",
                file_size_bytes=size,
            )

        post_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return ObservationRecord(
            target_path=str(resolved),
            observed_action="FILE_CREATED",
            is_verified=True,
            observation_details=f"OBSERVATION VERIFIED: Physical file confirmed on disk ({size} bytes, SHA256: {post_hash[:8]}).",
            post_sha256=post_hash,
            file_size_bytes=size,
        )

    def verify_file_modification(self, file_path: Path, pre_hash: str) -> ObservationRecord:
        """Asserts that a file was genuinely modified by comparing pre and post SHA-256 hashes."""
        resolved = file_path if file_path.is_absolute() else self.root_dir / file_path

        if not resolved.exists():
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="FILE_MODIFIED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: Target file '{resolved}' does not exist.",
            )

        post_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if post_hash == pre_hash:
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="FILE_MODIFIED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: No physical change detected in '{resolved}' (Pre and post hashes are identical: {pre_hash[:8]}).",
                pre_sha256=pre_hash,
                post_sha256=post_hash,
            )

        return ObservationRecord(
            target_path=str(resolved),
            observed_action="FILE_MODIFIED",
            is_verified=True,
            observation_details=f"OBSERVATION VERIFIED: Physical change confirmed on disk ({pre_hash[:8]} -> {post_hash[:8]}).",
            pre_sha256=pre_hash,
            post_sha256=post_hash,
            file_size_bytes=resolved.stat().st_size,
        )

    def verify_python_syntax(self, file_path: Path) -> ObservationRecord:
        """Asserts that a Python file has 100% valid AST syntax without parse errors."""
        resolved = file_path if file_path.is_absolute() else self.root_dir / file_path

        if not resolved.exists():
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="SYNTAX_VERIFIED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: Cannot verify syntax of missing file '{resolved}'.",
            )

        try:
            content = resolved.read_text(encoding="utf-8")
            ast.parse(content)
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="SYNTAX_VERIFIED",
                is_verified=True,
                observation_details=f"OBSERVATION VERIFIED: Python AST syntax parse succeeded for '{resolved}'.",
                file_size_bytes=len(content),
            )
        except SyntaxError as se:
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="SYNTAX_VERIFIED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: SyntaxError on line {se.lineno}: {se.msg}",
            )
        except Exception as e:
            return ObservationRecord(
                target_path=str(resolved),
                observed_action="SYNTAX_VERIFIED",
                is_verified=False,
                observation_details=f"OBSERVATION FAILED: Parse failure: {e}",
            )
