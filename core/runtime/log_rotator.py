# ==============================================================================
# E-ZZIO — Production Log Rotation & Safe JSON Formatter (Hardened v2.1)
# File: G:\AI\E-zzio\core\runtime\log_rotator.py
# ==============================================================================
import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SafeJsonFormatter(logging.Formatter):
    """Formateur JSON strict protégeant contre l'injection de retours ligne ou guillemets."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_record, ensure_ascii=False)


ROOT_PATH = Path(r"G:\AI\E-zzio")
LOG_DIR = ROOT_PATH / "runtime" / "logs"


def setup_production_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "ezzio_runtime.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler_exists = any(
        isinstance(h, RotatingFileHandler) and Path(getattr(h, "baseFilename", "")) == log_file for h in root_logger.handlers
    )

    if not handler_exists:
        handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        handler.setFormatter(SafeJsonFormatter())
        root_logger.addHandler(handler)
    else:
        handler = next(h for h in root_logger.handlers if isinstance(h, RotatingFileHandler))

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.setLevel(logging.INFO)
        uv_logger.propagate = False
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)

    logging.info("Pipeline de journalisation unifié et sécurisé actif (v2.1).")


if __name__ == "__main__":
    setup_production_logging()
