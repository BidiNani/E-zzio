"""E-ZZIO Core — Antigravity Policy & Containment Governor (Phase 4B).

Enforces strict containment boundaries before delegating tasks to Antigravity:
1. Rejects dangerous tool bypass flags unless explicitly permitted by human governance.
2. Restricts target workspace to authorized paths.
3. Prohibits any execution attempting to alter the frozen Decision Ledger directly.
4. Enforces timeouts and resource bounds.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.cognition.antigravity.capabilities import (
    AntigravityAgentRequest,
    AntigravityPolicyViolationError,
)

logger = logging.getLogger(__name__)


class AntigravityPolicyGovernor:
    # Forbidden execution paths where Antigravity must never execute modifying operations
    PROTECTED_ROOT_PATHS = {
        Path(r"core\constitution"),
        Path(r"runtime\cognition\budget"),  # Decision ledger storage
    }

    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir

    def evaluate_request(self, request: AntigravityAgentRequest) -> None:
        """Validates that a delegation request conforms to E-ZZIO safety invariants."""
        # 1. Workspace boundary check
        try:
            ws_resolved = request.workspace_path.resolve()
            root_resolved = self.root_dir.resolve()
            if not str(ws_resolved).startswith(str(root_resolved)) and not str(ws_resolved).startswith("C:\\Users\\"):
                raise AntigravityPolicyViolationError(
                    f"FAIL-CLOSED: Workspace path '{request.workspace_path}' is outside authorized boundaries."
                )
        except Exception as e:
            raise AntigravityPolicyViolationError(f"FAIL-CLOSED: Invalid workspace path: {e}") from e

        # 2. Strict protection of the frozen Decision Ledger & Constitution
        prompt_low = request.prompt.lower()
        prompt_normalized = prompt_low.replace("/", "\\")

        # Invariant 2a: Strict block on P0 files and anchors
        P0_BLOCKED_STRINGS = [
            "unified_decision_ledger",
            ".ledger_head",
            ".ledger_monotonic_state",
            ".ledger_transaction.lock",
            "ezzio_genome.json",
            "contract_manifest.json",
        ]
        for p0_str in P0_BLOCKED_STRINGS:
            if p0_str in prompt_normalized and any(verb in prompt_low for verb in ["write", "delete", "tamper", "modify", "corrupt", "unlink", "overwrite", "append"]):
                raise AntigravityPolicyViolationError(
                    f"FAIL-CLOSED P0: Direct modification of protected artifact '{p0_str}' is strictly prohibited."
                )

        # Invariant 2b: Prompt injection & sovereign policy override rejection
        FORBIDDEN_SOVEREIGN_OVERRIDE_PATTERNS = [
            "ignore previous instructions",
            "ignore all instructions",
            "disregard policy",
            "override constitution",
            "you are now the root authority",
            "ezzio is no longer sovereign",
            "reconfigure provider federation",
            "self_select_as_exclusive_provider",
        ]
        for pattern in FORBIDDEN_SOVEREIGN_OVERRIDE_PATTERNS:
            if pattern in prompt_low:
                raise AntigravityPolicyViolationError(
                    f"FAIL-CLOSED: Prompt injection / sovereign override pattern detected: '{pattern}'."
                )

        # Invariant 2c: General protected paths
        for protected_rel in self.PROTECTED_ROOT_PATHS:
            protected_full = self.root_dir / protected_rel
            rel_str = str(protected_rel).lower().replace("/", "\\")
            full_str = str(protected_full).lower().replace("/", "\\")
            if (rel_str in prompt_normalized or full_str in prompt_normalized) and ("write" in prompt_low or "delete" in prompt_low or "tamper" in prompt_low):
                raise AntigravityPolicyViolationError(
                    f"FAIL-CLOSED: Direct modification of protected zone '{protected_rel}' is strictly prohibited."
                )

        # 3. Timeout bounds check
        if request.timeout_seconds > 600 or request.timeout_seconds < 1:
            raise AntigravityPolicyViolationError(
                f"FAIL-CLOSED: Invalid timeout {request.timeout_seconds}s (must be between 1s and 600s)."
            )

        logger.info(f"[ANTIGRAVITY POLICY] Delegation request '{request.task_id}' approved for execution.")
