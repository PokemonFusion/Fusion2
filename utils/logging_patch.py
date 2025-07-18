from __future__ import annotations

"""Monkey patches for Evennia's logging utilities."""

# Imports are done lazily within patch functions to avoid requiring Django
# settings during module import.


def patch_open_log_file() -> None:
    """Patch evennia.utils.logger._open_log_file to reopen closed handles."""

    from evennia.utils import logger as evennia_logger

    original_open = evennia_logger._open_log_file

    def _open_log_file(filename: str):
        handle = evennia_logger._LOG_FILE_HANDLES.get(filename)
        if handle is not None:
            if getattr(handle, "closed", False):
                evennia_logger._LOG_FILE_HANDLES.pop(filename, None)
                evennia_logger._LOG_FILE_HANDLE_COUNTS.pop(filename, None)
                handle = None
        if handle is not None:
            evennia_logger._LOG_FILE_HANDLE_COUNTS[filename] += 1
            if (
                evennia_logger._LOG_FILE_HANDLE_COUNTS[filename]
                > evennia_logger._LOG_FILE_HANDLE_RESET
            ):
                handle.close()
                evennia_logger._LOG_FILE_HANDLES.pop(filename, None)
                evennia_logger._LOG_FILE_HANDLE_COUNTS.pop(filename, None)
                handle = None
            else:
                return handle
        handle = original_open(filename)
        return handle

    evennia_logger._open_log_file = _open_log_file


def patch_file_observer() -> None:
    """Patch Twisted FileLogObserver to reopen closed files before writing."""

    from twisted.logger._file import FileLogObserver

    original_call = FileLogObserver.__call__

    def _call(self: FileLogObserver, event):
        if getattr(self._outFile, "closed", False):
            reopen = getattr(self._outFile, "reopen", None)
            if callable(reopen):
                try:
                    reopen()
                except Exception:
                    pass
        return original_call(self, event)

    FileLogObserver.__call__ = _call

