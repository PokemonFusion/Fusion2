from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_daily_battle_log(log_dir: str | Path) -> logging.Logger:
    """Attach a rotating battle log handler and return the logger."""
    path = Path(log_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    log_file = path / "battle.log"

    logger = logging.getLogger("battle")
    for handler in logger.handlers:
        if isinstance(handler, TimedRotatingFileHandler) and Path(handler.baseFilename) == log_file:
            return logger

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
