import subprocess
from pathlib import Path

class GitSensor:
    """Capteur de perception de l'état du dépôt Git."""
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir).resolve()

    def scan(self) -> dict:
        branch = "unknown"
        status = "unknown"
        last_commit = "unknown"
        modified_files = 0

        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.root_dir, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                branch = res.stdout.strip()

            res = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=self.root_dir, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                last_commit = res.stdout.strip()

            res = subprocess.run(["git", "status", "--porcelain"], cwd=self.root_dir, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                lines = [l for l in res.stdout.strip().split("\n") if l.strip()]
                modified_files = len(lines)
                status = "clean" if modified_files == 0 else "dirty"
        except Exception:
            status = "no_git_or_error"

        return {
            "branch": branch,
            "status": status,
            "last_commit": last_commit,
            "modified_files": modified_files
        }