class EzzioBrain:
    def __init__(self):
        self.state = "READY"

    def process(self, inputs: dict) -> dict:
        return {"status": "ok"}
