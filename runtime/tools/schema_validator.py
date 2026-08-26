from typing import Any, Optional
from runtime.tools.manifest_loader import ManifestLoader


class SchemaValidator:
    """Valide dynamiquement les arguments via le ManifestLoader."""

    TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool, "dict": dict, "list": list}

    @classmethod
    def validate(cls, tool_name: str, arguments: Any) -> tuple[bool, Optional[str]]:
        if not isinstance(arguments, dict):
            return False, f"Arguments invalides : Format dictionnaire attendu (reçu: {type(arguments).__name__})."

        tools = ManifestLoader.get_tools()
        config = tools.get(tool_name)

        # DENY BY DEFAULT
        if not config or "schema" not in config:
            return False, f"Fail-Secure : Aucun schéma validé pour l'outil '{tool_name}'."

        schema = config.get("schema")
        schema_types = schema.get("types", {})

        for req in schema.get("required_args", []):
            if req not in arguments:
                return False, f"Argument requis manquant : '{req}' pour l'outil '{tool_name}'."

            val = arguments.get(req)
            type_str = schema_types.get(req)
            expected_type = cls.TYPE_MAP.get(type_str) if type_str else None

            if expected_type and not isinstance(val, expected_type):
                return False, f"Type invalide pour '{req}' : Attendu '{type_str}', reçu '{type(val).__name__}'."

            if expected_type is str and not val.strip():
                return False, f"L'argument '{req}' ne peut pas être une chaîne vide."

        return True, None
