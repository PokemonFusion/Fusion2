# Server log rotation recovery

Evennia's WeeklyLogFile uses Twisted's DailyLogFile rotation. Rotation closes
the active file before renaming it. If Windows refuses the rename because
another writer has the file open, Evennia's exception handler attempts to log
through the same closed file. That produces recursive file-observer errors
and can prevent subsequent server messages from being recorded.

`utils.server_logging.RotationSafeWeeklyLogFile` calls the underlying rotation
directly. On an OS failure it reopens the active log first, defers the next
rotation attempt for 60 seconds, then records a warning through the working
observer. Messages continue to be recorded while rotation is deferred. Rotation
is retried after the backoff and preserves the archive when the lock is released.
Permanent directory or file-permission problems still require operational repair.

The existing `server.conf.at_server_startstop` hook installs this project
adapter at module import, before Evennia constructs its server file observer.
Installation is idempotent and keeps the configured weekly/size thresholds.
The virtualenv and Evennia/Twisted source files are unchanged.

Regression tests exercise a real file observer, a locked rename, its warning
through that same observer, deferred writes, eventual successful rotation and
the actual hook import. Live acceptance requires a second reload after initial
activation: errors emitted by the old process during the first transition cannot
be repaired retroactively. Check that the new server log continues to receive
startup and battle messages and the second reload adds no closed-file errors.

Upstream references: [Evennia logging](https://www.evennia.com/docs/latest/api/evennia.utils.logger.html)
and [Twisted DailyLogFile](https://docs.twisted.org/en/latest/api/twisted.python.logfile.DailyLogFile.html).
