from __future__ import annotations

"""Helpers for creating battle-ready :class:`~pokemon.battle.battledata.Pokemon`.

This module centralises logic used to build temporary Pokémon used by the
battle engine. It is separated from ``battleinstance`` to keep that module
focused on session management.
"""

from typing import List

from ..data.generation import generate_pokemon
from pokemon.helpers.pokemon_spawn import get_spawn
from .battledata import Pokemon, Move


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
        model_id=str(getattr(db_obj, "unique_id", "")) if db_obj else None,
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


def generate_trainer_pokemon(trainer=None) -> Pokemon:
    """Return a simple trainer-owned Charmander."""

    return create_battle_pokemon("Charmander", 5, trainer=trainer, is_wild=False)


__all__ = [
    "create_battle_pokemon",
    "generate_wild_pokemon",
    "generate_trainer_pokemon",
    "_calc_stats_from_model",
]
