"""Keep Evennia's server log usable when Windows blocks log rotation."""

from time import monotonic

from evennia.utils import logger
from twisted.python.logfile import DailyLogFile


class RotationSafeWeeklyLogFile(logger.WeeklyLogFile):
    """Reopen after failed rename instead of logging through a closed handle."""

    _pf2_rotation_safe = True
    rotation_retry_seconds = 60

    def __init__(self, *args, **kwargs):
        """Retain Evennia's rotation settings and begin without a retry delay."""
        self._rotation_retry_at = 0.0
        super().__init__(*args, **kwargs)

    def shouldRotate(self):
        """Back off repeated rename attempts while another process holds the file."""
        return monotonic() >= self._rotation_retry_at and super().shouldRotate()

    def rotate(self):
        """Preserve the active log and retry rotation later after an OS failure."""
        try:
            # WeeklyLogFile.rotate logs the exception before reopening the file,
            # recursively sending that error to its already closed observer.
            DailyLogFile.rotate(self)
        except OSError as error:
            self._openFile()
            self._rotation_retry_at = monotonic() + self.rotation_retry_seconds
            logger.log_warn(f"Server log rotation deferred; continuing in {self.path}: {error}")


def install_rotation_safe_logging():
    """Select the project adapter before Evennia creates its server observer."""
    if not getattr(logger.WeeklyLogFile, "_pf2_rotation_safe", False):
        logger.WeeklyLogFile = RotationSafeWeeklyLogFile
