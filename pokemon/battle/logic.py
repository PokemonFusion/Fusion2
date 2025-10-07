from __future__ import annotations

"""Simple container tying together battle engine objects and persistent state."""

from collections import defaultdict
from typing import Dict, List, Sequence

from .battledata import BattleData
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState


def _participant_identifier(pokemon) -> str:
        """Return a best-effort identifier for ``pokemon``.

        Persistent battle data stores multiple snapshots of the same Pokémon.
        When rebuilding live battle objects after a server restart we need to
        match the copies stored on the teams with the copies embedded in the
        active position data.  Prefer unique database-backed identifiers when
        available and otherwise fall back to a reproducible textual key.
        """

        for attr in ("model_id", "unique_id", "id"):
                value = getattr(pokemon, attr, None)
                if value not in (None, "", "0"):
                        return str(value)
        name = getattr(pokemon, "name", getattr(pokemon, "species", "Pokemon"))
        level = getattr(pokemon, "level", "?")
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", "?"))
        return f"{name}|{level}|{max_hp}"


def _align_positions_with_team(
        participant: BattleParticipant,
        positions: Dict[str, object],
        team_key: str,
) -> List:
        """Return active Pokémon aligned with ``participant``'s roster.

        The persisted :class:`TurnData` keeps its own Pokémon copies which are
        detached from the roster restored on :class:`BattleParticipant`.  The
        battle engine mutates the roster entries (for HP, status changes, etc.)
        so the position data must reference the same objects.  This helper
        rewires the position Pokémon to the roster entries and returns them in
        active-slot order.
        """

        roster: Sequence = [p for p in participant.pokemons if p]
        if not roster:
                return []

        pools: Dict[str, List] = defaultdict(list)
        for mon in roster:
                pools[_participant_identifier(mon)].append(mon)

        active: List = []
        for pos_name, pos in positions.items():
                if not isinstance(pos_name, str) or not pos_name.startswith(team_key):
                        continue
                pokemon = getattr(pos, "pokemon", None)
                if not pokemon:
                        continue
                ident = _participant_identifier(pokemon)
                replacement = None
                candidates = pools.get(ident)
                if candidates:
                        replacement = candidates.pop(0)
                else:
                        # Fallback: pick the first roster member that has not
                        # already been assigned. This keeps the battle running
                        # even if identifiers could not be matched (e.g. for
                        # generated wild Pokémon without stored ids).
                        for mon in roster:
                                if mon not in active:
                                        replacement = mon
                                        break
                if replacement:
                        setattr(pos, "pokemon", replacement)
                        active.append(replacement)
        return active


class BattleLogic:
	"""Live battle logic stored only in ``ndb``."""

	def __init__(self, battle, data, state):
		self.battle = battle
		self.data = data
		self.state = state
		battle.debug = getattr(state, "debug", False)

	def to_dict(self):
		return {
			"data": self.data.to_dict(),
			"state": self.state.to_dict(),
		}

	@classmethod
	def from_dict(cls, info):
		data = BattleData.from_dict(info.get("data", {}))
		state = BattleState.from_dict(info.get("state", {}))

		teamA = data.teams.get("A")
		teamB = data.teams.get("B")
		try:
			part_a = BattleParticipant(
				teamA.trainer,
				[p for p in teamA.returnlist() if p],
				is_ai=False,
				team="A",
			)
		except TypeError:
			part_a = BattleParticipant(
				teamA.trainer,
				[p for p in teamA.returnlist() if p],
				is_ai=False,
			)
		try:
			part_b = BattleParticipant(
				teamB.trainer,
				[p for p in teamB.returnlist() if p],
				team="B",
			)
		except TypeError:
			part_b = BattleParticipant(
				teamB.trainer,
				[p for p in teamB.returnlist() if p],
			)
		part_b.is_ai = state.ai_type != "Player"
		try:
			positions = getattr(data.turndata, "positions", {}) or {}
		except Exception:
			positions = {}
		if isinstance(positions, dict) and positions:
			active_a = _align_positions_with_team(part_a, positions, "A")
			if active_a:
				part_a.active = active_a[: part_a.max_active]
			active_b = _align_positions_with_team(part_b, positions, "B")
			if active_b:
				part_b.active = active_b[: part_b.max_active]
		else:
			pos_a = data.turndata.teamPositions("A").get("A1")
			if pos_a and pos_a.pokemon:
				part_a.active = [pos_a.pokemon]
			pos_b = data.turndata.teamPositions("B").get("B1")
			if pos_b and pos_b.pokemon:
				part_b.active = [pos_b.pokemon]
		try:
			btype = BattleType[state.ai_type.upper()]
		except KeyError:
			btype = BattleType.WILD
		battle = Battle(btype, [part_a, part_b])
		battle.turn_count = data.battle.turn
		battle.debug = getattr(state, "debug", False)
		return cls(battle, data, state)
