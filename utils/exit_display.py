"""Shared display helpers for room exits."""

from __future__ import annotations

import re


def format_exit_name(name: str) -> str:
	"""Return an exit name with parenthesized shortcut letters highlighted."""
	if not name:
		return ""

	def repl(match: re.Match) -> str:
		inner = match.group(1)
		return f"|c(|w{inner}|c)"

	colored = re.sub(r"\(([^)]*)\)", repl, str(name))
	if colored.startswith("|c"):
		return f"{colored}|n"
	return f"|c{colored}|n"
