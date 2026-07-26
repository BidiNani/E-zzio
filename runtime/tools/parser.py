import json
from typing import Optional
from runtime.tools.tool_schema import ToolRequest
from runtime.security.permissions import SecurityPolicy

class ToolParser:
    """Analyse stricte de la sortie du LLM (Exige un JSON brut pur)."""
    @staticmethod
    def parse_intent(llm_output: str) -> Optional[ToolRequest]:
        clean_text = llm_output.strip()
        
        # Exigence stricte : Le texte doit commencer par '{' et finir par '}'
        if not (clean_text.startswith("{") and clean_text.endswith("}")):
            return None

        try:
            data = json.loads(clean_text)
            if isinstance(data, dict) and data.get("type") == "tool_call":
                tool_name = data.get("tool")
                arguments = data.get("arguments", {})

                if not tool_name or tool_name not in SecurityPolicy.PERMISSIONS:
                    return None

                if not isinstance(arguments, dict):
                    return None

                if tool_name == "filesystem.read":
                    if not arguments.get("path"):
                        return None

                if SecurityPolicy.get_level(tool_name) >= SecurityPolicy.LEVEL_SYSTEM:
                    return None

                return ToolRequest(name=tool_name, arguments=arguments, requester="llm")
        except Exception:
            pass

        return None