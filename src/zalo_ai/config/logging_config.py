
import logging
import os

from zalo_ai.paths import LOG_DIR


def setup_logging() -> None:
    """Configure console and file logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                LOG_DIR / "app.log",
                encoding="utf-8",
            ),
        ],
        force=True,
    )