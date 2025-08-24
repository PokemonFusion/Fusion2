"""Utility helpers for the room/exit builder.

This module exposes small helper functions used by the room builder views.
"""
from __future__ import annotations

from collections.abc import Iterable

# Mapping of common exit directions to their reverse counterparts.
DIR_REVERSE = {
	"north": "south",
	"south": "north",
	"east": "west",
	"west": "east",
	"northeast": "southwest",
	"ne": "sw",
	"northwest": "southeast",
	"nw": "se",
	"southeast": "northwest",
	"se": "nw",
	"southwest": "northeast",
	"sw": "ne",
	"up": "down",
	"down": "up",
	"in": "out",
	"out": "in",
}



def reverse_dir(direction: str) -> str | None:
	"""Return the reverse of ``direction`` if known.

	Args:
		direction: The exit direction to reverse.

	Returns:
		The opposite direction or ``None`` if no mapping exists.
	"""
	if not direction:
		return None
	direction = direction.lower().strip()
	return DIR_REVERSE.get(direction)



def normalize_aliases(raw: str | Iterable[str]) -> list[str]:
	"""Normalize a comma-separated string of aliases.

	Args:
		raw: Either a string of aliases separated by commas/semicolons or an
		iterable of alias strings.

	Returns:
		A list of unique, stripped alias strings.
	"""
	if not raw:
		return []
	if isinstance(raw, str):
		parts = [p.strip() for p in raw.replace(";", ",").split(",")]
	else:
		parts = [str(p).strip() for p in raw]
	return [p for p in parts if p]
