
import logging

from zalo_ai.config import logging_config


def test_setup_logging_creates_log_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(logging_config, "LOG_DIR", tmp_path / "logs")
    logging_config.setup_logging()

    logger = logging.getLogger("test_zalo_ai")
    logger.info("Logging test message")

    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = tmp_path / "logs" / "app.log"

    assert log_file.exists()
    assert "Logging test message" in log_file.read_text(
        encoding="utf-8"
    )