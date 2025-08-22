"""Utility helpers for Pokémon spawn rolls."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from evennia import DefaultRoom

from pokemon.data.generation import PokemonInstance, generate_pokemon
from utils.pokemon_config import RARITY_WEIGHTS, TIERS


def weighted_choice(choices: List[Dict]) -> Optional[Dict]:
	"""Return a random item from a list of spawn entries based on rarity."""
	if not choices:
		return None
	weights = [RARITY_WEIGHTS.get(c.get("rarity", "common"), 1) for c in choices]
	return random.choices(choices, weights=weights, k=1)[0]


def roll_level(tiers: List[str]) -> int:
	"""Roll a random level from provided tier names."""
	options: List[str] = [t for t in tiers if t in TIERS]
	if not options:
		options = ["T1"]
	tier = random.choice(options)
	low, high = TIERS[tier]
	return random.randint(low, high)


def get_spawn(
	room: DefaultRoom, *, tiers: Optional[List[str]] = None, generations: Optional[List[str]] = None
) -> Optional[PokemonInstance]:
	"""Return a generated Pokémon from the room's spawn table."""
	table: List[Dict] = room.db.spawn_table or []
	# Filter by tier/generation if provided
	if tiers:
		table = [e for e in table if any(t in e.get("tiers", []) for t in tiers)]
	if generations:
		table = [e for e in table if any(g in e.get("generations", []) for g in generations)]

	entry = weighted_choice(table)
	if not entry:
		return None
	level = roll_level(entry.get("tiers", []))
	return generate_pokemon(entry["species"], level=level)
