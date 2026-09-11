"""
E-ZZIO V7.50.2 — Discord Permission Guard (Diagnostic Mode)
Affiche explicitement les ID reçus dans la console pour un diagnostic sans faille.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
AUDIT_DIR = ROOT_DIR / "runtime" / "audit" / "discord"
POLICY_FILE = ROOT_DIR / "runtime" / "config" / "security" / "discord_policy.json"


class DiscordPermissionGuard:
    def __init__(self):
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_policy(self) -> dict:
        if POLICY_FILE.exists():
            try:
                return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                import logging
                logging.getLogger("ezzio.discord.guard").warning(f"[SECURITY] Échec lecture policy {POLICY_FILE}: {e}")
        return {
            "allowed_guilds": ["1517985912951275590"],
            "allowed_users": {"186035306418405376": "MASTER_ADMIN"},
            "allow_direct_messages": True,
            "dm_owner_only": True,
        }

    def _audit_log(self, filename: str, data: dict):
        log_path = AUDIT_DIR / filename
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def evaluate_access_by_id(self, user_id: str, username: str = None) -> dict:
        policy = self._load_policy()
        allowed_users = policy.get("allowed_users", {})

        print(f"[DIAGNOSTIC] Vérification User ID -> Reçu: '{user_id}' | Autorisés: {list(allowed_users.keys())}")

        if user_id in allowed_users:
            role = allowed_users[user_id]
            return {"granted": True, "role": role, "reason": "USER_ID_WHITELISTED"}

        return {"granted": False, "role": "UNAUTHORIZED", "reason": "USER_ID_NOT_RECOGNIZED"}

    def evaluate_guild_access(self, guild_id: str | None, user_id: str, username: str = None, is_dm: bool = False) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        policy = self._load_policy()

        print(f"[DIAGNOSTIC] Évaluation accès -> DM: {is_dm} | Guild ID: {guild_id} | User ID: {user_id} ({username})")

        if is_dm:
            if not policy.get("allow_direct_messages", True):
                return {"granted": False, "reason": "DM_DISABLED"}

            if policy.get("dm_owner_only", True):
                allowed_users = policy.get("allowed_users", {})
                owner_id = next(iter(allowed_users.keys()), os.getenv("DISCORD_OWNER_ID", ""))
                if user_id not in allowed_users:
                    print(f"[DISCORD-SECURITY] DM rejeté : ID auteur '{user_id}' != DISCORD_OWNER_ID ({owner_id}).")
                    self._audit_log(
                        "access_denied.jsonl",
                        {"timestamp": timestamp, "user_id": user_id, "username": username, "reason": "DM_UNAUTHORIZED_USER"},
                    )
                    return {"granted": False, "reason": "DM_UNAUTHORIZED_USER"}

            print(f"[OK] ACCÈS DM ACCORDÉ pour {user_id}")
            self._audit_log(
                "access_granted.jsonl",
                {"timestamp": timestamp, "user_id": user_id, "username": username, "context": "DM", "status": "GRANTED"},
            )
            return {"granted": True, "role": "MASTER_ADMIN", "reason": "DM_OWNER_VALIDATED"}

        if guild_id is None:
            return {"granted": False, "reason": "NO_GUILD_CONTEXT"}

        allowed_guilds = policy.get("allowed_guilds", [])
        if guild_id not in allowed_guilds:
            print(f"[!] REFUS GUILD : Le serveur '{guild_id}' n'est pas autorisé.")
            self._audit_log(
                "access_denied.jsonl", {"timestamp": timestamp, "guild_id": guild_id, "user_id": user_id, "reason": "GUILD_NOT_AUTHORIZED"}
            )
            return {"granted": False, "reason": "GUILD_NOT_AUTHORIZED"}

        user_check = self.evaluate_access_by_id(user_id, username)
        if not user_check["granted"]:
            self._audit_log(
                "access_denied.jsonl",
                {
                    "timestamp": timestamp,
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "username": username,
                    "reason": "USER_NOT_AUTHORIZED_IN_GUILD",
                },
            )
            return user_check

        self._audit_log(
            "access_granted.jsonl",
            {"timestamp": timestamp, "guild_id": guild_id, "user_id": user_id, "username": username, "status": "GRANTED"},
        )
        return user_check


permission_guard = DiscordPermissionGuard()
