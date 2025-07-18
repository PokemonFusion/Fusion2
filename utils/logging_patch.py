from __future__ import annotations

"""Monkey patches for Evennia's logging utilities."""

from evennia.utils import logger as evennia_logger


def patch_open_log_file() -> None:
    """Patch evennia.utils.logger._open_log_file to reopen closed handles."""

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

