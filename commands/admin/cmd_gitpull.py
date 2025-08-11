from __future__ import annotations

import subprocess

from evennia import Command


class CmdGitPull(Command):
    """Update the server's code from the git repository.

    Usage:
      @gitpull

    This will run ``git pull`` in the game directory and relay any
    output back to the caller.
    """

    key = "@gitpull"
    locks = "cmd:perm(Wizards)"
    help_category = "Admin"

    def func(self):
        """Run ``git pull`` and inform caller of progress and result."""
        self.caller.msg("Running git pull, please wait...")

        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if result.stdout:
            self.caller.msg(result.stdout)

        if result.returncode == 0:
            summary = "Git pull completed successfully."
        else:
            summary = f"Git pull failed with return code {result.returncode}."

        if result.stderr:
            summary += f"\n{result.stderr}"

        self.caller.msg(summary)
