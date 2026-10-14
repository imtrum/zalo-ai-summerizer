
import logging
import os
from pathlib import Path


def setup_logging() -> None:
    """Configure console and file logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                log_dir / "app.log",
                encoding="utf-8",
            ),
        ],
        force=True,
    )