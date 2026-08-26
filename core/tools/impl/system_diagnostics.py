import psutil
from typing import Any, Dict
from core.tools.base import BaseTool


class SystemDiagnostics(BaseTool):
    def __init__(self):
        super().__init__(name="get_system_metrics", description="Retourne l'utilisation CPU, RAM et disque du système hôte.")

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
