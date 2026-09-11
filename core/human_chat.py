from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.human_chat_guard import deterministic_human_reply, sanitize_human_chat_reply

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
CHAT_ROOT = STATE_ROOT / "human_chat"
SESSIONS_ROOT = CHAT_ROOT / "sessions"

CHAT_ROOT.mkdir(parents=True, exist_ok=True)
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


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def safe_session_name(name: str) -> str:
    raw = (name or "pc").strip().lower()
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw)
    return safe[:80] or "pc"


def session_path(session: str) -> Path:
    return SESSIONS_ROOT / f"{safe_session_name(session)}.jsonl"


def append_session(session: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "session": safe_session_name(session),
        "role": role,
        "content": content,
        "meta": meta or {},
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "no_tracking": True,
            "safe_only": True,
        },
    }

    path = session_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def read_session(session: str, limit: int = 12) -> List[Dict[str, Any]]:
    path = session_path(session)
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    events: List[Dict[str, Any]] = []

    for line in lines[-max(1, min(int(limit), 100)) :]:
        try:
            events.append(json.loads(line))
        except Exception:
            events.append({"broken_line": line[:300]})

    return events


def list_sessions() -> Dict[str, Any]:
    sessions = []

    for path in sorted(SESSIONS_ROOT.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            count = len(lines)
            last = json.loads(lines[-1]) if lines else None
        except Exception:
            count = 0
            last = None

        sessions.append(
            {
                "session": path.stem,
                "path": str(path),
                "message_count": count,
                "modified_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(path.stat().st_mtime)),
                "last": last,
            }
        )

    return {
        "ok": True,
        "version": "v2.20.1b-human-chat-truth-guard",
        "session_count": len(sessions),
        "sessions": sessions,
        "root": str(CHAT_ROOT),
    }


def compact_context(session: str, limit: int = 8) -> str:
    events = read_session(session, limit=limit)
    if not events:
        return "Aucune conversation précédente dans cette session."

    lines = []
    for event in events:
        role = event.get("role", "?")
        content = (event.get("content") or "").replace("\n", " ").strip()
        if len(content) > 260:
            content = content[:260] + "..."
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def status() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": "v2.20.1b-human-chat-truth-guard",
        "chat_root": str(CHAT_ROOT),
        "sessions_root": str(SESSIONS_ROOT),
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
            "no_tracking": True,
            "safe_only": True,
            "truth_guard": True,
        },
        "commands": [
            "/help",
            "/status",
            "/maintenance",
            "/human",
            "/journal",
            "/sessions",
            "/brief",
            "/state",
            "/prepare-optimization",
        ],
    }


def build_brief() -> Dict[str, Any]:
    maintenance = None
    human = None
    brain = None
    errors = []

    try:
        from core.project_janitor import maintenance_status

        maintenance = maintenance_status()
    except Exception as exc:
        errors.append({"where": "maintenance", "error": str(exc)})

    try:
        from core.human_loop import status as human_status

        human = human_status()
    except Exception as exc:
        errors.append({"where": "human_loop", "error": str(exc)})

    try:
        from core.pc_model_router import router_status

        brain = router_status()
    except Exception as exc:
        errors.append({"where": "brain", "error": str(exc)})

    ok = not errors and bool((maintenance or {}).get("ok", False))

    summary = (
        "Brief E-ZZIO : système PC propre et prêt. "
        "Maintenance OK, human loop actif, cerveau routeur disponible. "
        "CPU/RAM only, GPU intact, zéro pub."
        if ok
        else "Brief E-ZZIO : système actif, mais certains points demandent vérification."
    )

    return {
        "ok": ok,
        "created_at": now(),
        "version": "v2.20.1b-human-chat-truth-guard",
        "summary": summary,
        "maintenance": maintenance,
        "human": {
            "version": human.get("version"),
            "rhythm": human.get("rhythm"),
        }
        if human
        else None,
        "brain": {
            "version": brain.get("version"),
            "installed_count": len(brain.get("installed_models", [])),
            "latest_guarded_bench": brain.get("latest_guarded_bench"),
        }
        if brain
        else None,
        "errors": errors,
    }


def command_reply(text: str, session: str) -> Optional[Dict[str, Any]]:
    cmd = (text or "").strip().lower()

    if cmd in ("/help", "help"):
        return {
            "reply": (
                "Commandes E-ZZIO PC : /status, /maintenance, /human, /journal, "
                "/sessions, /brief, /state, /prepare-optimization. Sinon, parle normalement."
            ),
            "command": "/help",
        }

    if cmd in ("/state", "state"):
        det = deterministic_human_reply("état rapide système E-ZZIO")
        return {
            "reply": det["reply"] if det else "État rapide indisponible.",
            "command": "/state",
        }

    if cmd in ("/prepare-optimization", "prepare-optimization"):
        det = deterministic_human_reply("prépare la prochaine optimisation PC sans rien casser")
        return {
            "reply": det["reply"] if det else "Préparation optimisation indisponible.",
            "command": "/prepare-optimization",
        }

    if cmd in ("/status", "status"):
        try:
            from core.pc_model_router import router_status

            brain = router_status()
            return {
                "reply": (
                    f"E-ZZIO PC est actif. Cerveau : {brain.get('version')}. "
                    f"Modèles installés : {len(brain.get('installed_models', []))}. "
                    "CPU/RAM only, GPU intact, zéro pub."
                ),
                "command": "/status",
                "data": {
                    "brain_version": brain.get("version"),
                    "installed_count": len(brain.get("installed_models", [])),
                },
            }
        except Exception as exc:
            return {
                "reply": f"Status partiel : cerveau indisponible ({exc}).",
                "command": "/status",
            }

    if cmd in ("/maintenance", "maintenance"):
        try:
            from core.project_janitor import maintenance_status

            maintenance = maintenance_status()
            return {
                "reply": (
                    f"Maintenance : ok={maintenance.get('ok')}, "
                    f"bad_count={maintenance.get('bad_count')}, "
                    f"dust={maintenance.get('dust_candidate_count')}."
                ),
                "command": "/maintenance",
                "data": maintenance,
            }
        except Exception as exc:
            return {
                "reply": f"Maintenance indisponible : {exc}",
                "command": "/maintenance",
            }

    if cmd in ("/human", "human"):
        try:
            from core.human_loop import status as human_status

            human = human_status()
            rhythm = human.get("rhythm") or {}
            return {
                "reply": (f"Human loop actif. Dernier tick : {rhythm.get('last_tick')}. Dernier objectif : {rhythm.get('last_goal')}."),
                "command": "/human",
                "data": {
                    "version": human.get("version"),
                    "rhythm": rhythm,
                },
            }
        except Exception as exc:
            return {
                "reply": f"Human loop indisponible : {exc}",
                "command": "/human",
            }

    if cmd in ("/journal", "journal"):
        try:
            from core.human_loop import journal_tail

            tail = journal_tail(limit=5)
            return {
                "reply": f"Journal humain disponible : {tail.get('count')} événement(s) récents.",
                "command": "/journal",
                "data": tail,
            }
        except Exception as exc:
            return {
                "reply": f"Journal indisponible : {exc}",
                "command": "/journal",
            }

    if cmd in ("/sessions", "sessions"):
        sessions = list_sessions()
        return {
            "reply": f"Sessions mémoire : {sessions.get('session_count')} session(s).",
            "command": "/sessions",
            "data": sessions,
        }

    if cmd in ("/brief", "brief"):
        brief = build_brief()
        return {
            "reply": brief.get("summary"),
            "command": "/brief",
            "data": brief,
        }

    return None


def human_chat(text: str, session: str = "pc", task: str = "auto", speed: str = "auto", predict: int = 260) -> Dict[str, Any]:
    started = time.time()
    session = safe_session_name(session)
    text = text or ""

    append_session(
        session,
        "user",
        text,
        {
            "task": task,
            "speed": speed,
        },
    )

    deterministic = deterministic_human_reply(text)
    if deterministic:
        reply = deterministic["reply"]
        append_session(
            session,
            "assistant",
            reply,
            {
                "command": deterministic.get("command"),
                "deterministic": True,
                "truth_guard": True,
            },
        )
        return {
            "ok": True,
            "created_at": now(),
            "version": "v2.20.1b-human-chat-truth-guard",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "reply": reply,
            "command": deterministic.get("command"),
            "deterministic": True,
            "truth_guard": True,
            "policy": {
                "cpu_ram_only": True,
                "gpu": "untouched",
                "no_ads": True,
            },
        }

    command = command_reply(text, session)
    if command:
        reply = sanitize_human_chat_reply(command["reply"])
        append_session(
            session,
            "assistant",
            reply,
            {
                "command": command.get("command"),
                "deterministic": True,
                "truth_guard": True,
            },
        )
        return {
            "ok": True,
            "created_at": now(),
            "version": "v2.20.1b-human-chat-truth-guard",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "reply": reply,
            "command": command.get("command"),
            "data": command.get("data"),
            "deterministic": True,
            "truth_guard": True,
            "policy": {
                "cpu_ram_only": True,
                "gpu": "untouched",
                "no_ads": True,
            },
        }

    context = compact_context(session, limit=8)

    enriched = f"""
Tu es E-ZZIO dans une session PC locale avec Enrik.

Mémoire courte de cette session :
{context}

Message actuel d'Enrik :
{text}

Réponds en français, de façon utile, humaine, honnête et professionnelle.
Reste local-first, CPU/RAM only, sans publicité, sans tracking, sans sponsor.
Ne prétends pas qu'un connecteur externe est actif s'il n'est pas configuré.
Ne dis jamais que tu vas exécuter une action système réelle sans confirmation explicite.
Tu peux préparer, observer, proposer, planifier et vérifier.
Tu ne dois pas supprimer, fermer, modifier ou nettoyer réellement sans confirmation explicite.
""".strip()

    try:
        from core.pc_model_router import chat_with_route

        routed = chat_with_route(
            text=enriched,
            task=task,
            speed=speed,
            predict=predict,
        )

        reply = sanitize_human_chat_reply(routed.get("reply") or "Je suis là, mais je n'ai pas produit de réponse exploitable.")

        append_session(
            session,
            "assistant",
            reply,
            {
                "route": routed.get("route"),
                "elapsed_ms": routed.get("elapsed_ms"),
                "deterministic": routed.get("deterministic", False),
                "truth_guard": True,
            },
        )

        routed["version"] = "v2.20.1b-human-chat-truth-guard"
        routed["session"] = session
        routed["reply"] = reply
        routed["truth_guard"] = True
        routed["human_chat_elapsed_ms"] = int((time.time() - started) * 1000)
        routed["gateway"] = "/api/chat/human"

        return routed

    except Exception as exc:
        reply = f"Je reste disponible, mais le cerveau routeur a rencontré une erreur : {exc}"
        append_session(
            session,
            "assistant",
            reply,
            {
                "error": str(exc),
                "truth_guard": True,
            },
        )
        return {
            "ok": False,
            "created_at": now(),
            "version": "v2.20.1b-human-chat-truth-guard",
            "session": session,
            "elapsed_ms": int((time.time() - started) * 1000),
            "reply": reply,
            "error": str(exc),
            "truth_guard": True,
        }
