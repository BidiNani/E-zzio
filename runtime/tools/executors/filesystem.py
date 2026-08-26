from pathlib import Path
from runtime.tools.tool_schema import ToolResult


class FileSystemExecutor:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or "G:/AI/E-zzio").resolve()

    def read_file(self, path: str) -> ToolResult:
        if not path:
            return ToolResult(success=False, output="", error="No path provided")
        target = Path(path)
        candidates = [target, self.project_root / target, Path.cwd() / target]
        for c in candidates:
            try:
                if c.exists() and c.is_file():
                    return ToolResult(success=True, output=c.read_text(encoding="utf-8"), error="")
            except Exception as e:
                continue
        return ToolResult(success=False, output="", error=f"File not found: {path}")

    @classmethod
    def execute(cls, context=None, *args, **kwargs):
        p = kwargs.get("path")
        if not p and context and hasattr(context, "arguments"):
            p = context.arguments.get("path")
        if not p and isinstance(context, dict):
            p = context.get("path")
        if not p and args:
            p = args[0]

        if not p:
            return ToolResult(success=False, output="", error="No path provided")

        target = Path(p)
        candidates = [target, Path("G:/AI/E-zzio") / target, Path.cwd() / target]

        for c in candidates:
            try:
                if c.exists() and c.is_file():
                    return ToolResult(success=True, output=c.read_text(encoding="utf-8"), error="")
            except Exception:
                continue

        return ToolResult(success=False, output="", error=f"File not found: {p}")
