class ToolResult:
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

class ExternalExecutorBase:
    pass
