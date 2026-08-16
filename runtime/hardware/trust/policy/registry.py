import json
from pathlib import Path

class TrustPolicyRegistry:
    def __init__(self, policy_file: Path):
        self.policy_file = policy_file
        self._load_policy()

    def _load_policy(self):
        if not self.policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_file}")
        try:
            self.data = json.loads(self.policy_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Invalid policy structure: {str(e)}")

    def get_profile(self, profile_name: str) -> dict:
        profiles = self.data.get("profiles", {})
        if profile_name not in profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        return profiles[profile_name]

    def get_version(self) -> str:
        return self.data.get("version", "1.0")
