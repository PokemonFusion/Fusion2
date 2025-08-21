"""Helpers for constructing ephemeral test Pokémon."""

from dataclasses import dataclass, field
from typing import List, Optional
import random

try:
	from PKMN_Fusion_Python.movesdex import MOVEDEX
except Exception:  # pragma: no cover - optional dependency
	MOVEDEX = {}

from pokemon.helpers.pokemon_helpers import get_max_hp

@dataclass
class EphemeralPokemon:
	"""Lightweight Pokémon container compatible with the battle layer."""
	name: str
	species: str
	level: int
	hp: int
	max_hp: int
	types: List[str]
	ability: Optional[str] = None
	item: Optional[str] = None
	moves: List[str] = field(default_factory=list)
	ivs: List[int] = field(default_factory=lambda: [0,0,0,0,0,0])
	evs: List[int] = field(default_factory=lambda: [0,0,0,0,0,0])
	nature: str = "Hardy"

def _validate_moves(moves: List[str]) -> List[str]:
	if not MOVEDEX:
		return moves
	valid = []
	errors = []
	for mv in moves:
		key = mv.strip().lower().replace(" ", "")
		if key in MOVEDEX:
			valid.append(mv)
		else:
			errors.append(mv)
	if errors:
		raise ValueError(f"Unknown moves: {', '.join(errors)}")
	return valid

def make_test_pokemon(*, level: int, moves: List[str], ability: Optional[str], item: Optional[str], seed: Optional[int]):
	"""Construct a temporary Pokémon for testing."""
	moves = _validate_moves(moves)
	if seed is not None:
		random.seed(seed)
	species = "Eevee"
	proto = EphemeralPokemon(
		name="TestMon",
		species=species,
		level=level,
		hp=0,
		max_hp=0,
		types=["Normal"],
		ability=ability,
		item=item,
		moves=moves,
	)
	max_hp = get_max_hp(proto)
	proto.hp = proto.max_hp = max_hp
	return proto

def make_punching_bag(*, hp: int, level: int):
	"""Create a high-HP dummy opponent."""
	species = "Eevee"
	proto = EphemeralPokemon(
		name="PunchBagMon",
		species=species,
		level=level,
		hp=0,
		max_hp=0,
		types=["Normal"],
	)
	max_hp = get_max_hp(proto)
	proto.max_hp = proto.hp = hp if hp else max_hp
	return proto
