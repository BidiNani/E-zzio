from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
QUEUE_ROOT = STATE_ROOT / "safe_actions"
QUEUE_PATH = QUEUE_ROOT / "queue.jsonl"
RUNS_PATH = QUEUE_ROOT / "runs.jsonl"

QUEUE_ROOT.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

ACTION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "maintenance_status": {
        "label": "Lire l'état maintenance",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
    "maintenance_audit": {
        "label": "Lire l'audit complet",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
    "dust_dry_run": {
        "label": "Préparer un nettoyage poussière en dry-run uniquement",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "dry_run",
    },
    "human_status": {
        "label": "Lire l'état human loop",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
    "human_tick_safe": {
        "label": "Exécuter un tick human loop sûr",
        "safe": True,
        "destructive": False,
        "requires_confirmation": True,
        "kind": "safe_observation",
    },
    "human_reflect": {
        "label": "Ajouter une réflexion human loop",
        "safe": True,
        "destructive": False,
        "requires_confirmation": True,
        "kind": "journal",
    },
    "human_chat_brief": {
        "label": "Lire le brief humain PC",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
    "brain_status": {
        "label": "Lire l'état du cerveau routeur",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
    "human_sessions": {
        "label": "Lister les sessions mémoire human chat",
        "safe": True,
        "destructive": False,
        "requires_confirmation": False,
        "kind": "read",
    },
}

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

def read_jsonl(path: Path, limit: int = 500) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: List[Dict[str, Any]] = []

    for line in lines[-max(1, min(int(limit), 5000)):]:
        try:
            output.append(json.loads(line))
        except Exception:
            output.append({"broken_line": line[:400]})

    return output

def registry() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": "v2.21.2-safe-action-ledger",
        "actions": ACTION_REGISTRY,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "destructive_actions": "forbidden",
            "safe_write_actions": "confirmation_required",
        },
    }

def run_index() -> Dict[str, Dict[str, Any]]:
    runs = read_jsonl(RUNS_PATH, limit=5000)
    index: Dict[str, Dict[str, Any]] = {}

    for run in runs:
        proposal_id = run.get("proposal_id")
        if proposal_id:
            index[proposal_id] = run

    return index

def augment_queue_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    runs_by_proposal = run_index()
    augmented: List[Dict[str, Any]] = []

    for item in items:
        clone = dict(item)
        proposal_id = clone.get("id")
        run = runs_by_proposal.get(proposal_id)

        if run:
            clone["effective_status"] = "executed" if run.get("ok") else "executed_failed"
            clone["executed"] = True
            clone["run_id"] = run.get("id")
            clone["run_ok"] = run.get("ok")
            clone["run_elapsed_ms"] = run.get("elapsed_ms")
            clone["run_created_at"] = run.get("created_at")
        else:
            clone["effective_status"] = "pending_confirmation" if clone.get("requires_confirmation") else "pending_read"
            clone["executed"] = False
            clone["run_id"] = None
            clone["run_ok"] = None
            clone["run_elapsed_ms"] = None
            clone["run_created_at"] = None

        augmented.append(clone)

    return augmented

def ledger(limit: int = 100) -> Dict[str, Any]:
    raw_items = read_jsonl(QUEUE_PATH, limit=limit)
    items = augment_queue_items(raw_items)

    executed = [item for item in items if item.get("executed")]
    pending = [item for item in items if not item.get("executed")]
    pending_confirmation = [item for item in pending if item.get("requires_confirmation")]
    pending_read = [item for item in pending if not item.get("requires_confirmation")]

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.21.2-safe-action-ledger",
        "count": len(items),
        "executed_count": len(executed),
        "pending_count": len(pending),
        "pending_confirmation_count": len(pending_confirmation),
        "pending_read_count": len(pending_read),
        "items": items,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "destructive_actions": "forbidden",
        },
    }

def status() -> Dict[str, Any]:
    data = ledger(limit=5000)
    runs = read_jsonl(RUNS_PATH, limit=50)

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.21.2-safe-action-ledger",
        "queue_path": str(QUEUE_PATH),
        "runs_path": str(RUNS_PATH),
        "known_actions": len(ACTION_REGISTRY),
        "queued_count": data["count"],
        "executed_count": data["executed_count"],
        "pending_count": data["pending_count"],
        "pending_confirmation_count": data["pending_confirmation_count"],
        "pending_read_count": data["pending_read_count"],
        "recent_runs": runs[-10:],
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "destructive_actions": "forbidden",
            "confirmation_word": "CONFIRME",
        },
    }

def propose_action(action: str, params: Optional[Dict[str, Any]] = None, reason: str = "") -> Dict[str, Any]:
    params = params or {}

    if action not in ACTION_REGISTRY:
        return {
            "ok": False,
            "error": f"Action inconnue : {action}",
            "known_actions": sorted(ACTION_REGISTRY.keys()),
        }

    spec = ACTION_REGISTRY[action]

    if not spec.get("safe") or spec.get("destructive"):
        return {
            "ok": False,
            "error": "Action refusée : non sûre ou destructive.",
            "action": action,
            "spec": spec,
        }

    proposal = {
        "ok": True,
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "version": "v2.21.2-safe-action-ledger",
        "status": "proposed",
        "action": action,
        "label": spec.get("label"),
        "params": params,
        "reason": reason,
        "requires_confirmation": bool(spec.get("requires_confirmation")),
        "safe": True,
        "destructive": False,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
        },
    }

    append_jsonl(QUEUE_PATH, proposal)
    return proposal

def queue(limit: int = 50) -> Dict[str, Any]:
    items = augment_queue_items(read_jsonl(QUEUE_PATH, limit=limit))
    return {
        "ok": True,
        "version": "v2.21.2-safe-action-ledger",
        "count": len(items),
        "items": items,
    }

def find_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    items = read_jsonl(QUEUE_PATH, limit=5000)
    for item in reversed(items):
        if item.get("id") == proposal_id:
            return item
    return None

def already_executed(proposal_id: str) -> Optional[Dict[str, Any]]:
    return run_index().get(proposal_id)

def run_action_logic(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}

    if action == "maintenance_status":
        from core.project_janitor import maintenance_status
        return maintenance_status()

    if action == "maintenance_audit":
        from core.project_janitor import audit_project
        return audit_project()

    if action == "dust_dry_run":
        from core.project_janitor import quarantine_dust
        return quarantine_dust(apply=False)

    if action == "human_status":
        from core.human_loop import status as human_status
        return human_status()

    if action == "human_tick_safe":
        from core.human_loop import tick
        return tick(
            user_goal=str(params.get("goal") or "rester stable et prêt"),
            context=str(params.get("context") or "safe action queue"),
            execute=True,
        )

    if action == "human_reflect":
        from core.human_loop import reflect
        return reflect(note=str(params.get("note") or "réflexion action queue"))

    if action == "human_chat_brief":
        from core.human_chat import build_brief
        return build_brief()

    if action == "brain_status":
        from core.pc_model_router import router_status
        return router_status()

    if action == "human_sessions":
        from core.human_chat import list_sessions
        return list_sessions()

    return {
        "ok": False,
        "error": f"Action non implémentée : {action}",
    }

def run_proposal(proposal_id: str, confirmation: str = "") -> Dict[str, Any]:
    proposal = find_proposal(proposal_id)
    if not proposal:
        return {
            "ok": False,
            "error": f"Proposition introuvable : {proposal_id}",
        }

    existing_run = already_executed(proposal_id)
    if existing_run:
        return {
            "ok": True,
            "already_executed": True,
            "proposal_id": proposal_id,
            "action": proposal.get("action"),
            "existing_run": existing_run,
            "message": "Cette proposition a déjà été exécutée. Aucun doublon lancé.",
        }

    action = proposal.get("action")
    spec = ACTION_REGISTRY.get(action)

    if not spec:
        return {
            "ok": False,
            "error": f"Action inconnue dans proposition : {action}",
        }

    if spec.get("destructive") or not spec.get("safe"):
        return {
            "ok": False,
            "error": "Action refusée : non sûre ou destructive.",
            "proposal": proposal,
        }

    if spec.get("requires_confirmation") and confirmation != "CONFIRME":
        return {
            "ok": False,
            "error": "Confirmation requise. Utilise exactement CONFIRME.",
            "requires_confirmation": True,
            "proposal": proposal,
        }

    started = time.time()

    try:
        result = run_action_logic(action, proposal.get("params") or {})
        ok = bool(result.get("ok", True)) if isinstance(result, dict) else True
    except Exception as exc:
        result = {
            "ok": False,
            "error": str(exc),
        }
        ok = False

    run = {
        "ok": ok,
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "version": "v2.21.2-safe-action-ledger",
        "proposal_id": proposal_id,
        "action": action,
        "elapsed_ms": int((time.time() - started) * 1000),
        "result": result,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "destructive": False,
        },
    }

    append_jsonl(RUNS_PATH, run)
    return run

def quick_action(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}

    if action not in ACTION_REGISTRY:
        return {
            "ok": False,
            "error": f"Action inconnue : {action}",
            "known_actions": sorted(ACTION_REGISTRY.keys()),
        }

    spec = ACTION_REGISTRY[action]

    if spec.get("requires_confirmation"):
        proposal = propose_action(action=action, params=params, reason="quick_action_requires_confirmation")
        return {
            "ok": True,
            "queued": True,
            "requires_confirmation": True,
            "proposal": proposal,
            "message": "Action proposée mais non exécutée : confirmation requise.",
        }

    proposal = propose_action(action=action, params=params, reason="quick_action_read_only")
    return run_proposal(proposal_id=proposal["id"], confirmation="")
