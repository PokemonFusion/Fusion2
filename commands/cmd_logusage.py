from __future__ import annotations

from evennia import Command
from pathlib import Path
import json

from utils.usage_logging import setup_daily_usage_log

LOG_DIR = Path(__file__).resolve().parents[2] / "server" / "logs"


class CmdLogUsage(Command):
    """Log move and ability usage for testing purposes.

    Usage:
      @logusage <move>[=<ability>]
    """

    key = "@logusage"
    locks = "cmd:all()"
    help_category = "Admin"

    def parse(self):
        args = self.args.strip()
        if "=" in args:
            self.move, self.ability = [p.strip() for p in args.split("=", 1)]
        else:
            self.move = args
            self.ability = ""

    def func(self):
        if not self.move:
            self.caller.msg("Usage: @logusage <move>[=<ability>]")
            return

        logger = setup_daily_usage_log(LOG_DIR)
        msg = f"MOVE={self.move}"
        if self.ability:
            msg += f" ABILITY={self.ability}"
        logger.info(msg)
        self.caller.msg(f"Logged usage: {msg}")


class CmdMarkVerified(Command):
    """Mark a move or ability as verified.

    Usage:
      @markverified move <name>
      @markverified ability <name>
    """

    key = "@markverified"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def parse(self):
        parts = self.args.split(None, 1)
        self.kind = parts[0].lower() if parts else ""
        self.name = parts[1].strip() if len(parts) > 1 else ""

    def func(self):
        if self.kind not in {"move", "ability"} or not self.name:
            self.caller.msg("Usage: @markverified (move|ability) <name>")
            return

        file = LOG_DIR / "verified_usage.json"
        data = {"moves": [], "abilities": []}
        if file.exists():
            try:
                data = json.loads(file.read_text())
            except Exception:
                pass
        if self.kind == "move":
            if self.name not in data["moves"]:
                data["moves"].append(self.name)
        else:
            if self.name not in data["abilities"]:
                data["abilities"].append(self.name)
        file.write_text(json.dumps(data, indent=2))
        self.caller.msg(f"{self.name} marked as verified {self.kind}.")
