from datetime import datetime
from runtime.sensors.system_sensor import SystemSensor
from runtime.sensors.filesystem_sensor import FilesystemSensor
from runtime.sensors.git_sensor import GitSensor


class SensorHealth:
    """Surveille l'intégrité et la disponibilité des capteurs d'E-zzio."""

    def __init__(self, project_root="."):
        self.system = SystemSensor()
        self.fs = FilesystemSensor(project_root)
        self.git = GitSensor(project_root)

    def check(self) -> dict:
        sys_status = "ok"
        fs_status = "ok"
        git_status = "ok"

        try:
            self.system.scan()
        except Exception:
            sys_status = "error"

        try:
            self.fs.scan()
        except Exception:
            fs_status = "error"

        try:
            self.git.scan()
        except Exception:
            git_status = "error"

        return {
            "system_sensor": sys_status,
            "filesystem_sensor": fs_status,
            "git_sensor": git_status,
            "last_check": datetime.now().isoformat(),
        }
