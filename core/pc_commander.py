from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
COMMANDER_ROOT = STATE_ROOT / "pc_commander"
SESSIONS_ROOT = COMMANDER_ROOT / "sessions"
JOURNAL_PATH = COMMANDER_ROOT / "journal.jsonl"

COMMANDER_ROOT.mkdir(parents=True, exist_ok=True)
SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)

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

SAFE_ACTIONS = {
    "maintenance_status",
    "maintenance_audit",
    "dust_dry_run",
    "human_status",
    "human_tick_safe",
    "human_reflect",
    "human_chat_brief",
    "brain_status",
    "human_sessions",
}

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def safe_session_name(session: str) -> str:
    raw = (session or "pc").strip().lower()
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw)
    return safe[:80] or "pc"

def session_state_path(session: str) -> Path:
    return SESSIONS_ROOT / f"{safe_session_name(session)}.json"

def append_journal(event: Dict[str, Any]) -> None:
    event.setdefault("created_at", now())
    event.setdefault("version", "v2.22-pc-commander")
    event.setdefault("policy", {
        "cpu_ram_only": True,
        "gpu": "untouched",
        "no_ads": True,
        "safe_actions_only": True,
    })

    with JOURNAL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_session_state(session: str) -> Dict[str, Any]:
    path = session_state_path(session)
    default = {
        "session": safe_session_name(session),
        "pending_proposal_id": None,
        "pending_action": None,
        "pending_label": None,
        "updated_at": None,
    }
    state = read_json(path, default)
    for key, value in default.items():
        state.setdefault(key, value)
    return state

def set_pending(session: str, proposal: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    state = get_session_state(session)

    if proposal:
        state["pending_proposal_id"] = proposal.get("id")
        state["pending_action"] = proposal.get("action")
        state["pending_label"] = proposal.get("label")
        state["updated_at"] = now()
    else:
        state["pending_proposal_id"] = None
        state["pending_action"] = None
        state["pending_label"] = None
        state["updated_at"] = now()

    write_json(session_state_path(session), state)
    return state

def normalize(text: str) -> str:
    return (text or "").strip().lower()

def contains_any(low: str, words: List[str]) -> bool:
    return any(word in low for word in words)

def status() -> Dict[str, Any]:
    sessions = []

    for path in sorted(SESSIONS_ROOT.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        state = read_json(path, {})
        sessions.append({
            "session": path.stem,
            "pending_proposal_id": state.get("pending_proposal_id"),
            "pending_action": state.get("pending_action"),
            "pending_label": state.get("pending_label"),
            "updated_at": state.get("updated_at"),
        })

    return {
        "ok": True,
        "created_at": now(),
        "version": "v2.22-pc-commander",
        "commander_root": str(COMMANDER_ROOT),
        "journal_path": str(JOURNAL_PATH),
        "sessions": sessions,
        "safe_actions": sorted(SAFE_ACTIONS),
        "commands": [
            "CONFIRME",
            "annule",
            "état système",
            "maintenance",
            "audit",
            "brief",
            "sessions",
            "prépare optimisation",
            "réflexion",
            "dust dry-run",
        ],
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "destructive_actions": "forbidden",
            "confirmation_word": "CONFIRME",
        },
    }

def interpret(text: str) -> Dict[str, Any]:
    low = normalize(text)

    if low in ("confirme", "confirmé", "confirmation", "ok confirme", "go confirme"):
        return {
            "kind": "confirm_pending",
            "action": None,
            "requires_confirmation": False,
            "confidence": 1.0,
            "reason": "mot de confirmation détecté",
        }

    if low in ("annule", "annuler", "cancel", "stop"):
        return {
            "kind": "cancel_pending",
            "action": None,
            "requires_confirmation": False,
            "confidence": 1.0,
            "reason": "demande d'annulation détectée",
        }

    if contains_any(low, ["registre", "safe actions", "queue", "file d'action", "file action"]):
        return {
            "kind": "quick",
            "action": "human_sessions",
            "requires_confirmation": False,
            "confidence": 0.75,
            "reason": "demande d'état mémoire/actions",
        }

    if contains_any(low, ["état", "etat", "status", "système", "systeme"]) and contains_any(low, ["rapide", "e-zzio", "ezzio", "pc", "ton"]):
        return {
            "kind": "quick",
            "action": "human_chat_brief",
            "requires_confirmation": False,
            "confidence": 0.95,
            "reason": "état système demandé",
        }

    if contains_any(low, ["maintenance"]) and not contains_any(low, ["audit"]):
        return {
            "kind": "quick",
            "action": "maintenance_status",
            "requires_confirmation": False,
            "confidence": 0.95,
            "reason": "maintenance status demandé",
        }

    if contains_any(low, ["audit", "vérifie les fichiers", "verifie les fichiers", "contrôle", "controle"]):
        return {
            "kind": "quick",
            "action": "maintenance_audit",
            "requires_confirmation": False,
            "confidence": 0.95,
            "reason": "audit demandé",
        }

    if contains_any(low, ["dust", "poussière", "poussiere", "nettoyage dry", "dry-run", "dry run"]):
        return {
            "kind": "quick",
            "action": "dust_dry_run",
            "requires_confirmation": False,
            "confidence": 0.9,
            "reason": "dry-run nettoyage demandé",
        }

    if contains_any(low, ["brief", "résumé", "resume"]):
        return {
            "kind": "quick",
            "action": "human_chat_brief",
            "requires_confirmation": False,
            "confidence": 0.9,
            "reason": "brief demandé",
        }

    if contains_any(low, ["session", "mémoire", "memoire"]):
        return {
            "kind": "quick",
            "action": "human_sessions",
            "requires_confirmation": False,
            "confidence": 0.85,
            "reason": "sessions mémoire demandées",
        }

    if contains_any(low, ["cerveau", "brain", "routeur", "modèles", "modeles"]):
        return {
            "kind": "quick",
            "action": "brain_status",
            "requires_confirmation": False,
            "confidence": 0.85,
            "reason": "état cerveau routeur demandé",
        }

    if contains_any(low, ["human loop", "boucle humaine", "tick"]):
        return {
            "kind": "proposal",
            "action": "human_tick_safe",
            "requires_confirmation": True,
            "confidence": 0.9,
            "reason": "tick human loop demandé",
            "params": {
                "goal": "vérifier E-ZZIO sans rien casser",
                "context": "pc commander",
            },
        }

    if contains_any(low, ["optimisation", "optimiser", "amélioration", "amelioration", "prépare", "prepare"]):
        return {
            "kind": "proposal",
            "action": "human_tick_safe",
            "requires_confirmation": True,
            "confidence": 0.9,
            "reason": "préparation optimisation PC demandée",
            "params": {
                "goal": "préparer la prochaine optimisation PC sans rien casser",
                "context": "pc commander optimisation",
            },
        }

    if contains_any(low, ["réflexion", "reflection", "réfléchis", "reflechis"]):
        return {
            "kind": "proposal",
            "action": "human_reflect",
            "requires_confirmation": True,
            "confidence": 0.85,
            "reason": "réflexion human loop demandée",
            "params": {
                "note": "réflexion commandée : rester prudent, utile, propre, local-first et sans action destructive automatique",
            },
        }

    return {
        "kind": "chat",
        "action": None,
        "requires_confirmation": False,
        "confidence": 0.35,
        "reason": "pas d'action sûre reconnue, fallback chat humain",
    }

def summarize_result(action: str, result: Dict[str, Any]) -> str:
    if action == "maintenance_status":
        return f"Maintenance : ok={result.get('ok')}, bad_count={result.get('bad_count')}, dust={result.get('dust_candidate_count')}."

    if action == "maintenance_audit":
        return f"Audit : ok={result.get('ok')}, checked={result.get('checked_count')}, bad_count={result.get('bad_count')}."

    if action == "dust_dry_run":
        return f"Dry-run poussière : ok={result.get('ok')}, candidats={result.get('candidate_count')}, déplacés=0."

    if action == "human_chat_brief":
        return result.get("summary") or "Brief disponible."

    if action == "brain_status":
        return f"Cerveau routeur : version={result.get('version')}, modèles installés={len(result.get('installed_models', []))}."

    if action == "human_sessions":
        return f"Sessions mémoire : {result.get('session_count')} session(s)."

    if action == "human_status":
        rhythm = result.get("rhythm") or {}
        return f"Human loop actif. Dernier tick : {rhythm.get('last_tick')}. Objectif : {rhythm.get('last_goal')}."

    if action == "human_tick_safe":
        return result.get("summary") or "Tick human loop exécuté."

    if action == "human_reflect":
        return result.get("reflection") or "Réflexion ajoutée."

    return "Action terminée."

def command(text: str, session: str = "pc") -> Dict[str, Any]:
    started = time.time()
    session = safe_session_name(session)
    state = get_session_state(session)
    parsed = interpret(text)

    append_journal({
        "type": "incoming_command",
        "session": session,
        "text": text,
        "parsed": parsed,
    })

    if parsed["kind"] == "confirm_pending":
        proposal_id = state.get("pending_proposal_id")
        if not proposal_id:
            return {
                "ok": False,
                "version": "v2.22-pc-commander",
                "session": session,
                "elapsed_ms": int((time.time() - started) * 1000),
                "reply": "Aucune action en attente à confirmer.",
                "pending": state,
            }

        from core.safe_actions import run_proposal

        run = run_proposal(proposal_id=proposal_id, confirmation="CONFIRME")
        if run.get("ok"):
            set_pending(session, None)

        result = run.get("result") or {}
        reply = summarize_result(run.get("action") or state.get("pending_action"), result) if run.get("ok") else run.get("error")

        output = {
            "ok": bool(run.get("ok")),
            "version": "v2.22-pc-commander",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "mode": "confirm_pending",
            "proposal_id": proposal_id,
            "run": run,
            "reply": reply,
        }
        append_journal({"type": "confirm_result", "session": session, "output": output})
        return output

    if parsed["kind"] == "cancel_pending":
        proposal_id = state.get("pending_proposal_id")
        if not proposal_id:
            return {
                "ok": True,
                "version": "v2.22-pc-commander",
                "session": session,
                "elapsed_ms": int((time.time() - started) * 1000),
                "reply": "Aucune action en attente à annuler.",
            }

        from core.safe_actions import cancel_proposal

        cancel = cancel_proposal(proposal_id=proposal_id, reason="annulation via PC Commander")
        if cancel.get("ok"):
            set_pending(session, None)

        output = {
            "ok": bool(cancel.get("ok")),
            "version": "v2.22-pc-commander",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "mode": "cancel_pending",
            "proposal_id": proposal_id,
            "cancel": cancel,
            "reply": "Action en attente annulée." if cancel.get("ok") else cancel.get("error"),
        }
        append_journal({"type": "cancel_result", "session": session, "output": output})
        return output

    if parsed["kind"] == "quick":
        from core.safe_actions import quick_action

        action = parsed.get("action")
        quick = quick_action(action=action, params={})
        result = quick.get("result") or {}
        reply = summarize_result(action, result) if quick.get("ok") else quick.get("error")

        output = {
            "ok": bool(quick.get("ok")),
            "version": "v2.22-pc-commander",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "mode": "quick_safe_action",
            "parsed": parsed,
            "action": action,
            "safe_action": quick,
            "reply": reply,
            "requires_confirmation": False,
        }
        append_journal({"type": "quick_result", "session": session, "output": output})
        return output

    if parsed["kind"] == "proposal":
        from core.safe_actions import propose_action

        action = parsed.get("action")
        params = parsed.get("params") or {}
        proposal = propose_action(action=action, params=params, reason=parsed.get("reason") or "pc commander proposal")

        if proposal.get("ok"):
            set_pending(session, proposal)

        reply = (
            f"J'ai préparé une action sûre : {proposal.get('label')}. "
            f"Elle attend confirmation. Tape exactement CONFIRME pour l'exécuter, ou annule pour l'abandonner."
            if proposal.get("ok") else
            proposal.get("error")
        )

        output = {
            "ok": bool(proposal.get("ok")),
            "version": "v2.22-pc-commander",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "mode": "proposal_requires_confirmation",
            "parsed": parsed,
            "proposal": proposal,
            "reply": reply,
            "requires_confirmation": True,
        }
        append_journal({"type": "proposal_result", "session": session, "output": output})
        return output

    from core.human_chat import human_chat

    fallback = human_chat(
        text=text,
        session=session,
        task="auto",
        speed="auto",
        predict=220,
    )

    output = {
        "ok": bool(fallback.get("ok")),
        "version": "v2.22-pc-commander",
        "session": session,
        "elapsed_ms": int((time.time() - started) * 1000),
        "mode": "fallback_human_chat",
        "parsed": parsed,
        "reply": fallback.get("reply"),
        "human_chat": fallback,
    }
    append_journal({"type": "fallback_result", "session": session, "output": output})
    return output
