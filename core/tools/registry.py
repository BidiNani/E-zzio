import logging
from typing import Dict, Optional
from core.tools.base import BaseTool

logger = logging.getLogger("ezzio.tools.registry")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.info(f"[TOOL] Enregistré : {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        return {name: t.description for name, t in self._tools.items()}
