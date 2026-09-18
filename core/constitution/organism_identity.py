"""
E-ZZIO Core — Organism Identity & Existence Counter (V8.10)
Calcule l'âge opérationnel de l'organisme à partir de sa naissance physique sur NTFS.
"""

import json
from datetime import UTC, datetime
from pathlib import Path


class OrganismIdentity:
    def __init__(self, root_dir: Path = Path(r"G:\AI\E-zzio")):
        self.root_dir = root_dir
        self.genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        self._load_birth_data()

    def _load_birth_data(self):
        self.birth_str = "2026-06-09T18:19:57"
        if self.genome_path.exists():
            try:
                data = json.loads(self.genome_path.read_text(encoding="utf-8"))
                if "physical_birth" in data:
                    self.birth_str = data["physical_birth"].get("timestamp", self.birth_str)
            except Exception:
                pass
        # Parse en UTC
        self.birth_dt = datetime.fromisoformat(self.birth_str).replace(tzinfo=UTC)

    def get_existence_duration(self) -> dict:
        now = datetime.now(UTC)
        diff = now - self.birth_dt

        days = diff.days
        seconds = diff.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        milestones = {"24h": days >= 1, "7_days": days >= 7, "30_days": days >= 30, "100_days": days >= 100, "1_year": days >= 365}

        return {
            "birth_timestamp_utc": self.birth_str,
            "current_timestamp_utc": now.isoformat(),
            "total_days_alive": days,
            "detailed_age": {"days": days, "hours": hours, "minutes": minutes},
            "milestones": milestones,
        }


if __name__ == "__main__":
    ident = OrganismIdentity()
    print(json.dumps(ident.get_existence_duration(), indent=2))
