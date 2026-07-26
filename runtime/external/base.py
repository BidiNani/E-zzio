from abc import ABC, abstractmethod
from typing import Optional
from runtime.contracts.execution_context import ExecutionContext
from runtime.tools.tool_schema import ToolResult

class ExternalExecutorBase(ABC):
    """Contrat strict pour tout outil interagissant avec l'OS via des processus isolés."""
    TOOL_NAME = ""

    @abstractmethod
    def spawn(self, context: ExecutionContext, project_root: str, **kwargs):
        """Instancie le processus (subprocess.Popen) de manière non bloquante."""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Vérifie si le processus est toujours en cours d'exécution."""
        pass

    @abstractmethod
    def terminate(self, graceful_timeout: float = 2.0):
        """Met en œuvre la stratégie d'arrêt (SIGTERM -> délai -> SIGKILL)."""
        pass

    @abstractmethod
    def collect_output(self) -> Optional[ToolResult]:
        """Collecte stdout/stderr, gère le code de retour et forge le résultat."""
        pass