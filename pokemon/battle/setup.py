"""Utilities for initializing battle state and participants."""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from .battledata import BattleData, Pokemon, Team
from .engine import Battle, BattleParticipant, BattleType
from .logic import BattleLogic
from .state import BattleState


def create_participants(
	captain,
	player_pokemon: List[Pokemon],
	opponent_poke: Pokemon,
	opponent_name: str,
) -> Tuple[BattleParticipant, BattleParticipant]:
	"""Return participants for the player and the opponent.

	``BattleParticipant`` implementations used in tests may not accept the
	``team`` or ``player`` keyword arguments. This helper attempts to supply
	them when available and falls back gracefully when they're unsupported.
	"""
	try:
		opponent_participant = BattleParticipant(opponent_name, [opponent_poke], is_ai=True, team="B")
	except TypeError:
		opponent_participant = BattleParticipant(opponent_name, [opponent_poke], is_ai=True)

	try:
		player_participant = BattleParticipant(captain.key, player_pokemon, player=captain, team="A")
	except TypeError:
		try:
			player_participant = BattleParticipant(captain.key, player_pokemon, team="A")
		except TypeError:
			player_participant = BattleParticipant(captain.key, player_pokemon)

	if player_participant.pokemons:
		player_participant.active = [player_participant.pokemons[0]]
	if opponent_participant.pokemons:
		opponent_participant.active = [opponent_participant.pokemons[0]]

	return player_participant, opponent_participant


def build_initial_state(
	origin,
	battle_type: BattleType,
	player_participant: BattleParticipant,
	opponent_participant: BattleParticipant,
	player_pokemon: List[Pokemon],
	opponent_poke: Pokemon,
	captainA,
	notify: Callable[[str], None],
	captainB: Optional[object] = None,
) -> BattleLogic:
	"""Construct the initial battle objects and return the logic wrapper."""
	battle = Battle(battle_type, [player_participant, opponent_participant])

	player_team = Team(trainer=captainA.key, pokemon_list=player_pokemon)
	opponent_name = getattr(opponent_participant, "key", None) or getattr(opponent_participant, "name", "Opponent")
	opponent_team = Team(trainer=opponent_name, pokemon_list=[opponent_poke])
	data = BattleData(player_team, opponent_team)

	state = BattleState.from_battle_data(data, ai_type=battle_type.name)
	state.roomweather = getattr(getattr(origin, "db", {}), "weather", "clear")
	state.pokemon_control = {}
	for poke in player_pokemon:
		if getattr(poke, "model_id", None):
			owner_id = getattr(captainA, "id", getattr(captainA, "key", None))
			if owner_id is not None:
				state.pokemon_control[str(poke.model_id)] = str(owner_id)
	if getattr(opponent_poke, "model_id", None) and captainB:
		owner_id = getattr(captainB, "id", getattr(captainB, "key", None))
		if owner_id is not None:
			state.pokemon_control[str(opponent_poke.model_id)] = str(owner_id)

	logic = BattleLogic(battle, data, state)
	logic.battle.log_action = notify
	return logic


def persist_initial_state(
	session,
	player_participant: BattleParticipant,
	player_pokemon: List[Pokemon],
) -> None:
	"""Persist battle information for later restoration."""
	try:
		session.captainA.team = player_pokemon
		if player_participant.active:
			session.captainA.active_pokemon = player_participant.active[0]
	except Exception:
		pass

	session.storage.set("data", session.logic.data.to_dict())
	session.storage.set("state", session.logic.state.to_dict())
	session.storage.set("temp_pokemon_ids", list(session.temp_pokemon_ids))
	trainer_ids = {"teamA": []}
	if hasattr(session.captainA, "id"):
		trainer_ids["teamA"].append(session.captainA.id)
	if session.captainB:
		trainer_ids["teamB"] = []
		if hasattr(session.captainB, "id"):
			trainer_ids["teamB"].append(session.captainB.id)
	session.storage.set("trainers", trainer_ids)
