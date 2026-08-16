import logging

class AuditLogger:
    def __init__(self, name: str = "ezzio.audit"):
        self.logger = logging.getLogger(name)

    def log_event(self, event_type: str, payload: dict) -> None:
        self.logger.info(f"[{event_type}] {payload}")

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
