from __future__ import annotations
import shutil
from pathlib import Path
from runtime.kernel.context import RuntimeContext
from runtime.recovery.snapshot import SnapshotManager


class RecoveryActions:
    """Bibliothèque des actions de remédiation active incluant le rollback transactionnel."""

    snapshot_manager = SnapshotManager()

    @staticmethod
    def force_quarantine(context: RuntimeContext, actor: str, reason: str) -> bool:
        if hasattr(context.policy, "trust_scorer") and context.policy.trust_scorer:
            score = context.policy.trust_scorer.get_score(actor)
            context.policy.trust_scorer.penalize(actor, points=score, reason=f"RECOVERY_QUARANTINE: {reason}")
            return True
        return False

    @staticmethod
    def purge_execution_workspace(execution_id: str) -> bool:
        workspace = Path("runtime/workspaces/executions") / execution_id
        if workspace.exists() and workspace.is_dir():
            try:
                shutil.rmtree(workspace)
                return True
            except Exception:
                return False
        return False

    @classmethod
    def execute_rollback(cls, execution_id: str) -> bool:
        """Déclenche la restauration des fichiers via le SnapshotManager."""
        success = cls.snapshot_manager.rollback(execution_id)
        cls.snapshot_manager.purge_snapshot(execution_id)
        return success
