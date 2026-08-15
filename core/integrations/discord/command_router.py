"""
E-ZZIO V7.44 — Discord Command Router
Intercepte les messages Discord, vérifie les droits, et achemine l'intention vers l'Agent Core.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.integrations.discord.permission_guard import permission_guard

# Fallback pour le Task Engine s'il n'est pas chargé
try:
    from core.agent.task_engine import task_engine
except ImportError:
    task_engine = None

class DiscordCommandRouter:
    def __init__(self, prefix: str = "!bidi"):
        self.prefix = prefix

    def process_message(self, username: str, message_content: str) -> dict:
        # 1. Filtrage du préfixe
        if not message_content.startswith(self.prefix):
            return {"status": "IGNORED", "reason": "NOT_A_COMMAND"}

        # 2. Validation des permissions
        auth_check = permission_guard.evaluate_access(username)
        if not auth_check["granted"]:
            return {
                "status": "REJECTED",
                "reason": auth_check["reason"],
                "reply_to_user": "❌ Accès refusé : Identité non reconnue par le Guardian."
            }

        # 3. Extraction de l'intention
        raw_intent = message_content[len(self.prefix):].strip()
        command_type = raw_intent.split(" ")[0].upper() if raw_intent else "UNKNOWN"

        # 4. Routage vers l'Agent Layer (V7.40)
        execution_plan = None
        if task_engine:
            execution_plan = task_engine.create_execution_plan(raw_intent)
        else:
            execution_plan = {"status": "MOCKED_PLAN", "tasks": [f"PROCESS_{command_type}"]}

        return {
            "status": "ACCEPTED",
            "command_type": command_type,
            "intent_extracted": raw_intent,
            "execution_plan": execution_plan,
            "reply_to_user": f"🔄 Intention comprise ({command_type}). Initialisation du plan..."
        }

command_router = DiscordCommandRouter()
