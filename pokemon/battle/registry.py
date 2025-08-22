"""Lightweight battle session registry.

Use this from commands to resolve which battle a caller is in/watching.
Engine code can register/unregister sessions explicitly.
"""

from __future__ import annotations

import weakref
from typing import List


class _Registry:
	def __init__(self) -> None:
		self._sessions: "weakref.WeakSet[object]" = weakref.WeakSet()

	def register(self, session) -> None:
		if session:
			self._sessions.add(session)

	def unregister(self, session) -> None:
		try:
			self._sessions.discard(session)
		except Exception:
			pass

	def all(self) -> List[object]:
		return list(self._sessions)

	def get_by_id(self, ident: str):
		for s in self._sessions:
			sid = getattr(s, "id", None) or getattr(s, "uuid", None) or str(id(s))
			if str(sid) == str(ident) or str(sid).endswith(str(ident).lstrip("#")):
				return s
		return None

	def sessions_for(self, caller) -> List[object]:
		out: List[object] = []
		for s in self._sessions:
			if caller in getattr(s, "teamA", []) or caller == getattr(s, "captainA", None):
				out.append(s)
				continue
			if caller in getattr(s, "teamB", []) or caller == getattr(s, "captainB", None):
				out.append(s)
				continue
			if caller in getattr(s, "observers", []):
				out.append(s)
		return out


REGISTRY = _Registry()
