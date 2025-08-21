from __future__ import annotations

"""Developer command to inspect a player's active ``BattleSession``."""

import json
from typing import Any, Iterable

from evennia import Command
from evennia.utils.search import search_object

# Colors (pipe-ANSI); adjust to theme
CLR_TITLE = "|w"
CLR_KEY = "|W"
CLR_VAL = "|y"
CLR_WARN = "|r"
CLR_RESET = "|n"


def _chunk(text: str, size: int = 3800) -> Iterable[str]:
	"""Yield ``text`` in chunks to avoid Evennia's message size limit."""

	for i in range(0, len(text), size):
		yield text[i : i + size]


def _is_dbref(s: str) -> bool:
	"""Return ``True`` if ``s`` looks like an Evennia #dbref."""

	return s.startswith("#") and s[1:].isdigit()


def _name(obj: Any) -> str:
	"""Return a display name for ``obj``."""

	return getattr(obj, "key", str(obj))


def _id(obj: Any) -> str:
	"""Return a database id for ``obj`` if available."""

	return str(getattr(obj, "id", "?"))


def _get_player(caller, arg: str):
	"""Resolve a player or object by ``arg``; default to ``caller``."""

	if not arg:
		return caller
	arg = arg.strip()
	if _is_dbref(arg):
		objs = search_object(arg)
	else:
		objs = search_object(arg)
	return objs[0] if objs else None


class CmdBattleInspect(Command):
	"""Inspect a player's in-memory ``BattleSession``."""

	key = "battleinspect"
	locks = "cmd:perm(Developers) or perm(Admin) or perm(Builder)"
	help_category = "Admin"

	def parse(self):  # type: ignore[override]
		"""Parse switches and target from command input."""

		self.switches = []
		self.target = ""
		if not self.args:
			return
		parts = self.args.split()
		for part in list(parts):
			if part.startswith("--"):
				self.switches.append(part)
				parts.remove(part)
		self.target = " ".join(parts).strip()

	def func(self):  # type: ignore[override]
		"""Execute the inspection command."""

		caller = self.caller
		player = _get_player(caller, self.target)
		if not player:
			self.msg(f"{CLR_WARN}Target not found.{CLR_RESET}")
			return

		# Prefer ndb; else attempt to restore via ensure_for_player
		bs = getattr(player.ndb, "battle_instance", None)
		if not bs:
			try:
				from fusion2.pokemon.battle.battleinstance import BattleSession
			except Exception:  # pragma: no cover - graceful fallback
				try:
					from pokemon.battle.battleinstance import BattleSession
				except Exception:  # pragma: no cover - final fallback
					BattleSession = None
			if BattleSession:
				bs = BattleSession.ensure_for_player(player)
		if not bs:
			self.msg(f"{CLR_WARN}No BattleSession found for {CLR_VAL}{_name(player)}{CLR_RESET}.")
			return

		# Build a concise summary first
		info = {
			"id": getattr(bs, "battle_id", None),
			"captainA": _name(getattr(bs, "captainA", None)),
			"captainB": _name(getattr(bs, "captainB", None)) if getattr(bs, "captainB", None) else None,
			"room_id": getattr(getattr(bs, "room", None), "id", None),
			"teamA": [_name(t) for t in getattr(bs, "teamA", [])],
			"teamB": [_name(t) for t in getattr(bs, "teamB", [])],
			"observers": [_name(o) for o in getattr(bs, "observers", set())],
			"watcher_ids": list(getattr(bs, "watchers", set())),
			"turn_state_keys": list(getattr(bs, "turn_state", {}).keys()),
			"temp_pokemon_ids": list(getattr(bs, "temp_pokemon_ids", [])),
			"has_logic": bool(getattr(bs, "logic", None)),
			"has_data": bool(getattr(bs, "data", None)),
			"has_state": bool(getattr(bs, "state", None)),
		}

		header = (
			f"{CLR_TITLE}BattleSession{CLR_RESET} {CLR_KEY}#{info['id']}{CLR_RESET}  "
			f"{CLR_KEY}{info['captainA']}{CLR_RESET} vs "
			f"{CLR_KEY}{info.get('captainB') or '<wild>'}{CLR_RESET}"
		)
		self.msg(header)
		self.msg(
			f"{CLR_KEY}Room:{CLR_RESET} {info['room_id']} | "
			f"{CLR_KEY}Watchers:{CLR_RESET} {len(info['watcher_ids'])} | "
			f"{CLR_KEY}Observers:{CLR_RESET} {len(info['observers'])}"
		)
		self.msg(f"{CLR_KEY}Team A:{CLR_RESET} {', '.join(info['teamA']) or '-'}")
		self.msg(f"{CLR_KEY}Team B:{CLR_RESET} {', '.join(info['teamB']) or '-'}")
		if info["turn_state_keys"]:
			self.msg(f"{CLR_KEY}Turn State:{CLR_RESET} {', '.join(info['turn_state_keys'])}")
		if info["temp_pokemon_ids"]:
			self.msg(f"{CLR_KEY}Temp Pokes:{CLR_RESET} {', '.join(map(str, info['temp_pokemon_ids']))}")

		# Positions & queued actions (if available)
		try:
			data = getattr(bs, "data", None)
			if data and hasattr(data, "turndata"):
				lines = []
				for pos_name, pos in data.turndata.positions.items():
					poke = getattr(pos, "pokemon", None)
					pname = getattr(poke, "name", "-") if poke else "-"
					action = pos.getAction() if hasattr(pos, "getAction") else None
					act = getattr(action, "desc", None) or str(action) if action else "-"
					lines.append(f" {pos_name:<3} {_name(pname):<16} -> {act}")
				if lines:
					self.msg(f"{CLR_KEY}Positions:{CLR_RESET}")
					for line in lines:
						self.msg(line)
		except Exception:  # pragma: no cover - best-effort debug view
			pass

		# Optional deep dump (data/state dicts)
		if "--deep" in self.switches:

			def safe_dump(obj):
				"""Return a JSON-serialisable representation of ``obj``.

				This handles Evennia's Saver* containers (such as ``_SaverDict``)
				by converting them to their plain Python counterparts and then
				recursively ensuring all nested values are JSON serialisable. If
				an object still cannot be dumped, its string representation is
				returned instead of raising an exception.
				"""

				try:
					if hasattr(obj, "to_dict"):
						obj = obj.to_dict()
					elif hasattr(obj, "items"):
						obj = dict(obj)
					elif isinstance(obj, (list, tuple, set)):
						obj = list(obj)

					if isinstance(obj, dict):
						return {str(k): safe_dump(v) for k, v in obj.items()}
					if isinstance(obj, list):
						return [safe_dump(v) for v in obj]

					json.dumps(obj)
					return obj
				except Exception:  # pragma: no cover - ignore dump errors
					try:
						return str(obj)
					except Exception:
						return {}

			deep = {
				"data": safe_dump(getattr(bs, "data", None)),
				"state": safe_dump(getattr(bs, "state", None)),
			}
			text = json.dumps(deep, indent=2, ensure_ascii=False)
			self.msg(f"{CLR_KEY}Deep dump (data/state):{CLR_RESET}")
			for segment in _chunk(text):
				self.msg(segment)
		else:
			self.msg(f"{CLR_KEY}Tip:{CLR_RESET} add {CLR_VAL}--deep{CLR_RESET} to include data/state JSON.")
