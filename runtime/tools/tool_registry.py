from typing import Dict, Any, List, Optional
from pathlib import Path
from runtime.tools.tool_schema import ToolRequest, ToolResult
from runtime.tools.executors.filesystem import FileSystemExecutor
from runtime.security.permissions import SecurityPolicy


class ToolRegistry:
    """Registre centralisé et souverain des outils d'E-ZZIO avec contrôle de sécurité strict."""

    _TOOLS_METADATA = {
        "filesystem.read": {
            "name": "filesystem.read",
            "version": "1.2.0",
            "description": "Lecture sécurisée de fichier en mode strictement read-only",
            "capabilities": ["fs:read"],
            "permission_level": SecurityPolicy.LEVEL_READ,
            "input_schema": {"path": "str"},
            "output_schema": {"content": "str"},
            "timeout": 5.0,
            "audit_required": True,
        },
        "filesystem.list": {
            "name": "filesystem.list",
            "version": "1.2.0",
            "description": "Listage sécurisé du contenu d'un répertoire autorisé",
            "capabilities": ["fs:list"],
            "permission_level": SecurityPolicy.LEVEL_READ,
            "input_schema": {"folder_path": "str", "limit": "int"},
            "output_schema": {"items": "list"},
            "timeout": 5.0,
            "audit_required": True,
        },
        "filesystem.observe": {
            "name": "filesystem.observe",
            "version": "1.0.0",
            "description": "Observation structurée et réconciliation différentielle",
            "capabilities": ["fs:observe"],
            "permission_level": SecurityPolicy.LEVEL_READ,
            "input_schema": {"directory_path": "str"},
            "output_schema": {"status": "str", "files": "dict", "diff": "dict"},
            "timeout": 10.0,
            "audit_required": True,
        },
    }

    def __init__(self, project_root=None):
        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]
        self.project_root = Path(project_root).resolve()
        self.fs_executor = FileSystemExecutor(self.project_root)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Retourne la liste des outils officiellement enregistrés."""
        return list(self._TOOLS_METADATA.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupère les métadonnées et le schéma d'un outil enregistré."""
        return self._TOOLS_METADATA.get(name)

    def authorize_tool(self, name: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Vérifie l'autorisation d'exécution d'un outil dans un contexte donné."""
        tool_meta = self.get_tool(name)
        if not tool_meta:
            return False

        # Vérification d'absence de cible protégée / immuable
        if context and "target" in context:
            target = str(context["target"])
            if "core/constitution" in target or "secrets/" in target:
                return False

        # Vérification des capabilities du contexte
        if context and "capabilities" in context:
            allowed_caps = set(context["capabilities"])
            required_caps = set(tool_meta.get("capabilities", []))
            if not required_caps.issubset(allowed_caps):
                return False

        return True

    def dispatch(self, request: ToolRequest) -> ToolResult:
        tool_meta = self.get_tool(request.name)
        if not tool_meta:
            return ToolResult(success=False, output="", error=f"Outil inconnu ou non enregistré : {request.name}")

        level = SecurityPolicy.get_level(request.name)
        if level >= SecurityPolicy.LEVEL_MODIFY:
            return ToolResult(
                success=False,
                output="",
                error=f"Sécurité : L'outil '{request.name}' requiert un niveau de privilège supérieur non validé.",
            )

        if request.name == "filesystem.read":
            path = request.arguments.get("path", "")
            return self.fs_executor.read_file(path)

        if request.name == "filesystem.observe":
            from tools.fs_tools import observe_filesystem
            path = request.arguments.get("directory_path", "")
            res = observe_filesystem(path)
            return ToolResult(success=(res.get("status") == "SUCCESS"), output=str(res), error=res.get("error", ""))

        return ToolResult(success=False, output="", error=f"Exécuteur non implémenté pour : {request.name}")
