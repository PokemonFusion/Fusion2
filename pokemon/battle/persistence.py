"""Helpers for compacting battle state for persistence."""

from __future__ import annotations

from typing import Any, Dict, List

try:  # pragma: no cover - tests may stub watchers without helper
	from .watchers import normalize_watchers
except Exception:  # pragma: no cover - fallback when watcher helper missing

	def normalize_watchers(val: Any) -> List[int]:  # type: ignore[misc]
		if isinstance(val, list):
			return [int(x) for x in val if isinstance(x, (int, str))]
		if isinstance(val, set):
			return [int(x) for x in val]
		if isinstance(val, str):
			s = val.strip()
			if s.startswith("{") and s.endswith("}"):
				s = s[1:-1]
			out: List[int] = []
			for part in s.split(","):
				part = part.strip()
				if not part:
					continue
				try:
					out.append(int(part))
				except Exception:
					continue
			return out
		return []


# Defaults used for compacting persisted state (omit if same as default)
DEFAULT_FLAGS: Dict[str, int | bool] = {
	"xp": True,
	"txp": True,
	"tier": 1,
	"four_moves": False,
}


class StatePersistenceMixin:
	"""Mixin providing helpers for saving battle state."""

	def _compact_state_for_persist(self, st: Dict[str, Any]) -> Dict[str, Any]:
		"""Return a compacted copy of ``st`` suitable for storage."""
		state: Dict[str, Any] = dict(st) if st else {}
		state.pop("turn", None)
		state.pop("teams", None)
		state.pop("movesets", None)
		live_watch: List[int] = list(getattr(self.ndb, "watchers_live", []))
		state["watchers"] = live_watch or normalize_watchers(state.get("watchers", []))
		for k, default in DEFAULT_FLAGS.items():
			if state.get(k, default) == default:
				state.pop(k, None)
		return state


__all__ = ["StatePersistenceMixin", "DEFAULT_FLAGS"]
