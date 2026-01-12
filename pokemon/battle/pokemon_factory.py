from __future__ import annotations

"""Helpers for creating battle-ready :class:`~pokemon.battle.battledata.Pokemon`.

This module centralises logic used to build temporary Pokémon used by the
battle engine. It is separated from ``battleinstance`` to keep that module
focused on session management.
"""

import random
import re

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

from pokemon.helpers.pokemon_spawn import get_spawn

from ..data.generation import generate_pokemon
from .battledata import Move, Pokemon


TRAINER_ENCOUNTERS: Dict[str, Any] = {
        "default": [
                {"species": "Charmander", "min_level": 5, "max_level": 6, "weight": 1},
                {"species": "Squirtle", "min_level": 5, "max_level": 6, "weight": 1},
                {"species": "Bulbasaur", "min_level": 5, "max_level": 6, "weight": 1},
        ],
        "locations": {
                "forest": [
                        {"species": "Caterpie", "min_level": 3, "max_level": 5, "weight": 3},
                        {"species": "Weedle", "min_level": 3, "max_level": 5, "weight": 2},
                        {"species": "Metapod", "min_level": 4, "max_level": 6, "weight": 1},
                ],
                "mountain": [
                        {"species": "Geodude", "min_level": 6, "max_level": 8, "weight": 2},
                        {"species": "Onix", "min_level": 8, "max_level": 10, "weight": 1},
                        {"species": "Machop", "min_level": 6, "max_level": 8, "weight": 1},
                ],
        },
        "archetypes": {
                "ace": [
                        {"species": "Pikachu", "min_level": 7, "max_level": 9, "weight": 1},
                        {"species": "Eevee", "min_level": 7, "max_level": 9, "weight": 1},
                ],
                "bug_catcher": [
                        {"species": "Paras", "min_level": 5, "max_level": 7, "weight": 1},
                        {"species": "Pinsir", "min_level": 7, "max_level": 9, "weight": 1},
                ],
        },
        "pairs": {
                ("forest", "bug_catcher"): [
                        {"species": "Venonat", "min_level": 6, "max_level": 8, "weight": 1},
                        {"species": "Beedrill", "min_level": 7, "max_level": 9, "weight": 1},
                ]
        },
}


def _normalize_key(value: Any) -> Optional[str]:
        """Return a lower-case key representation for ``value``."""

        if value is None:
                return None
        if isinstance(value, str):
                cleaned = value.strip().lower()
                if cleaned.startswith("#"):
                        cleaned = cleaned.lstrip("#")
                cleaned = re.sub(r"[\s\-]+", "_", cleaned)
                return cleaned or None
        for attr in ("key", "db_key", "dbref", "name"):
                attr_value = getattr(value, attr, None)
                if attr_value:
                        return _normalize_key(attr_value)
        representation = str(value).strip().lower()
        return representation or None


def _coerce_roster(entries: Any) -> List[Dict[str, Any]]:
        """Return a normalised list of trainer encounter entries."""

        if not entries:
                return []
        roster: List[Dict[str, Any]] = []
        for entry in entries:
                payload: Dict[str, Any]
                if isinstance(entry, Mapping):
                        species = entry.get("species") or entry.get("name")
                        if not species:
                                continue
                        payload = dict(entry)
                        payload["species"] = str(species)
                        min_level = payload.get("min_level", payload.get("level"))
                        payload["min_level"] = int(min_level or 1)
                        payload["max_level"] = int(payload.get("max_level", payload["min_level"]))
                        payload.setdefault("weight", 1)
                elif isinstance(entry, (list, tuple)):
                        if not entry:
                                continue
                        species = entry[0]
                        if not species:
                                continue
                        min_level = entry[1] if len(entry) > 1 else 1
                        max_level = entry[2] if len(entry) > 2 else min_level
                        payload = {
                                "species": str(species),
                                "min_level": int(min_level or 1),
                                "max_level": int(max_level or min_level or 1),
                                "weight": int(entry[3]) if len(entry) > 3 else 1,
                        }
                else:
                        continue
                if payload["max_level"] < payload["min_level"]:
                        payload["max_level"] = payload["min_level"]
                roster.append(payload)
        return roster


def _lookup_pair_roster(
        pairs: Mapping[Any, Iterable[Mapping[str, Any]]],
        location_key: Optional[str],
        archetype_key: Optional[str],
) -> List[Dict[str, Any]]:
        """Return roster for combined location/archetype keys."""

        if not pairs or not (location_key or archetype_key):
                return []
        for key, values in pairs.items():
                if isinstance(key, tuple):
                        normalised = tuple(_normalize_key(part) for part in key)
                        if len(normalised) == 2 and normalised == (location_key, archetype_key):
                                roster = _coerce_roster(values)
                                if roster:
                                        return roster
                else:
                        normalised = _normalize_key(key)
                        expected = ":".join(
                                part for part in (location_key, archetype_key) if part is not None
                        )
                        if normalised == expected and expected:
                                roster = _coerce_roster(values)
                                if roster:
                                        return roster
        return []


def _roster_from_context(trainer, context: Optional[MutableMapping[str, Any]]) -> List[Dict[str, Any]]:
        """Return the configured roster for ``trainer`` and ``context``."""

        context = context or {}
        for key in ("roster", "encounters", "table"):
                roster = _coerce_roster(context.get(key))
                if roster:
                        return roster

        # Trainer-provided rosters take precedence over global tables.
        for source in (trainer, getattr(trainer, "db", None)):
                if not source:
                        continue
                for attr in ("trainer_roster", "trainer_encounters", "encounters", "roster"):
                        roster = _coerce_roster(getattr(source, attr, None))
                        if roster:
                                return roster

        location_key = _normalize_key(context.get("location"))
        archetype_key = _normalize_key(context.get("archetype"))

        if location_key is None and trainer is not None:
                location_key = _normalize_key(getattr(trainer, "location", None))
        if archetype_key is None and trainer is not None:
                archetype_key = _normalize_key(getattr(trainer, "archetype", None)) or _normalize_key(
                        getattr(trainer, "trainer_archetype", None)
                )

        pairs = _lookup_pair_roster(TRAINER_ENCOUNTERS.get("pairs", {}), location_key, archetype_key)
        if pairs:
                return pairs

        if location_key:
                for key, values in (TRAINER_ENCOUNTERS.get("locations", {}) or {}).items():
                        if _normalize_key(key) == location_key:
                                roster = _coerce_roster(values)
                                if roster:
                                        return roster

        if archetype_key:
                for key, values in (TRAINER_ENCOUNTERS.get("archetypes", {}) or {}).items():
                        if _normalize_key(key) == archetype_key:
                                roster = _coerce_roster(values)
                                if roster:
                                        return roster

        return _coerce_roster(TRAINER_ENCOUNTERS.get("default"))


def _resolve_trainer_identifier(trainer, context: Optional[MutableMapping[str, Any]], entry: Mapping[str, Any]):
        """Return an identifier associated with the trainer encounter."""

        if trainer is not None:
                for attr in ("id", "dbid", "db_id", "pk", "unique_id"):
                        value = getattr(trainer, attr, None)
                        if value is not None:
                                return value
                dbref = getattr(trainer, "dbref", None)
                if dbref:
                        try:
                                return int(str(dbref).lstrip("#"))
                        except (TypeError, ValueError):
                                return str(dbref)

        context = context or {}
        for key in ("trainer_id", "trainer_identifier", "identifier", "id"):
                value = context.get(key)
                if value is not None:
                        return value

        parts = [
                _normalize_key(context.get("location")),
                _normalize_key(context.get("archetype")),
                _normalize_key(entry.get("species")),
        ]
        slug = ":".join(filter(None, parts))
        return slug or _normalize_key(entry.get("species"))


def _stat_list(source) -> List[int]:
	"""Return a 6-length list of stats from ``source``.

	``source`` may be ``None``, an object with stat attributes or an existing
	list. Missing values default to ``0``.
	"""
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
		inst = generate_pokemon(name, level=level)
		st = getattr(inst, "stats", inst)
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
) -> Pokemon:
	"""Return a ``Pokemon`` battle object for the given species/level."""

	try:
		from pokemon.helpers.pokemon_helpers import create_owned_pokemon
	except Exception:  # pragma: no cover - optional in tests
		create_owned_pokemon = None

	inst = generate_pokemon(species, level=level)
	move_names = getattr(inst, "moves", []) or ["Flail"]
	moves = [Move(name=m) for m in move_names]

	ivs_list = _stat_list(getattr(inst, "ivs", None))
	evs_list = _stat_list(getattr(inst, "evs", None))
	nature = getattr(inst, "nature", "Hardy")

	db_obj = None
	if create_owned_pokemon:
		try:
			db_obj = create_owned_pokemon(
				inst.species.name,
				None,
				inst.level,
				gender=getattr(inst, "gender", "N"),
				nature=nature,
				ability=getattr(inst, "ability", ""),
				ivs=ivs_list,
				evs=evs_list,
				ai_trainer=trainer,
				is_wild=is_wild,
			)
		except Exception:
			db_obj = None

		identifier = None
		if db_obj:
			identifier = getattr(db_obj, "unique_id", getattr(db_obj, "model_id", None))
		model_id = str(identifier) if identifier else None


		return Pokemon(
			name=inst.species.name,
			level=inst.level,
			hp=getattr(db_obj, "current_hp", getattr(inst.stats, "hp", level)),
			max_hp=getattr(inst.stats, "hp", level),
			moves=moves,
			ability=getattr(inst, "ability", None),
			ivs=ivs_list,
			evs=evs_list,
			nature=nature,
			model_id=model_id,
			gender=getattr(inst, "gender", "N"),
		)


def generate_wild_pokemon(location=None) -> Pokemon:
	"""Generate a wild Pokémon based on the supplied location."""

	inst = get_spawn(location) if location else None
	if not inst:
		species = "Pikachu"
		level = 5
	else:
		species = inst.species.name
		level = inst.level

	return create_battle_pokemon(species, level, is_wild=True)


def generate_trainer_pokemon(
        trainer=None,
        *,
        context: Optional[MutableMapping[str, Any]] = None,
        rng: Optional[random.Random] = None,
) -> Pokemon:
        """Return a trainer-owned Pokémon from configured encounter tables."""

        roster = _roster_from_context(trainer, context)
        if not roster:
                roster = [
                        {"species": "Charmander", "min_level": 5, "max_level": 5, "weight": 1},
                ]

        rng = rng or random
        weights = [entry.get("weight", 1) for entry in roster]
        selected = rng.choices(roster, weights=weights, k=1)[0]

        min_level = int(selected.get("min_level", selected.get("level", 1)) or 1)
        max_level = int(selected.get("max_level", min_level) or min_level or 1)
        if max_level < min_level:
                max_level = min_level

        level = rng.randint(min_level, max_level)

        pokemon = create_battle_pokemon(
                selected.get("species", "Charmander"),
                level,
                trainer=trainer,
                is_wild=False,
        )

        setattr(pokemon, "is_wild", False)

        identifier = _resolve_trainer_identifier(trainer, context, selected)
        if identifier is not None:
                if getattr(pokemon, "trainer_id", None) is None:
                        setattr(pokemon, "trainer_id", identifier)
                setattr(pokemon, "trainer_identifier", identifier)
                if getattr(pokemon, "ai_trainer_id", None) is None:
                        setattr(pokemon, "ai_trainer_id", identifier)

        if trainer is not None and getattr(pokemon, "trainer", None) is None:
                setattr(pokemon, "trainer", trainer)

        return pokemon


__all__ = [
	"create_battle_pokemon",
	"generate_wild_pokemon",
	"generate_trainer_pokemon",
	"_calc_stats_from_model",
]
