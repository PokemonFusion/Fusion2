"""Customized @py command with fixed prompts and multi-line output."""

from evennia.commands.default.system import CmdPy as _CmdPy
from evennia.commands.default.system import EvenniaPythonConsole as _EvenniaPythonConsole
import sys


class EvenniaPythonConsole(_EvenniaPythonConsole):
    """Console wrapper that preserves multi-line output."""

    def write(self, string: str) -> None:
        """Send all lines to the caller without truncation."""
        for line in string.splitlines():
            self.caller.msg(line)


class CmdPy(_CmdPy):
    """Drop-in replacement for @py using the non-truncating console."""

    def func(self):
        """Execute the command."""
        caller = self.caller
        pycode = self.args

        noecho = "noecho" in self.switches

        if "edit" in self.switches:
            return super().func()

        if not pycode:
            console = EvenniaPythonConsole(caller)
            banner = (
                "|gEvennia Interactive Python mode{echomode}\n"
                f"Python {sys.version} on {sys.platform}"
            ).format(echomode=" (no echoing of prompts)" if noecho else "")
            self.msg(banner)
            line = ""
            main_prompt = "|x[py mode - quit() to exit]|n"
            cont_prompt = "..."
            prompt = main_prompt
            while line.lower() not in ("exit", "exit()"):
                try:
                    line = yield (prompt)
                    needs_more = console.push(line)
                    if noecho:
                        prompt = cont_prompt if needs_more else main_prompt
                    else:
                        if line:
                            caller.msg(f">>> {line}")
                        prompt = cont_prompt if needs_more else main_prompt
                except SystemExit:
                    break
            self.msg("|gClosing the Python console.|n")
            return

        return super().func()
