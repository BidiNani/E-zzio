class SessionContext:
    def __init__(self):
        self.user = "BidiNani"
        self.active_project = "E-zzio"
        self.version = "4.2.2"
        self.history = []

    def record(self, cmd: str):
        self.history.append(cmd)
