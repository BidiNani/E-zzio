import concurrent.futures
from pathlib import Path
from typing import Tuple, Optional, Callable
from runtime.tools.manifest_loader import ManifestLoader
from runtime.tools.tool_schema import ToolResult

class ExecutionSandbox:
    """Isole et confine l'exécution (Timeout, Roots, Symlinks, Taille, Extensions)."""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()

    def execute(self, tool_name: str, func: Callable, *args, **kwargs) -> ToolResult:
        """Enveloppe l'exécution de tout outil métier dans un thread limité dans le temps."""
        config = ManifestLoader.get_tools().get(tool_name, {})
        timeout = config.get("timeout_sec", 10)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                # Blocage jusqu'au timeout
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                return ToolResult(success=False, output="", error=f"Sandbox Timeout : L'outil '{tool_name}' a dépassé la limite d'exécution de {timeout}s.")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Sandbox Execution Error : {str(e)}")

    def resolve_and_validate_path(self, raw_path: str, tool_name: str) -> Tuple[Optional[Path], Optional[ToolResult]]:
        config = ManifestLoader.get_tools().get(tool_name, {})
        sandbox_rules = config.get("sandbox", {})
        
        target_path = None
        valid_root = False
        roots = sandbox_rules.get("roots", ["."])

        # 1. Validation de la racine (anti Path-Traversal dynamique)
        for r in roots:
            root_path = (self.project_root / r).resolve()
            try:
                temp_path = (self.project_root / raw_path).resolve()
                temp_path.relative_to(root_path)
                valid_root = True
                target_path = temp_path
                break
            except ValueError:
                continue
                
        if not valid_root or not target_path:
            return None, ToolResult(success=False, output="", error="Sandbox : Chemin refusé (Hors des racines autorisées).")

        # 2. Interdiction absolue des liens symboliques
        if target_path.is_symlink():
            return None, ToolResult(success=False, output="", error="Sandbox : Les liens symboliques sont interdits.")

        if not target_path.exists() or not target_path.is_file():
            return None, ToolResult(success=False, output="", error=f"Sandbox : Fichier introuvable.")

        # 3. Validation stricte de l'extension (Protection contre script.txt.exe)
        allowed_exts = sandbox_rules.get("allowed_extensions", [])
        if allowed_exts:
            file_name = target_path.name.lower()
            if not any(file_name.endswith(ext.lower()) for ext in allowed_exts):
                return None, ToolResult(success=False, output="", error=f"Sandbox : Extension interdite pour ce fichier.")

        # 4. Vérification de taille via stat
        max_size = sandbox_rules.get("max_file_size_bytes", 2097152)
        try:
            if target_path.stat().st_size > max_size:
                return None, ToolResult(success=False, output="", error=f"Sandbox : Fichier trop volumineux.")
        except Exception as e:
            return None, ToolResult(success=False, output="", error=f"Sandbox Stat Error : {str(e)}")

        return target_path, None