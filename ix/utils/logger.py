import logging
import os
import json
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

DEFAULT_SERVICE_NAME = "investment-x"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(service)s | %(name)s:%(lineno)d | %(message)s"
)
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = "~/.investment-x/logs/"
DB_LOGGER_PREFIXES = (
    "ix.",
    "uvicorn",
    "fastapi",
    "apscheduler",
    "py.warnings",
    "sqlalchemy",
)
DB_LOGGER_NAMES = {"backend", "root", "__main__"}
NORMALIZED_LOGGER_NAMES = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
    "apscheduler",
    "py.warnings",
)


class TextFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_LOG_DATE_FORMAT)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        record.service = getattr(record, "service", None) or self.service_name
        return super().format(record)


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", None) or self.service_name,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line_no": record.lineno,
            "path": record.pathname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def _normalize_level(level: int | str) -> int:
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return level


def _normalize_external_loggers() -> None:
    logging.captureWarnings(True)
    for logger_name in NORMALIZED_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True


class DatabaseLogHandler(logging.Handler):
    """Persist selected application logs to the runtime_logs table."""

    def __init__(self, service_name: str):
        super().__init__(level=logging.INFO)
        self.service_name = service_name
        self._guard = threading.local()

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(self._guard, "active", False):
            return

        logger_name = getattr(record, "name", "") or ""
        if logger_name and not (
            logger_name.startswith(DB_LOGGER_PREFIXES) or logger_name in DB_LOGGER_NAMES
        ):
            return

        try:
            from ix.db.conn import conn

            if not conn.is_connected() or conn.engine is None:
                return

            self._guard.active = True
            exc_text = None
            if record.exc_info:
                exc_text = logging.Formatter().formatException(record.exc_info)

            payload = {
                "level": record.levelname,
                "logger_name": logger_name[:255] or "backend",
                "module": (getattr(record, "module", None) or "")[:255] or None,
                "function": (getattr(record, "funcName", None) or "")[:255] or None,
                "message": record.getMessage(),
                "path": getattr(record, "pathname", None),
                "line_no": getattr(record, "lineno", None),
                "service": (getattr(record, "service", None) or self.service_name)[:64],
                "exception": exc_text,
            }

            with conn.engine.begin() as db_conn:
                db_conn.execute(
                    text(
                        """
                        INSERT INTO runtime_logs
                            (level, logger_name, module, function, message, path, line_no, service, exception, created_at)
                        VALUES
                            (:level, :logger_name, :module, :function, :message, :path, :line_no, :service, :exception, NOW())
                        """
                    ),
                    payload,
                )
        except Exception:
            # Logging failures must never break application flow.
            return
        finally:
            self._guard.active = False


def configure_root_logger(
    service_name: str = DEFAULT_SERVICE_NAME,
    *,
    level: int | str = logging.INFO,
    enable_stream: bool = True,
    enable_file: bool = False,
    enable_db: bool = False,
) -> logging.Logger:
    resolved_level = _normalize_level(level)
    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)
    root_logger.propagate = False

    text_formatter = TextFormatter(service_name=service_name)
    json_formatter = JsonFormatter(service_name=service_name)

    if enable_stream:
        stream_handler = next(
            (handler for handler in root_logger.handlers if getattr(handler, "_investment_x_stream", False)),
            None,
        )
        if stream_handler is None:
            stream_handler = logging.StreamHandler()
            stream_handler._investment_x_stream = True
            root_logger.addHandler(stream_handler)
        stream_handler.setLevel(resolved_level)
        stream_handler.setFormatter(text_formatter)

    if enable_file:
        try:
            log_dir = Path(os.path.expanduser(DEFAULT_LOG_DIR))
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir / f"{service_name}_{timestamp}.jsonl"

            file_handler = next(
                (handler for handler in root_logger.handlers if getattr(handler, "_investment_x_file", False)),
                None,
            )
            if file_handler is None:
                file_handler = logging.FileHandler(log_file, delay=True)
                file_handler._investment_x_file = True
                root_logger.addHandler(file_handler)
            file_handler.setLevel(resolved_level)
            file_handler.setFormatter(json_formatter)
        except Exception as exc:
            fallback_logger = logging.getLogger(service_name)
            fallback_logger.warning("Could not initialize file logger: %s", exc)

    if enable_db:
        db_handler = next(
            (handler for handler in root_logger.handlers if getattr(handler, "_investment_x_db", False)),
            None,
        )
        if db_handler is None:
            db_handler = DatabaseLogHandler(service_name=service_name)
            db_handler._investment_x_db = True
            root_logger.addHandler(db_handler)
        db_handler.service_name = service_name
        db_handler.setLevel(resolved_level)

    _normalize_external_loggers()
    service_logger = logging.getLogger(service_name)
    service_logger.setLevel(resolved_level)
    service_logger.propagate = True
    return service_logger


def setup_logging(service_name: str = DEFAULT_SERVICE_NAME) -> logging.Logger:
    """Initialize the shared application logging pipeline."""
    logger = configure_root_logger(
        service_name=service_name,
        level=logging.INFO,
        enable_stream=True,
        enable_file=True,
        enable_db=True,
    )
    return logger
