"""E-ZZIO — observabilité Discord tamponnée (threads + throttle 1 Hz)."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("ezzio.discord.agentview")

EDIT_MIN_INTERVAL = 1.0

STATUS_ICON = {"PENDING": "⏳", "RUNNING": "🟡", "BLOCKED": "⛔",
               "SUCCESS": "🟢", "FAILED": "🔴"}
AGENT_ICON = {"orchestrateur": "🤖", "architecte": "🔍", "coder": "⚙️",
              "quality": "🛡", "default": "🔹"}


def render_ascii_tree(root_label: str, children: list[dict[str, Any]]) -> str:
    """Arbre monospace : agents + outils + statuts + latences."""
    lines = [root_label]
    for i, ch in enumerate(children):
        last = i == len(children) - 1
        pre = "└─ " if last else "├─ "
        sub = "    " if last else "│   "
        icon = AGENT_ICON.get(str(ch.get("agent_id", "")).lower().split("_")[0]
                              if "_" in str(ch.get("agent_id", "")) else "default",
                              "🔹")
        if ch.get("kind") == "tool":
            icon = "🛠"
        lat = f" ({ch['duration_ms']:.0f}ms)" if ch.get("duration_ms") is not None else ""
        if ch.get("status") == "RUNNING" and ch.get("kind") != "tool":
            lat = " [RUNNING...]"
        lines.append(f"{pre}{icon} {ch.get('label', ch.get('agent_id', '?'))} "
                     f"[{ch.get('status', '?')}]" + lat)
        for tool in ch.get("tools", [])[:4]:
            tlat = f" ({tool['duration_ms']:.0f}ms)" if tool.get("duration_ms") is not None else ""
            lines.append(f"{sub}└─ 🛠 Tool: {tool.get('name', '?')}{tlat}")
    return "```\n" + "\n".join(lines) + "\n```"


class AgentViewTracker:
    """Tamponne les événements tracer → message.edit() ≤ 1 Hz (anti-429)."""

    def __init__(self, send, edit):
        self._send = send
        self._edit = edit
        self._nodes: dict[str, dict[str, Any]] = {}
        self._root = "🤖 Orchestrateur"
        self._last_edit = 0.0
        self._dirty = False
        self._msg = None
        self.edits_sent = 0

    def ingest(self, event) -> None:
        key = event.agent_id + (f":{event.tool_name}" if event.tool_name else "")
        node = self._nodes.get(key, {"agent_id": event.agent_id, "tools": []})
        node["status"] = event.status
        if event.duration_ms is not None:
            node["duration_ms"] = event.duration_ms
        if event.event_type == "TOOL_RESULT" and event.tool_name:
            node["tools"] = [t for t in node.get("tools", [])
                             if t.get("name") != event.tool_name]
            node["tools"].append({"name": event.tool_name,
                                  "duration_ms": event.duration_ms})
        elif event.event_type == "TOOL_CALL":
            node["label"] = event.agent_id
        self._nodes[key] = node
        self._dirty = True

    def render(self) -> str:
        agents: dict[str, dict[str, Any]] = {}
        for key, node in self._nodes.items():
            if ":" in key:
                base = key.split(":")[0]
                parent = agents.setdefault(base, {"agent_id": base, "status": "?",
                                                  "tools": []})
                for t in node.get("tools", []):
                    if t not in parent["tools"]:
                        parent["tools"].append(t)
                if node.get("status") not in (None, "?"):
                    parent["status"] = node["status"]
            else:
                agents[key] = node
        return render_ascii_tree(self._root, list(agents.values()))

    async def maybe_flush(self, force: bool = False) -> None:
        if not self._dirty and not force:
            return
        now = time.monotonic()
        if not force and now - self._last_edit < EDIT_MIN_INTERVAL:
            return
        text = self.render()
        try:
            if self._msg is None:
                self._msg = await self._send(text)
            else:
                await self._edit(self._msg, text)
            self.edits_sent += 1
            self._last_edit = now
            self._dirty = False
        except Exception as exc:
            logger.warning("[AGENTVIEW] edit impossible : %s", exc)

    async def run(self, queue: asyncio.Queue, stop_after_idle: float = 300.0) -> None:
        """Boucle de consommation : termine après inactivité (jamais de 429)."""
        idle_since = time.monotonic()
        while True:
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=1.0)
                self.ingest(ev)
                idle_since = time.monotonic()
            except TimeoutError:
                if self._dirty:
                    await self.maybe_flush(force=False)
                if time.monotonic() - idle_since > stop_after_idle:
                    await self.maybe_flush(force=True)
                    return
                continue
            await self.maybe_flush()


async def open_trace_thread(channel, short_id: str, tracker: AgentViewTracker) -> None:
    """Fil de suivi `trace-<id>` + message d'amorçage."""
    try:
        thread = await channel.create_thread(
            name=f"trace-{short_id}", auto_archive_duration=60)
    except Exception as exc:
        logger.warning("[AGENTVIEW] thread impossible : %s", exc)
        return
    try:
        tracker._msg = await thread.send(render_ascii_tree(
            "🤖 Orchestrateur", [{"agent_id": "init", "status": "RUNNING"}]))
    except Exception as exc:
        logger.warning("[AGENTVIEW] amorçage impossible : %s", exc)
