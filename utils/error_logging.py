"""Utility for configuring daily error logging."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_daily_error_log(log_dir: str | Path) -> None:
    """Attach a daily rotating error log handler to the root logger.

    Parameters
    ----------
    log_dir : str or Path
        Directory where ``errors.log`` should be created. The directory is
        created if it does not already exist.
    """
    path = Path(log_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    log_file = path / "errors.log"

    logger = logging.getLogger("errors")
    for handler in logger.handlers:
        if isinstance(handler, TimedRotatingFileHandler) and Path(handler.baseFilename) == log_file:
            return logger # handler already configured

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logging.getLogger().addHandler(handler)
    logger.setLevel(logging.ERROR)
    return logger
