from runtime.memory.replay import MemoryReplay
from runtime.skills.registry import SkillRegistry
from pathlib import Path
import json


class CommandHandler:
    def __init__(self):
        self.registry = SkillRegistry()

    def handle(self, raw_input: str) -> str:
        parts = raw_input.strip().split(maxsplit=1)
        if not parts:
            return ""

        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "exit":
            return "EXIT"

        elif cmd == "status":
            skills = self.registry.list_skills()
            return f"[STATUS] E-zzio Core v4.2.2 | Skills actifs : {len(skills)} -> {skills}"

        elif cmd == "skills" and arg == "list":
            skills = self.registry.list_skills()
            return f"[SKILLS] Disponibles : {', '.join(skills)}"

        elif cmd == "analyze":
            if not arg:
                return "[ERROR] Usage: analyze <chemin_fichier_python>"
            res = self.registry.execute("python_analyzer", {"path": arg})
            return json.dumps(res, indent=2, ensure_ascii=False)

        elif cmd == "search":
            if not arg:
                return "[ERROR] Usage: search <terme>"
            res = self.registry.execute("filesystem_search", {"query": arg, "path": "."})
            return json.dumps(res, indent=2, ensure_ascii=False)

        elif cmd == "memory" or cmd == "history":
            replay = MemoryReplay()
            summary = replay.summarize()
            recent = replay.get_recent_skills(3)
            res = f"[MEMORY SUMMARY] Total événements : {summary['total_events']} | Skills exécutés : {summary['total_skills_executed']} | Dernier skill : {summary['last_skill']}\n"
            res += "[DERNIERS ÉPISODES] :\n"
            for ep in recent:
                p = ep.get("payload", {})
                res += f"  - Skill: {p.get('skill')} | Args: {p.get('arguments')}\n"
            return res.strip()

        elif cmd == "ledger":
            ledger_path = Path("runtime/audit/tool_calls.jsonl")
            if not ledger_path.exists():
                return "[INFO] Aucun journal tool_calls.jsonl trouvé."
            lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                return "[INFO] Journal vide."
            return f"[LEDGER] Dernière entrée :\n{lines[-1]}"

        else:
            return f"[ERROR] Commande inconnue : '{cmd}'. Tape 'status' ou 'skills list'."
