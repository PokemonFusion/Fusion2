"""Helper functions for working with Pokémon stats.

This module exposes convenience wrappers for calculating and caching a
Pokémon's stats.  Stats are expensive to compute, so we store the most
recently calculated values on the object itself and only recompute when
necessary.  ``refresh_stats`` can be used to force a recalculation when an
event occurs that would change the numbers (level up, EV gain, species
change, etc.).
"""

from pokemon.data.generation import generate_pokemon
from pokemon.services.move_management import learn_level_up_moves
from pokemon.utils.boosts import STAT_KEY_MAP


def _resolve_pokemon(pokemon):
        """Return a Pokémon model when given an identifier.

        Many helpers in this module accept either an :class:`OwnedPokemon`
        instance or its unique identifier.  This small utility attempts to
        resolve identifiers to model instances while gracefully handling
        missing database dependencies.  If resolution fails, ``pokemon`` is
        returned unchanged or ``None``.
        """

        if isinstance(pokemon, (str, bytes)):
                try:  # pragma: no cover - database access optional in tests
                        from pokemon.models.core import OwnedPokemon

                        return OwnedPokemon.objects.filter(unique_id=pokemon).first()
                except Exception:  # pragma: no cover - fallback when models unavailable
                        return None
        return pokemon


def calculate_stats(species, level, ivs, evs, nature):
        """Return calculated stats, falling back to generated data if needed."""

        try:  # pragma: no cover - heavy Django dependency
                from pokemon.models.stats import calculate_stats as _calc

                return _calc(species, level, ivs, evs, nature)
        except Exception:
                inst = generate_pokemon(species, level=level)
                return {
                        "hp": inst.stats.hp,
                        "attack": inst.stats.attack,
                        "defense": inst.stats.defense,
                        "special_attack": inst.stats.special_attack,
                        "special_defense": inst.stats.special_defense,
                        "speed": inst.stats.speed,
                }


def _calculate_from_data(pokemon):
        """Return freshly calculated stats based on stored attributes."""

        pokemon = _resolve_pokemon(pokemon)
        if pokemon is None:
                return {}

        ivs_attr = getattr(pokemon, "ivs", [0, 0, 0, 0, 0, 0])
        evs_attr = getattr(pokemon, "evs", [0, 0, 0, 0, 0, 0])
        if isinstance(ivs_attr, dict):
                ivs = {STAT_KEY_MAP.get(k, k): v for k, v in ivs_attr.items()}
                ivs = {stat: ivs.get(stat, 0) for stat in STAT_KEY_MAP.values()}
        else:
                ivs = {
                        "hp": ivs_attr[0],
                        "attack": ivs_attr[1],
                        "defense": ivs_attr[2],
                        "special_attack": ivs_attr[3],
                        "special_defense": ivs_attr[4],
                        "speed": ivs_attr[5],
                }
        if isinstance(evs_attr, dict):
                evs = {STAT_KEY_MAP.get(k, k): v for k, v in evs_attr.items()}
                evs = {stat: evs.get(stat, 0) for stat in STAT_KEY_MAP.values()}
        else:
                evs = {
                        "hp": evs_attr[0],
                        "attack": evs_attr[1],
                        "defense": evs_attr[2],
                        "special_attack": evs_attr[3],
                        "special_defense": evs_attr[4],
                        "speed": evs_attr[5],
                }
        nature = getattr(pokemon, "nature", "Hardy")
        species = getattr(pokemon, "species", getattr(pokemon, "name", ""))
        level = getattr(pokemon, "level", 1)
        return calculate_stats(species, level, ivs, evs, nature)


def _get_stats_from_data(pokemon):
        """Return cached calculated stats based on stored attributes."""

        pokemon = _resolve_pokemon(pokemon)
        if pokemon is None:
                return {}

        cache = getattr(pokemon, "_cached_stats", None)
        if cache is not None:
                return cache
        stats = _calculate_from_data(pokemon)
        setattr(pokemon, "_cached_stats", stats)
        return stats


def refresh_stats(pokemon):
	"""Recalculate and cache stats for ``pokemon``.

	This helper should be invoked whenever something happens that would
	alter a Pokémon's stats, such as level changes, EV gains or species
	changes.  It returns the newly computed stats dictionary.
	"""

	stats = _calculate_from_data(pokemon)
	setattr(pokemon, "_cached_stats", stats)
	return stats


def get_max_hp(pokemon) -> int:
	"""Return the calculated maximum HP for ``pokemon``."""
	stats = _get_stats_from_data(pokemon)
	return stats.get("hp", 0)


def get_stats(pokemon):
	"""Return a dict of calculated stats for ``pokemon``."""
	return _get_stats_from_data(pokemon)


def create_owned_pokemon(
	species: str,
	trainer,
	level: int,
	*,
	gender: str = "",
	ability: str = "",
	nature: str = "",
	ivs: list[int] | None = None,
	evs: list[int] | None = None,
	**extra_fields,
):
	"""Create and initialize an :class:`OwnedPokemon` instance.

	Parameters
	----------
	species:
	    Species name of the Pokémon to create.
	trainer:
	    Owning trainer or ``None`` for wild/AI-controlled Pokémon.
	level:
	    Initial level for the Pokémon.
	gender, ability, nature, ivs, evs:
	    Optional data used to seed model fields. ``ivs`` and ``evs`` default
	    to zeroed lists if not supplied.
	extra_fields:
	    Additional model fields passed directly to ``objects.create``.

	Returns
	-------
	OwnedPokemon
	    The fully initialised Pokémon model with level, health and moves set.
	"""

	from pokemon.models.core import OwnedPokemon

	ivs = ivs if ivs is not None else [0, 0, 0, 0, 0, 0]
	evs = evs if evs is not None else [0, 0, 0, 0, 0, 0]

	pokemon = OwnedPokemon.objects.create(
		trainer=trainer,
		species=species,
		nickname="",
		gender=gender,
		nature=nature,
		ability=ability,
		ivs=ivs,
		evs=evs,
		**extra_fields,
	)

	pokemon.set_level(level)
	pokemon.heal()
	try:
		learn_level_up_moves(pokemon)
	except Exception:  # pragma: no cover - helper optional in tests
		pass
	return pokemon
