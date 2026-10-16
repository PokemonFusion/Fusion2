from __future__ import annotations

"""Simple container tying together battle engine objects and persistent state."""

from collections import defaultdict
from typing import Dict, List, Sequence

from .battledata import BattleData, Team
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
		battle.fail_fast_errors = bool(getattr(battle, "debug", False))
		battle.award_xp = bool(getattr(state, "xp", True))
		battle.award_txp = bool(getattr(state, "txp", True))
		battle._rewards_granted = bool(getattr(state, "rewards_granted", False))
		battle.battle_over = bool(getattr(state, "battle_over", False))
		battle._flee_result = dict(getattr(state, "flee_result", {}) or {})
		battle.capture_succeeded = bool(getattr(state, "capture_succeeded", False))
		for index, participant in enumerate(battle.participants):
			team = getattr(participant, "team", None) or ("A" if index == 0 else "B")
			participant.flee_attempts = getattr(state, "flee_attempts", {}).get(team, 0)
			saved = getattr(state, "participants", {}).get(team)
			if saved is not None:
				participant.participating_pokemon = []
				participant._participant_cache = set()
				for mon in participant.pokemons:
					if _participant_identifier(mon) in saved:
						if hasattr(participant, "record_participation"):
							participant.record_participation(mon)
						else:
							participant.participating_pokemon.append(mon)
		bind_reveal_data = getattr(battle, "bind_reveal_data", None)
		if callable(bind_reveal_data):
			bind_reveal_data(data)

	def to_dict(self):
		self.sync_runtime_state()
		return {
			"data": self.data.to_dict(),
			"state": self.state.to_dict(),
		}

	def sync_runtime_state(self):
		"""Freeze primitive result and participation state before a checkpoint."""
		self.state.rewards_granted = bool(getattr(self.battle, "_rewards_granted", False))
		self.state.battle_over = bool(getattr(self.battle, "battle_over", False))
		self.state.capture_succeeded = bool(getattr(self.battle, "capture_succeeded", False))
		teams = [
			(getattr(part, "team", None) or ("A" if index == 0 else "B"), part)
			for index, part in enumerate(self.battle.participants)
		]
		for key, participant in teams:
			team = self.data.teams.get(key)
			if team is not None:
				self.data.teams[key] = Team(team.trainer, participant.pokemons)
		flee = getattr(self.battle, "_flee_result", {}) or {}
		self.state.flee_result = {key: flee[key] for key in ("success", "reason", "message") if key in flee}
		self.state.flee_attempts = {key: int(getattr(part, "flee_attempts", 0)) for key, part in teams}
		self.state.participants = {
			key: [_participant_identifier(mon) for mon in (getattr(part, "participating_pokemon", []) or getattr(part, "active", []))]
			for key, part in teams
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
		part_b.is_ai = state.ai_type.upper() not in {"PLAYER", "PVP"}
		try:
			positions = getattr(data.turndata, "positions", {}) or {}
		except Exception:
			positions = {}
		if isinstance(positions, dict) and positions:
			part_a.max_active = max(1, sum(str(key).startswith("A") for key in positions))
			part_b.max_active = max(1, sum(str(key).startswith("B") for key in positions))
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
		for part in (part_a, part_b):
			part.active = [mon for mon in part.active if mon.hp > 0]
			conscious = [mon for mon in part.pokemons if mon.hp > 0]
			part.has_lost = not conscious
			if not part.active and conscious:
				part.active = conscious[:part.max_active]
			if getattr(part, "side", None) is not None:
				part.side.active = part.active
		battle = Battle(btype, [part_a, part_b])
		battle.turn_count = data.battle.turn
		battle.debug = getattr(state, "debug", False)
		battle.fail_fast_errors = bool(getattr(battle, "debug", False))
		return cls(battle, data, state)
