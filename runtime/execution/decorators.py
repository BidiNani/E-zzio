from typing import Type


def executor(cls: Type) -> Type:
    if not hasattr(cls, "TOOL_NAME") or not isinstance(cls.TOOL_NAME, str):
        raise TypeError(f"Executor class '{cls.__name__}' must define a valid string 'TOOL_NAME'.")

    if not hasattr(cls, "execute") or not callable(getattr(cls, "execute")):
        raise TypeError(f"Executor class '{cls.__name__}' must implement a callable 'execute' method.")

    cls.__is_executor__ = True
    cls.__executor_contract__ = {"input": "ExecutionContext", "output": "ToolResult"}
    cls.__executor_metadata__ = {
        "contract_version": "1.0",
        "tool_name": cls.TOOL_NAME,
        "version": getattr(cls, "VERSION", "1.0"),
        "security_level": getattr(cls, "SECURITY_LEVEL", "restricted"),
    }
    return cls
