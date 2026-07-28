from pathlib import Path
import datetime

class FilesystemSensor:
    IGNORED_DIRS = {
        ".git", "__pycache__", "build", "node_modules", ".venv", "models", "cache", "env",
        ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "tmp", "logs"
    }

    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = Path(__file__).resolve().parents[2]
        self.root_dir = Path(root_dir).resolve()

    def scan(self) -> dict:
        total_files = 0
        py_files = 0
        ps1_files = 0
        total_size = 0
        latest_change = 0.0

        if self.root_dir.exists():
            for p in self.root_dir.rglob("*"):
                if any(part in self.IGNORED_DIRS for part in p.parts):
                    continue
                if p.is_file():
                    total_files += 1
                    try:
                        stat = p.stat()
                        total_size += stat.st_size
                        if stat.st_mtime > latest_change:
                            latest_change = stat.st_mtime
                    except Exception:
                        pass

                    if p.suffix == ".py":
                        py_files += 1
                    elif p.suffix == ".ps1":
                        ps1_files += 1

        size_mb = round(total_size / (1024 * 1024), 2)
        last_change_str = datetime.datetime.fromtimestamp(latest_change).strftime("%Y-%m-%d %H:%M:%S") if latest_change > 0 else "N/A"

        return {
            "root": str(self.root_dir),
            "files": total_files,
            "python_files": py_files,
            "powershell_files": ps1_files,
            "size_mb": size_mb,
            "last_change": last_change_str
        }