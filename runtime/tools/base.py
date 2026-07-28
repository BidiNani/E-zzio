class ToolResult:
    def __init__(self, success=False, output="", error="", metadata=None, **kwargs):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)

class ExternalExecutorBase:
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
