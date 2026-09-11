"""
E-ZZIO Sovereign Discord — HITL Approval Bridge & View.
Fournit le composant interactif Discord (boutons Approuver/Refuser) et le contrôleur de callback
qui dialogue directement avec le ApprovalManager canonique sans contournement.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.governance.approval import (
    ApprovalExpiredError,
    ApprovalManager,
    ApprovalStatus,
    DecisionChoice,
    DoubleExecutionError,
    StateTransitionError,
    approval_manager,
)

logger = logging.getLogger("DiscordHITL")


def format_time_remaining(expires_at_str: str) -> str:
    try:
        exp_dt = datetime.fromisoformat(expires_at_str)
        now_dt = datetime.now(timezone.utc)
        diff = int((exp_dt - now_dt).total_seconds())
        if diff <= 0:
            return "00:00 (Expiré)"
        m, s = divmod(diff, 60)
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "00:00"


class DiscordApprovalController:
    """Contrôleur applicatif pour les interactions d'approbation Discord."""

    def __init__(self, manager: Optional[ApprovalManager] = None):
        self.manager = manager or approval_manager

    def build_approval_embed_payload(self, approval_id: str) -> Dict[str, Any]:
        """Génère le dictionnaire de rendu Discord pour une demande d'approbation."""
        req = self.manager.get(approval_id)
        if not req:
            raise KeyError(f"Demande introuvable : {approval_id}")

        time_left = format_time_remaining(req.expires_at)

        return {
            "title": "🛡️ E-ZZIO HITL — Validation Requise",
            "description": f"Une action sensible requiert votre validation humaine explicite.",
            "fields": [
                {"name": "ID Approbation", "value": f"`{req.approval_id}`", "inline": True},
                {"name": "Tâche", "value": f"`{req.task_id}`", "inline": True},
                {"name": "Agent", "value": req.agent_id, "inline": True},
                {"name": "Capacité", "value": f"`{req.capability_name}`", "inline": True},
                {"name": "Scope", "value": f"`{req.scope}`", "inline": True},
                {"name": "Statut", "value": req.status.value, "inline": True},
                {"name": "Résumé", "value": req.safe_summary, "inline": False},
                {"name": "Temps restant", "value": f"⏳ **{time_left}**", "inline": False},
            ],
            "color": 0xFFA500 if req.status == ApprovalStatus.PENDING else (0x00FF00 if req.status == ApprovalStatus.APPROVED else 0xFF0000),
        }

    def handle_interaction_decision(
        self,
        approval_id: str,
        choice_str: str,
        user_id: str,
        username: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Traite le clic d'un bouton Discord en déléguant au ApprovalManager."""
        try:
            choice = DecisionChoice(choice_str.upper())
        except ValueError:
            return {
                "ok": False,
                "error": f"Choix de décision non valide : {choice_str}",
                "code": "INVALID_CHOICE",
            }

        decided_by = f"discord:{user_id} ({username})"
        try:
            updated = self.manager.decide(
                approval_id=approval_id,
                choice=choice,
                decided_by=decided_by,
                reason=reason or f"Action {choice.value} via interface Discord",
            )
            return {
                "ok": True,
                "approval_id": updated.approval_id,
                "status": updated.status.value,
                "decided_by": updated.decided_by,
                "message": f"Demande `{approval_id}` {updated.status.value} par {username}.",
            }
        except KeyError:
            return {"ok": False, "error": f"Demande inconnue : {approval_id}", "code": "NOT_FOUND"}
        except ApprovalExpiredError as exc:
            return {"ok": False, "error": f"Demande expirée : {exc}", "code": "EXPIRED"}
        except StateTransitionError as exc:
            return {"ok": False, "error": f"Action déjà traitée ou interdite : {exc}", "code": "CONFLICT"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "code": "INTERNAL_ERROR"}


discord_approval_controller = DiscordApprovalController()
