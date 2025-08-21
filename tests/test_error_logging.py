import importlib
import logging
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_setup_daily_error_log(tmp_path):
    log_dir = tmp_path / "logs"
    mod = importlib.import_module("utils.error_logging")
    mod.setup_daily_error_log(log_dir)

    root = logging.getLogger("errors")
    log_path = log_dir / "errors.log"
    handlers = [
        h
        for h in root.handlers
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
            root.removeHandler(h)
