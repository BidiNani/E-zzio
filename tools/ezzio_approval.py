"""
E-ZZIO Sovereign CLI — HITL Approval Tool.
Permet à l'opérateur d'interagir directement avec le moteur d'approbation humaine.
Commandes :
  ezzio-approval list
  ezzio-approval approve <approval_id> [--reason <texte>] [--by <nom>]
  ezzio-approval reject <approval_id> [--reason <texte>] [--by <nom>]
"""
import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

# Assurer l'import de core.*
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.governance.approval import (
    ApprovalExpiredError,
    DecisionChoice,
    StateTransitionError,
    approval_manager,
)


def format_time_remaining(expires_at_str: str) -> str:
    try:
        exp_dt = datetime.fromisoformat(expires_at_str)
        now_dt = datetime.now(UTC)
        diff = int((exp_dt - now_dt).total_seconds())
        if diff <= 0:
            return "EXPIRED"
        m, s = divmod(diff, 60)
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "UNKNOWN"


def cmd_list(args):
    pending = approval_manager.get_pending()
    if not pending:
        print("Aucune demande d'approbation en attente.")
        return 0

    print(f"\n{'ID':<18} {'TASK':<16} {'AGENT':<15} {'CAPABILITY':<20} {'SCOPE':<18} {'STATUS':<10} {'TIME LEFT':<10}")
    print("-" * 115)
    for r in pending:
        t_left = format_time_remaining(r.expires_at)
        print(f"{r.approval_id:<18} {r.task_id:<16} {r.agent_id:<15} {r.capability_name:<20} {r.scope:<18} {r.status.value:<10} {t_left:<10}")
        print(f"  └─ Résumé : {r.safe_summary}")
    print()
    return 0


def cmd_approve(args):
    try:
        updated = approval_manager.decide(
            approval_id=args.approval_id,
            choice=DecisionChoice.APPROVE,
            decided_by=args.by,
            reason=args.reason,
        )
        print(f"[OK] Demande '{updated.approval_id}' APPROUVÉE avec succès par {updated.decided_by}.")
        return 0
    except KeyError:
        print(f"[ERREUR] Demande inconnue : {args.approval_id}", file=sys.stderr)
        return 1
    except ApprovalExpiredError as exc:
        print(f"[EXPORATION] {exc}", file=sys.stderr)
        return 2
    except StateTransitionError as exc:
        print(f"[CONFLIT] {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 4


def cmd_reject(args):
    try:
        updated = approval_manager.decide(
            approval_id=args.approval_id,
            choice=DecisionChoice.REJECT,
            decided_by=args.by,
            reason=args.reason,
        )
        print(f"[OK] Demande '{updated.approval_id}' REJETÉE avec succès par {updated.decided_by}.")
        return 0
    except KeyError:
        print(f"[ERREUR] Demande inconnue : {args.approval_id}", file=sys.stderr)
        return 1
    except ApprovalExpiredError as exc:
        print(f"[EXPIRATION] {exc}", file=sys.stderr)
        return 2
    except StateTransitionError as exc:
        print(f"[CONFLIT] {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 4


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Human Approval CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="Lister les demandes en attente")

    # approve
    p_appr = subparsers.add_parser("approve", help="Approuver une demande")
    p_appr.add_argument("approval_id", help="Identifiant de l'approbation")
    p_appr.add_argument("--reason", default="Approuvé via CLI", help="Motif")
    p_appr.add_argument("--by", default="cli_operator", help="Opérateur")

    # reject
    p_rej = subparsers.add_parser("reject", help="Rejeter une demande")
    p_rej.add_argument("approval_id", help="Identifiant de l'approbation")
    p_rej.add_argument("--reason", default="Rejeté via CLI", help="Motif")
    p_rej.add_argument("--by", default="cli_operator", help="Opérateur")

    args = parser.parse_args()
    if args.command == "list":
        sys.exit(cmd_list(args))
    elif args.command == "approve":
        sys.exit(cmd_approve(args))
    elif args.command == "reject":
        sys.exit(cmd_reject(args))


if __name__ == "__main__":
    main()
