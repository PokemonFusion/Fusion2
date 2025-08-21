import importlib
import logging
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_setup_daily_battle_log(tmp_path):
    log_dir = tmp_path / "logs"
    mod = importlib.import_module("utils.battle_logging")
    logger = mod.setup_daily_battle_log(log_dir)

    log_path = log_dir / "battle.log"
    handlers = [
        h
        for h in logger.handlers
        if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        and Path(h.baseFilename) == log_path
    ]
    try:
        assert handlers
        handler = handlers[0]
        assert handler.backupCount == 14
        assert handler.when == "MIDNIGHT"
    finally:
        for h in handlers:
            logger.removeHandler(h)
