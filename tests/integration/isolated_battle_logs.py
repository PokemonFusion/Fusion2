"""Keep disposable command checks away from the running game's battle logs."""

import logging
from tempfile import TemporaryDirectory
from unittest.mock import patch


class IsolatedBattleLogs:
    """Redirect only this test process's new battle handler and close it first."""

    def __enter__(self):
        """Leave production logger configuration and unrelated handlers untouched."""
        from utils.battle_logging import setup_daily_battle_log

        self.directory = TemporaryDirectory(prefix="pf2-item-checks-")
        self.logger = logging.getLogger("battle")
        self.previous = list(self.logger.handlers)
        self.patch = patch("pokemon.battle.battleinstance.setup_daily_battle_log",
                           lambda unused: setup_daily_battle_log(self.directory.name))
        self.patch.start()
        return self

    def __exit__(self, *exc):
        """Release only task-created file handles before private log cleanup."""
        self.patch.stop()
        for handler in list(self.logger.handlers):
            if handler not in self.previous:
                self.logger.removeHandler(handler)
                handler.close()
        self.directory.cleanup()
