import logging
import os
import json
from datetime import datetime
from pathlib import Path


def setup_antigravity_logging(service_name: str = "core"):
    """
    Initializes the mandatory Antigravity logging sink.
    Target: ~/.gemini/antigravity/logs/
    """
    # 1. Define Protocol Path
    log_dir = Path(os.path.expanduser("~/.gemini/antigravity/logs/"))
    log_dir.mkdir(parents=True, exist_ok=True)

    # 2. Define Naming Convention
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{service_name}_{timestamp}.jsonl"

    # 3. Configure Structured JSON Logger
    logger = logging.getLogger()  # Use root logger to capture everything
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if re-initialized
    if logger.hasHandlers():
        return logger

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "service": service_name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "path": record.pathname,
            }
            return json.dumps(log_record)

    # File Handler (Persistent)
    try:
        file_handler = logging.FileHandler(log_file, delay=True)
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not initialize file logger: {e}")

    # Stream Handler (Visual/Rich capability could be added here)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)

    return logger
