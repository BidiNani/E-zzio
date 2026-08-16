class ExecutionTrace:
    def __init__(self, trace_id: str = "default-trace"):
        self.trace_id = trace_id
        self.spans = []

    def add_span(self, name: str, data: dict = None) -> None:
        self.spans.append({"name": name, "data": data or {}})
