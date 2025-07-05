from __future__ import annotations

import subprocess

from evennia import Command


class CmdGitPull(Command):
    """Pull the latest code from the git repository."""

    key = "+gitpull"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if result.stdout:
            self.caller.msg(result.stdout)
        if result.stderr:
            self.caller.msg(result.stderr)
