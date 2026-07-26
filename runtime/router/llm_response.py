class LLMResponse:
    def __init__(self, text: str = "", model: str = "", provider: str = "", latency: float = 0.0, success: bool = False):
        self.text = text
        self.model = model
        self.provider = provider
        self.latency = latency
        self.success = success

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "latency": self.latency,
            "success": self.success
        }

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<LLMResponse [{self.provider}/{self.model}] {status} ({self.latency:.2f}s)>"