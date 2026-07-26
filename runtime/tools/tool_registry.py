from pathlib import Path
from runtime.tools.tool_schema import ToolRequest, ToolResult
from runtime.tools.executors.filesystem import FileSystemExecutor
from runtime.security.permissions import SecurityPolicy

class ToolRegistry:
    """Registre centralisé des outils d'E-zzio avec contrôle de sécurité et d'exécution."""
    def __init__(self, project_root=None):
        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]
        self.project_root = Path(project_root).resolve()
        self.fs_executor = FileSystemExecutor(self.project_root)

    def dispatch(self, request: ToolRequest) -> ToolResult:
        level = SecurityPolicy.get_level(request.name)
        
        # Gestion des niveaux de sécurité
        if level >= SecurityPolicy.LEVEL_MODIFY:
            # Pour l'instant, les actions de modification/système demandent une validation explicite
            return ToolResult(
                success=False, 
                output="", 
                error=f"Sécurité : L'outil '{request.name}' requiert un niveau de privilège supérieur (Modification/Système) non validé."
            )

        # Exécution des outils de niveau Lecture
        if request.name == "filesystem.read":
            path = request.arguments.get("path", "")
            return self.fs_executor.read_file(path)

        return ToolResult(success=False, output="", error=f"Outil inconnu ou non enregistré : {request.name}")