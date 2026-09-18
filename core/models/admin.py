"""E-ZZIO Fabric Administration CLI — core/models/admin.py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models.fabric import build_fabric


def main() -> None:
    parser = argparse.ArgumentParser(description="E-ZZIO Model Fabric — Administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_p = subparsers.add_parser("list", help="Lister les modèles du registre.")
    list_p.add_argument("--quarantined-only", action="store_true", help="Afficher uniquement les modèles en quarantaine.")
    list_p.add_argument("--active-only", action="store_true", help="Afficher uniquement les modèles actifs.")

    show_p = subparsers.add_parser("show", help="Afficher la fiche forensic d'un modèle.")
    show_p.add_argument("--provider", required=True, help="Fournisseur.")
    show_p.add_argument("--model-id", required=True, help="ID du modèle.")

    rehab_p = subparsers.add_parser("rehabilitate", help="Réhabiliter un modèle de QUARANTINED vers CANDIDATE.")
    rehab_p.add_argument("--provider", required=True, help="Fournisseur.")
    rehab_p.add_argument("--model-id", required=True, help="ID du modèle.")
    rehab_p.add_argument("--reason", required=True, help="Motif explicite (>= 5 caractères).")
    rehab_p.add_argument("--operator", required=True, help="Identifiant opérateur (>= 2 caractères).")
    rehab_p.add_argument("--dry-run", action="store_true", help="Simuler la réhabilitation.")

    args = parser.parse_args()
    fabric = build_fabric(project_root=PROJECT_ROOT)

    if args.command == "list":
        models = fabric.registry.all() if hasattr(fabric.registry, "all") else list(fabric.registry.models.values())
        if args.quarantined_only:
            models = [m for m in models if getattr(m, "lifecycle", "") == "QUARANTINED"]
        elif args.active_only:
            models = [m for m in models if getattr(m, "lifecycle", "") == "ACTIVE"]

        print(f"\n--- Modèles E-ZZIO ({len(models)} correspondants) ---")
        for m in models:
            failures = getattr(m, "failure_count", 0)
            hist = getattr(m, "historical_failures", 0)
            print(f"[{getattr(m, 'lifecycle', 'UNKNOWN'):<11}] [{getattr(m, 'tier', 'UNQUALIFIED'):<11}] {m.provider}/{m.model_id} (échecs: {failures}, hist: {hist})")

    elif args.command == "show":
        entry = fabric.registry.find(args.provider, args.model_id)
        if not entry:
            print(f"[FAIL] Modèle {args.provider}/{args.model_id} introuvable.", file=sys.stderr)
            sys.exit(1)
        data = {k: v for k, v in entry.__dict__.items() if not k.startswith("_")}
        print(f"\n=== FICHE FORENSIQUE : {args.provider}/{args.model_id} ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.command == "rehabilitate":
        if len(args.operator.strip()) < 2:
            print("[FAIL] Paramètre --operator invalide (min 2 caractères).", file=sys.stderr)
            sys.exit(1)
        if len(args.reason.strip()) < 5:
            print("[FAIL] Paramètre --reason invalide (min 5 caractères).", file=sys.stderr)
            sys.exit(1)

        entry = fabric.registry.find(args.provider, args.model_id)
        if not entry:
            print(f"[FAIL] Modèle {args.provider}/{args.model_id} introuvable.", file=sys.stderr)
            sys.exit(1)

        if getattr(entry, "lifecycle", "") != "QUARANTINED":
            print(f"[FAIL] INVALID_STATE : État attendu QUARANTINED, obtenu {getattr(entry, 'lifecycle', '')}.", file=sys.stderr)
            sys.exit(1)

        if args.dry_run:
            print(f"[PASS] Simulation réussie : QUARANTINED -> CANDIDATE pour {args.provider}/{args.model_id}")
            sys.exit(0)

        success = fabric.rehabilitate_model(
            provider=args.provider,
            model_id=args.model_id,
            reason=args.reason.strip(),
            operator=args.operator.strip(),
        )
        if success:
            print(f"[PASS] Modèle {args.provider}/{args.model_id} réhabilité avec succès vers CANDIDATE.")
        else:
            print("[FAIL] Échec de la réhabilitation.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
