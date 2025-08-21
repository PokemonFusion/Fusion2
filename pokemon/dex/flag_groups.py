"""Utilities for grouping moves by shared flags.

This module exposes a helper used primarily for data driven tests.  It
inspects the loaded movedex and builds a mapping of individual flag names to
the moves which declare them.  The returned structure allows tests to easily
parameterize over all moves that share a particular behavioural flag such as
``heal`` or ``snatch``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from . import MOVEDEX, Move


def get_move_flag_groups(movedex: Optional[Dict[str, Move]] = None) -> Dict[str, List[str]]:
	"""Group move names by the flags they expose.

	Parameters
	----------
	movedex:
	    Optional mapping of move identifiers to :class:`~pokemon.dex.entities.Move`
	    instances.  When omitted the project's global ``MOVEDEX`` is used.

	Returns
	-------
	dict
	    A dictionary mapping each flag name to the list of move names declaring
	    that flag.
	"""

	dex = movedex or MOVEDEX
	groups: Dict[str, List[str]] = {}
	for move in dex.values():
		flags = move.raw.get("flags", {}) or {}
		for flag in flags:
			groups.setdefault(flag, []).append(move.name)
	return groups


__all__ = ["get_move_flag_groups"]
