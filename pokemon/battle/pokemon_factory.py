from __future__ import annotations

"""Helpers for creating battle-ready :class:`~pokemon.battle.battledata.Pokemon`."""

from types import SimpleNamespace
from typing import List

from pokemon.helpers.pokemon_spawn import get_spawn
from pokemon.services.encounters import create_encounter_pokemon, encounter_ref
from pokemon.services.pokemon_refs import build_owned_ref

from ..data.generation import generate_pokemon
from .battledata import Move, Pokemon


def _stat_list(source) -> List[int]:
	"""Return a 6-length list of stats from ``source``."""

	if isinstance(source, list):
		return [int(x) for x in source[:6]] + [0] * (6 - len(source[:6]))
	if source is None:
		return [0, 0, 0, 0, 0, 0]
	return [
		getattr(source, "hp", 0),
		getattr(source, "atk", 0),
		getattr(source, "def_", getattr(source, "def", 0)),
		getattr(source, "spa", 0),
		getattr(source, "spd", 0),
		getattr(source, "spe", 0),
	]


def _calc_stats_from_model(poke):
	"""Return calculated stats for a stored Pokemon model."""
	try:
		from ..stats import calculate_stats
	except Exception:  # pragma: no cover
		calculate_stats = None

	ivs_list = _stat_list(getattr(poke, "ivs", None))
	evs_list = _stat_list(getattr(poke, "evs", None))
	nature = getattr(poke, "nature", "Hardy")
	name = getattr(poke, "name", getattr(poke, "species", "Pikachu"))
	level = getattr(poke, "level", 1)

	ivs = {
		"hp": ivs_list[0],
		"atk": ivs_list[1],
		"def": ivs_list[2],
		"spa": ivs_list[3],
		"spd": ivs_list[4],
		"spe": ivs_list[5],
	}
	evs = {
		"hp": evs_list[0],
		"atk": evs_list[1],
		"def": evs_list[2],
		"spa": evs_list[3],
		"spd": evs_list[4],
		"spe": evs_list[5],
	}

	try:
		if calculate_stats:
			return calculate_stats(name, level, ivs, evs, nature)
		raise Exception
	except Exception:
		try:
			inst = generate_pokemon(name, level=level)
			st = getattr(inst, "stats", inst)
		except Exception:
			current_hp = getattr(poke, "max_hp", getattr(poke, "current_hp", 1))
			return {
				"hp": current_hp,
				"atk": 0,
				"def": 0,
				"spa": 0,
				"spd": 0,
				"spe": 0,
			}
		return {
			"hp": getattr(st, "hp", 100),
			"atk": getattr(st, "atk", 0),
			"def": getattr(st, "def_", 0),
			"spa": getattr(st, "spa", 0),
			"spd": getattr(st, "spd", 0),
			"spe": getattr(st, "spe", 0),
		}


def create_battle_pokemon(
	species: str,
	level: int,
	*,
	trainer: object | None = None,
	is_wild: bool = False,
	template_key: str = "",
	move_names: list[str] | None = None,
) -> Pokemon:
	"""Return a ``Pokemon`` battle object for the given species/level."""

	inst = generate_pokemon(species, level=level)
	move_names = list(move_names or getattr(inst, "moves", []) or ["Flail"])
	moves = [Move(name=m) for m in move_names]

	ivs_list = _stat_list(getattr(inst, "ivs", None))
	evs_list = _stat_list(getattr(inst, "evs", None))
	nature = getattr(inst, "nature", "Hardy")
	max_hp = getattr(inst.stats, "hp", level)

	try:
		encounter = create_encounter_pokemon(
			species=inst.species.name,
			level=inst.level,
			source_kind="wild" if is_wild else "npc",
			gender=getattr(inst, "gender", "N"),
			nature=nature,
			ability=getattr(inst, "ability", ""),
			ivs=ivs_list,
			evs=evs_list,
			current_hp=max_hp,
			move_names=move_names,
			npc_trainer=trainer if not is_wild else None,
			template_key=template_key,
		)
	except Exception:
		encounter = SimpleNamespace(current_hp=max_hp, held_item="", encounter_id=None)

	return Pokemon(
		name=inst.species.name,
		level=inst.level,
		hp=encounter.current_hp,
		max_hp=max_hp,
		moves=moves,
		ability=getattr(inst, "ability", None),
		ivs=ivs_list,
		evs=evs_list,
		nature=nature,
		model_id=encounter_ref(encounter),
		gender=getattr(inst, "gender", "N"),
		item=getattr(encounter, "held_item", ""),
	)


def generate_wild_pokemon(location=None) -> Pokemon:
	"""Generate a wild Pokemon based on the supplied location."""

	inst = get_spawn(location) if location else None
	if not inst:
		species = "Pikachu"
		level = 5
	else:
		species = inst.species.name
		level = inst.level

	return create_battle_pokemon(species, level, is_wild=True)


def generate_trainer_pokemon(trainer=None) -> Pokemon:
	"""Return a simple trainer-owned Charmander encounter."""

	return create_battle_pokemon("Charmander", 5, trainer=trainer, is_wild=False)


def owned_model_ref(model) -> str | None:
	return build_owned_ref(getattr(model, "unique_id", getattr(model, "model_id", None)))


__all__ = [
	"create_battle_pokemon",
	"generate_wild_pokemon",
	"generate_trainer_pokemon",
	"_calc_stats_from_model",
	"owned_model_ref",
]
