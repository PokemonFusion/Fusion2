"""Real file-observer regressions for rotation failure and startup installation."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from evennia.utils import logger
from twisted.logger import LogLevel, LogPublisher

from utils.server_logging import RotationSafeWeeklyLogFile, install_rotation_safe_logging


def test_failed_rotation_reopens_before_recursive_observer_warning(tmp_path):
    """An OS rename error must not disable the observer or lose either message."""
    logfile = RotationSafeWeeklyLogFile("server.log", str(tmp_path), max_size=1)
    publisher = LogPublisher(logger.GetServerLogObserver()(logfile))
    warnings = []

    def warning(message):
        """Send the warning through the same observer that failed to rotate."""
        warnings.append(message)
        publisher({"log_format": message, "log_level": LogLevel.warn})

    try:
        logfile.write("before\n")
        with patch("twisted.python.logfile.os.rename", side_effect=PermissionError("locked")) as rename, patch.object(logger, "log_warn", warning):
            publisher({"log_format": "after reload", "log_level": LogLevel.info})
            publisher({"log_format": "next message", "log_level": LogLevel.info})
        assert not logfile._file.closed
        assert rename.call_count == 1
        assert len(warnings) == 1
        text = (tmp_path / "server.log").read_text(encoding="utf-8")
        assert all(message in text for message in ("before", "rotation deferred", "after reload", "next message"))
        assert "I/O operation on closed file" not in text
    finally:
        logfile.close()


def test_rotation_recovers_after_lock_released_without_losing_archive(tmp_path):
    """A deferred rotation retries after the backoff and preserves the old log."""
    clock = [100.0]
    with patch("utils.server_logging.monotonic", side_effect=lambda: clock[0]):
        logfile = RotationSafeWeeklyLogFile("server.log", str(tmp_path), max_size=1)
        try:
            logfile.write("before\n")
            with patch("twisted.python.logfile.os.rename", side_effect=PermissionError("locked")), patch.object(logger, "log_warn"):
                logfile.write("during lock\n")
            clock[0] += logfile.rotation_retry_seconds + 1
            logfile.write("after lock\n")
            archives = list(tmp_path.glob("server.log.*"))
            assert len(archives) == 1
            assert archives[0].read_text() == "before\nduring lock\n"
            assert (tmp_path / "server.log").read_text() == "after lock\n"
        finally:
            logfile.close()


def test_logging_installation_is_idempotent(monkeypatch):
    """Repeated hook imports cannot stack adapters or alter rotation settings."""
    monkeypatch.setattr(logger, "WeeklyLogFile", RotationSafeWeeklyLogFile.__bases__[0])
    install_rotation_safe_logging()
    first = logger.WeeklyLogFile
    install_rotation_safe_logging()
    assert logger.WeeklyLogFile is first is RotationSafeWeeklyLogFile


def test_startstop_module_installs_before_evennia_creates_observer():
    """Exercise the actual hook import in a clean process with no server startup."""
    code = (
        "import server.conf.at_server_startstop; "
        "from evennia.utils import logger; "
        "assert logger.WeeklyLogFile._pf2_rotation_safe"
    )
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parents[2],
                            env=os.environ.copy(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
