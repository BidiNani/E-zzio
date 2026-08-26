import json
import time
from pathlib import Path


class CapabilityRevocationRegistry:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.consumed_tokens_file = self.storage_dir / "consumed_tokens.json"
        self.revoked_tokens_file = self.storage_dir / "revoked_tokens.jsonl"
        self._consumed = set()
        self._revoked = set()
        self._load_state()

    def _load_state(self):
        """Charge l'état des jetons consommés et de la liste noire de révocation."""
        if self.consumed_tokens_file.exists():
            try:
                data = json.loads(self.consumed_tokens_file.read_text(encoding="utf-8"))
                # On ne garde que les tokens dont le TTL n'est pas biologiquement dépassé
                now = time.time()
                self._consumed = {t_id for t_id, exp in data.items() if exp > now}
            except (json.JSONDecodeError, OSError):
                self._consumed = set()

        if self.revoked_tokens_file.exists():
            try:
                lines = self.revoked_tokens_file.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    if line.strip():
                        entry = json.loads(line)
                        self._revoked.add(entry["token_id"])
            except (json.JSONDecodeError, OSError):
                self._revoked = set()

    def mark_consumed(self, token_id: str, expires_at: float):
        """Marque un jeton comme consommé pour prévenir tout rejeu (Anti-Replay)."""
        self._consumed.add(token_id)
        # Nettoyage et sauvegarde synchrone
        now = time.time()
        active_consumed = {t_id: expires_at for t_id in self._consumed if expires_at > now}
        self.consumed_tokens_file.write_text(json.dumps(active_consumed, indent=2), encoding="utf-8")

    def revoke_token(self, token_id: str, reason: str = "MANUAL_REVOCATION"):
        """Ajoute un jeton à la liste noire (CRL) de manière permanente."""
        self._revoked.add(token_id)
        record = {"timestamp": time.time(), "token_id": token_id, "reason": reason}
        with open(self.revoked_tokens_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def is_usable(self, token_id: str) -> tuple:
        """Vérifie si un jeton n'a pas été déjà consommé (Replay) ou révoqué (CRL)."""
        if token_id in self._revoked:
            return False, "TOKEN_EXPLICITLY_REVOKED"
        if token_id in self._consumed:
            return False, "TOKEN_ALREADY_CONSUMED_REPLAY_ATTACK"
        return True, "TOKEN_NOT_REVOKED"
