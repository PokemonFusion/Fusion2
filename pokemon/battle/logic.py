from __future__ import annotations

"""Simple container tying together battle engine objects and persistent state."""

from collections import defaultdict
from typing import Dict, List, Sequence

from ._shared import restore_battle_value
from .battledata import BattleData, Team
from .engine import Battle, BattleParticipant, BattleType
from .state import BattleState


def _participant_identifier(pokemon) -> str:
        """Return a best-effort identifier for ``pokemon``.

        Persistent battle data stores multiple snapshots of the same PokÃƒÂ©mon.
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
        """Return active PokÃƒÂ©mon aligned with ``participant``'s roster.

        The persisted :class:`TurnData` keeps its own PokÃƒÂ©mon copies which are
        detached from the roster restored on :class:`BattleParticipant`.  The
        battle engine mutates the roster entries (for HP, status changes, etc.)
        so the position data must reference the same objects.  This helper
        rewires the position PokÃƒÂ©mon to the roster entries and returns them in
        active-slot order.
        """

        roster: Sequence = [p for p in participant.pokemons if p]
        if not roster:
                return []

        pools: Dict[str, List] = defaultdict(list)
        for mon in roster:
                pools[_participant_identifier(mon)].append(mon)

        active: List = []
        participant._active_slots = {}
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
                        # generated wild PokÃƒÂ©mon without stored ids).
                        for mon in roster:
                                if mon not in active:
                                        replacement = mon
                                        break
                if replacement:
                        setattr(pos, "pokemon", replacement)
                        active.append(replacement)
                        participant._active_slots[int(pos_name[1:]) - 1] = replacement
        return active


class BattleLogic:
	"""Live battle logic stored only in ``ndb``."""

	def __init__(self, battle, data, state):
		self.battle = battle
		self.data = data
		self.state = state
		from .item_boosts import ItemRandomState

		ItemRandomState.restore(battle, getattr(state, "item_rng_state", None))
		# One live field must also be the checkpoint's field. Otherwise an
		# executed Trick Room disappears during a save/rebuild.
		data.field = battle.field
		battle.debug = getattr(state, "debug", False)
		battle.fail_fast_errors = bool(getattr(battle, "debug", False))
		battle.award_xp = bool(getattr(state, "xp", True))
		battle.award_txp = bool(getattr(state, "txp", True))
		battle._rewards_granted = bool(getattr(state, "rewards_granted", False))
		battle.battle_over = bool(getattr(state, "battle_over", False))
		battle.flee_allowed = getattr(state, "flee_allowed", True) is True
		battle._flee_result = dict(getattr(state, "flee_result", {}) or {})
		battle.capture_succeeded = bool(getattr(state, "capture_succeeded", False))
		battle.failed_capture_ball = str(getattr(state, "failed_capture_ball", "") or "")
		battle.tera_used = set(getattr(state, "tera_used", []))
		battle.tera_pending = {key: dict(value) for key, value in getattr(state, "tera_pending", {}).items()}
		if (type(getattr(state, "mechanic_version", 1)) is not int or getattr(state, "mechanic_version", 1) != 1
				or type(getattr(state, "mechanic_turn", 0)) is not int or getattr(state, "mechanic_turn", 0) < 0):
			raise ValueError("Unsupported or corrupt battle mechanic checkpoint.")
		battle.mechanic_battle_id = getattr(state, "reward_id", None)
		battle.mechanic_turn = getattr(state, "mechanic_turn", 0)
		battle.mechanic_controllers = dict(getattr(state, "pokemon_control", {}))
		battle.mega_used = set(getattr(state, "mega_used", []))
		battle.mega_pending = {key: dict(value) for key, value in getattr(state, "mega_pending", {}).items()}
		z_used, z_pending = getattr(state, "z_used", []), getattr(state, "z_pending", {})
		from collections.abc import Mapping, MutableSequence

		if (not isinstance(z_used, (list, tuple, MutableSequence)) or any(side not in {"A", "B"} for side in z_used)
				or len(z_used) != len(set(z_used)) or not isinstance(z_pending, Mapping)
				or any(side not in {"A", "B"} or not isinstance(value, Mapping) for side, value in z_pending.items())):
			raise ValueError("Corrupt Z side ledger requires recovery.")
		battle.z_used = set(z_used)
		battle.z_pending = {key: dict(value) for key, value in getattr(state, "z_pending", {}).items()}
		from .mega_evolution import MegaEvolution
		from .z_moves import ZMoves

		ultra_used, ultra_pending = getattr(state, "ultra_used", []), getattr(state, "ultra_pending", {})
		if (not isinstance(ultra_used, (list, tuple, MutableSequence))
				or any(side not in {"A", "B"} for side in ultra_used)
				or len(ultra_used) != len(set(ultra_used)) or not isinstance(ultra_pending, Mapping)
				or any(side not in {"A", "B"} or not isinstance(value, Mapping) for side, value in ultra_pending.items())):
			raise ValueError("Corrupt Ultra side ledger requires recovery.")
		battle.ultra_used = set(ultra_used)
		from ._shared import snapshot_battle_value

		battle.ultra_pending = snapshot_battle_value(ultra_pending)
		MegaEvolution.recover(battle)
		from .ultra_burst import UltraBurst

		UltraBurst.recover(battle)
		ZMoves.recover(battle, state.declare)
		from .z_effects import ZEffects

		ZEffects.recover(battle, getattr(state, "z_effects", {}))
		from .battle_boosters import BattleBoosters

		BattleBoosters.recover(battle, getattr(state, "booster_effects", {}))
		from .item_consumption import ItemUseHistory

		ItemUseHistory.restore_sides(battle, getattr(state, "used_item_history", {}))
		for index, participant in enumerate(battle.participants):
			team = getattr(participant, "team", None) or ("A" if index == 0 else "B")
			participant.flee_attempts = getattr(state, "flee_attempts", {}).get(team, 0)
			participant.last_ai_switch_turn = getattr(state, "ai_switch_turns", {}).get(team, -100)
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
		# A restored dispatcher is empty even when its saved turn is nonzero.
		# Bind current holders without replaying entry, forms or Start effects.
		register = getattr(battle, "register_handlers", None)
		if callable(register):
			for participant in battle.participants:
				for pokemon in getattr(participant, "active", []):
					register(pokemon)

	def to_dict(self):
		self.sync_runtime_state()
		return {
			"data": self.data.to_dict(),
			"state": self.state.to_dict(),
		}

	def sync_runtime_state(self):
		"""Freeze primitive result and participation state before a checkpoint."""
		self.data.field = self.battle.field
		self.state.rewards_granted = bool(getattr(self.battle, "_rewards_granted", False))
		self.state.battle_over = bool(getattr(self.battle, "battle_over", False))
		self.state.flee_allowed = getattr(self.battle, "flee_allowed", True) is True
		self.state.capture_succeeded = bool(getattr(self.battle, "capture_succeeded", False))
		self.state.failed_capture_ball = str(getattr(self.battle, "failed_capture_ball", "") or "")
		self.state.tera_used = sorted(getattr(self.battle, "tera_used", set()))
		self.state.tera_pending = {key: dict(value) for key, value in getattr(self.battle, "tera_pending", {}).items()}
		self.state.mechanic_turn = getattr(self.battle, "mechanic_turn", 0)
		self.state.ultra_used = sorted(getattr(self.battle, "ultra_used", set()))
		self.state.ultra_pending = {key: dict(value) for key, value in getattr(self.battle, "ultra_pending", {}).items()}
		self.state.mega_used = sorted(getattr(self.battle, "mega_used", set()))
		self.state.mega_pending = {key: dict(value) for key, value in getattr(self.battle, "mega_pending", {}).items()}
		self.state.z_used = sorted(getattr(self.battle, "z_used", set()))
		self.state.z_pending = {key: dict(value) for key, value in getattr(self.battle, "z_pending", {}).items()}
		from .z_effects import ZEffects

		self.state.z_effects = ZEffects.freeze(self.battle)
		from .battle_boosters import BattleBoosters

		self.state.booster_effects = BattleBoosters.freeze(self.battle)
		from .item_consumption import ItemUseHistory

		self.state.used_item_history = ItemUseHistory.freeze_sides(self.battle)
		from .item_boosts import ItemRandomState

		self.state.item_rng_state = ItemRandomState.freeze(self.battle)
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
		self.state.ai_switch_turns = {key: int(getattr(part, "last_ai_switch_turn", -100)) for key, part in teams}
		self.state.participants = {
			key: [_participant_identifier(mon) for mon in (getattr(part, "participating_pokemon", []) or getattr(part, "active", []))]
			for key, part in teams
		}
		if getattr(self.state, 'multi', None):
			from .multi_state import freeze
			freeze(self)

	@classmethod
	def from_dict(cls, info):
		data = BattleData.from_dict(info.get("data", {}))
		state = BattleState.from_dict(info.get("state", {}))
		if getattr(state, 'multi', None):
			from .multi_state import rebuild
			return rebuild(cls, data, state)

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
		pokemon_by_ref = {_participant_identifier(mon): mon for part in (part_a, part_b) for mon in part.pokemons}
		for part in (part_a, part_b):
			for mon in part.pokemons:
				mon.tempvals = restore_battle_value(mon.tempvals, pokemon_by_ref, field=data.field)
				mon.volatiles = restore_battle_value(mon.volatiles, pokemon_by_ref, field=data.field)
				mon.ability_state = restore_battle_value(mon.ability_state, pokemon_by_ref, field=data.field)
				mon.item_state = restore_battle_value(mon.item_state, pokemon_by_ref, field=data.field)
				mon.last_move = restore_battle_value(getattr(mon, "last_move", None), pokemon_by_ref, field=data.field)
		for name in ("weather_state", "terrain_state", "pseudo_weather"):
			setattr(data.field, name, restore_battle_value(getattr(data.field, name), pokemon_by_ref, field=data.field))
		battle.field = data.field
		# Handlers are runtime objects, not checkpoint data. Reconnect them
		# without setWeather/setTerrain, whose Start hooks reset durations and
		# replay activation effects on every restore.
		for name in ("weather", "terrain"):
			effect = getattr(data.field, name, None)
			setattr(data.field, name + "_handler", battle._lookup_effect(effect) if effect else None)
		battle.weather_state = data.field.weather_state
		battle.turn_count = data.battle.turn
		battle.debug = getattr(state, "debug", False)
		battle.fail_fast_errors = bool(getattr(battle, "debug", False))
		return cls(battle, data, state)
