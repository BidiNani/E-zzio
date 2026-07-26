from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
HUMAN_ROOT = STATE_ROOT / "human_loop"
JOURNAL_PATH = HUMAN_ROOT / "journal.jsonl"
MEMORY_PATH = HUMAN_ROOT / "memory.json"
INTENT_PATH = HUMAN_ROOT / "current_intent.json"
SNAPSHOT_PATH = HUMAN_ROOT / "last_perception.json"

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

HUMAN_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_MEMORY: Dict[str, Any] = {
    "version": "v2.19-pc-human-loop",
    "identity": {
        "name": "E-ZZIO",
        "role": "ami IA local d'Enrik sur PC",
        "style": "humain, prudent, utile, honnête, professionnel",
    },
    "doctrine": {
        "cpu_ram_only": True,
        "gpu": "untouched",
        "no_ads": True,
        "no_tracking": True,
        "no_sponsors": True,
        "no_destructive_action_without_confirmation": True,
        "prefer_backup_logs_json_validation": True,
    },
    "rhythm": {
        "mode": "manual_tick",
        "autonomous_actions": "safe_only",
        "last_tick": None,
    },
    "learned_preferences": [
        "Répondre en français.",
        "Privilégier PowerShell propre, court ou modulaire, avec chemins intégrés.",
        "Toujours protéger la GTX 1650 et rester CPU/RAM/NVMe-first.",
        "Éviter publicité, tracking, sponsors et recommandations payées.",
    ],
}

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def safe_read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def safe_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def append_journal(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "type": event_type,
        "payload": payload,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "safe_only": True,
        },
    }

    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event

def load_memory() -> Dict[str, Any]:
    memory = safe_read_json(MEMORY_PATH, DEFAULT_MEMORY)
    changed = False

    for key, value in DEFAULT_MEMORY.items():
        if key not in memory:
            memory[key] = value
            changed = True

    if changed or not MEMORY_PATH.exists():
        safe_write_json(MEMORY_PATH, memory)

    return memory

def save_memory(memory: Dict[str, Any]) -> Dict[str, Any]:
    memory["version"] = "v2.19-pc-human-loop"
    safe_write_json(MEMORY_PATH, memory)
    return memory

def journal_tail(limit: int = 20) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 200))

    if not JOURNAL_PATH.exists():
        return {
            "ok": True,
            "events": [],
            "count": 0,
            "journal_path": str(JOURNAL_PATH),
        }

    lines = JOURNAL_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    events = []

    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except Exception:
            events.append({"broken_line": line[:500]})

    return {
        "ok": True,
        "events": events,
        "count": len(events),
        "journal_path": str(JOURNAL_PATH),
    }

def project_health() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ok": True,
        "maintenance": None,
        "brain": None,
        "errors": [],
    }

    try:
        from core.project_janitor import maintenance_status

        result["maintenance"] = maintenance_status()
        if not result["maintenance"].get("ok", False):
            result["ok"] = False
    except Exception as exc:
        result["ok"] = False
        result["errors"].append({
            "where": "maintenance_status",
            "error": str(exc),
        })

    try:
        from core.pc_model_router import router_status

        brain_status = router_status()
        result["brain"] = {
            "ok": brain_status.get("ok", False),
            "version": brain_status.get("version"),
            "policy_path": brain_status.get("policy_path"),
            "installed_count": len(brain_status.get("installed_models", [])),
            "latest_guarded_bench": brain_status.get("latest_guarded_bench"),
        }
        if not result["brain"]["ok"]:
            result["ok"] = False
    except Exception as exc:
        result["ok"] = False
        result["errors"].append({
            "where": "router_status",
            "error": str(exc),
        })

    return result

def perceive(context: str = "") -> Dict[str, Any]:
    memory = load_memory()
    health = project_health()

    perception = {
        "ok": True,
        "created_at": now(),
        "version": "v2.19-pc-human-loop",
        "context": context,
        "identity": memory.get("identity"),
        "doctrine": memory.get("doctrine"),
        "health": health,
        "signals": {
            "system_clean": bool(health.get("ok")),
            "maintenance_ok": bool((health.get("maintenance") or {}).get("ok", False)),
            "brain_known": bool(health.get("brain")),
            "manual_tick": True,
            "destructive_actions_allowed": False,
        },
    }

    safe_write_json(SNAPSHOT_PATH, perception)
    append_journal("perception", perception)

    return perception

def choose_intention(perception: Dict[str, Any], user_goal: str = "") -> Dict[str, Any]:
    health = perception.get("health", {})
    maintenance = health.get("maintenance") or {}
    signals = perception.get("signals", {})

    if user_goal.strip():
        goal = user_goal.strip()
    elif not signals.get("system_clean", False):
        goal = "stabiliser le système local avant toute évolution"
    else:
        goal = "rester prêt, propre, rapide et utile sur PC"

    risks: List[str] = []
    if not maintenance.get("ok", False):
        risks.append("maintenance signale encore des éléments à vérifier")

    intention = {
        "ok": True,
        "created_at": now(),
        "goal": goal,
        "mood": "calme, attentif, protecteur",
        "priority": "stabilité locale PC",
        "risk_level": "low" if not risks else "medium",
        "risks": risks,
        "rules": [
            "ne rien supprimer sans confirmation",
            "ne pas toucher au GPU",
            "journaliser les décisions",
            "préférer actions sûres et vérifiables",
            "garder zéro publicité et zéro tracking",
        ],
    }

    safe_write_json(INTENT_PATH, intention)
    append_journal("intention", intention)

    return intention

def build_plan(perception: Dict[str, Any], intention: Dict[str, Any]) -> Dict[str, Any]:
    maintenance = (perception.get("health") or {}).get("maintenance") or {}
    bad_count = int(maintenance.get("bad_count", 0) or 0)
    dust_count = int(maintenance.get("dust_candidate_count", 0) or 0)

    steps: List[Dict[str, Any]] = []

    steps.append({
        "id": "verify_maintenance",
        "label": "Vérifier l'audit maintenance",
        "safe": True,
        "destructive": False,
        "suggested_endpoint": "/maintenance/status",
    })

    steps.append({
        "id": "verify_brain_gateway",
        "label": "Vérifier le cerveau routeur PC",
        "safe": True,
        "destructive": False,
        "suggested_endpoint": "/api/brain/status",
    })

    if bad_count > 0:
        steps.append({
            "id": "inspect_bad_items",
            "label": "Inspecter les fichiers signalés par l'audit",
            "safe": True,
            "destructive": False,
            "suggested_endpoint": "/maintenance/audit",
        })

    if dust_count > 0:
        steps.append({
            "id": "dust_dry_run_only",
            "label": "Préparer un nettoyage poussière en dry-run uniquement",
            "safe": True,
            "destructive": False,
            "suggested_script": "G:/AI/E-zzio/scripts/ezzio_clean_dust.ps1",
        })

    steps.append({
        "id": "record_state",
        "label": "Journaliser l'état et rester prêt",
        "safe": True,
        "destructive": False,
        "suggested_file": str(JOURNAL_PATH),
    })

    plan = {
        "ok": True,
        "created_at": now(),
        "goal": intention.get("goal"),
        "steps": steps,
        "execute_mode": "safe_observation_only",
        "requires_confirmation_for": [
            "suppression",
            "quarantaine appliquée",
            "modification massive",
            "connexion externe",
            "action Discord ou Messenger réelle",
        ],
    }

    append_journal("plan", plan)
    return plan

def execute_safe_step(step: Dict[str, Any]) -> Dict[str, Any]:
    step_id = step.get("id")

    if step_id == "verify_maintenance":
        try:
            from core.project_janitor import maintenance_status
            data = maintenance_status()
            return {
                "ok": bool(data.get("ok")),
                "step_id": step_id,
                "action": "read_maintenance_status",
                "data": data,
            }
        except Exception as exc:
            return {
                "ok": False,
                "step_id": step_id,
                "error": str(exc),
            }

    if step_id == "verify_brain_gateway":
        try:
            from core.pc_model_router import router_status
            data = router_status()
            return {
                "ok": bool(data.get("ok")),
                "step_id": step_id,
                "action": "read_brain_status",
                "data": {
                    "version": data.get("version"),
                    "installed_count": len(data.get("installed_models", [])),
                    "latest_guarded_bench": data.get("latest_guarded_bench"),
                },
            }
        except Exception as exc:
            return {
                "ok": False,
                "step_id": step_id,
                "error": str(exc),
            }

    if step_id == "inspect_bad_items":
        try:
            from core.project_janitor import audit_project
            data = audit_project()
            return {
                "ok": bool(data.get("ok")),
                "step_id": step_id,
                "action": "read_audit",
                "bad_count": data.get("bad_count"),
                "bad": data.get("bad", []),
            }
        except Exception as exc:
            return {
                "ok": False,
                "step_id": step_id,
                "error": str(exc),
            }

    if step_id == "dust_dry_run_only":
        try:
            from core.project_janitor import quarantine_dust
            data = quarantine_dust(apply=False)
            return {
                "ok": bool(data.get("ok")),
                "step_id": step_id,
                "action": "dust_dry_run_only",
                "candidate_count": data.get("candidate_count"),
                "data": data,
            }
        except Exception as exc:
            return {
                "ok": False,
                "step_id": step_id,
                "error": str(exc),
            }

    if step_id == "record_state":
        return {
            "ok": True,
            "step_id": step_id,
            "action": "journal_ready",
            "journal_path": str(JOURNAL_PATH),
        }

    return {
        "ok": True,
        "step_id": step_id,
        "action": "skipped_unknown_safe_step",
    }

def tick(user_goal: str = "", context: str = "", execute: bool = True) -> Dict[str, Any]:
    started = time.time()

    perception = perceive(context=context)
    intention = choose_intention(perception, user_goal=user_goal)
    plan = build_plan(perception, intention)

    results: List[Dict[str, Any]] = []

    if execute:
        for step in plan.get("steps", []):
            if not step.get("safe", False) or step.get("destructive", False):
                results.append({
                    "ok": False,
                    "step_id": step.get("id"),
                    "skipped": True,
                    "reason": "unsafe_or_destructive",
                })
                continue
            results.append(execute_safe_step(step))

    verified_ok = all(item.get("ok", False) for item in results) if results else True

    memory = load_memory()
    memory.setdefault("rhythm", {})
    memory["rhythm"]["last_tick"] = now()
    memory["rhythm"]["last_goal"] = intention.get("goal")
    save_memory(memory)

    output = {
        "ok": verified_ok,
        "created_at": now(),
        "version": "v2.19-pc-human-loop",
        "elapsed_ms": int((time.time() - started) * 1000),
        "perception": perception,
        "intention": intention,
        "plan": plan,
        "results": results,
        "summary": summarize_tick(verified_ok, intention, results),
    }

    append_journal("tick", output)
    return output

def summarize_tick(ok: bool, intention: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    goal = intention.get("goal", "rester stable")
    if ok:
        return f"E-ZZIO est calme et prêt : {goal}. Les vérifications sûres sont passées."
    failed = [item for item in results if not item.get("ok")]
    return f"E-ZZIO reste prudent : {goal}. {len(failed)} point(s) demandent inspection."

def reflect(note: str = "") -> Dict[str, Any]:
    memory = load_memory()
    tail = journal_tail(limit=12)

    reflection = {
        "ok": True,
        "created_at": now(),
        "version": "v2.19-pc-human-loop",
        "note": note,
        "identity": memory.get("identity"),
        "doctrine": memory.get("doctrine"),
        "recent_event_count": tail.get("count", 0),
        "reflection": (
            "Je dois rester utile, calme, local-first, sans pub ni tracking. "
            "Je peux observer, planifier, vérifier et journaliser. "
            "Je ne dois pas effectuer d'action destructive sans confirmation explicite."
        ),
    }

    append_journal("reflection", reflection)
    return reflection

def status() -> Dict[str, Any]:
    memory = load_memory()
    health = project_health()
    tail = journal_tail(limit=5)

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.19-pc-human-loop",
        "state_root": str(HUMAN_ROOT),
        "journal_path": str(JOURNAL_PATH),
        "memory_path": str(MEMORY_PATH),
        "identity": memory.get("identity"),
        "doctrine": memory.get("doctrine"),
        "rhythm": memory.get("rhythm"),
        "health": health,
        "recent_events": tail.get("events", []),
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "safe_only": True,
        },
    }
