from django.db import transaction
from typing import Any

try:
    from pokemon.models.core import OwnedPokemon
except Exception:  # pragma: no cover - optional in tests
    OwnedPokemon = None

try:
    from pokemon.battle.battledata import Pokemon, Move
except Exception:  # pragma: no cover - allow tests to stub
    Pokemon = Move = None


def _fallback_normalize_key(val: str) -> str:
    """Simplified key normalisation used when engine helpers are unavailable."""

    return val.replace(" ", "").replace("-", "").replace("'", "").lower()


try:
    from pokemon.dex import POKEDEX as _GLOBAL_POKEDEX  # type: ignore
except Exception:  # pragma: no cover - optional in tests
    _GLOBAL_POKEDEX = {}


def _get_calc_stats_from_model():
    try:
        from pokemon.battle import battleinstance as bi
        return getattr(bi, "_calc_stats_from_model", None)
    except Exception:  # pragma: no cover
        return None


def _get_create_battle_pokemon():
    try:
        from pokemon.battle import battleinstance as bi
        return getattr(bi, "create_battle_pokemon", None)
    except Exception:  # pragma: no cover
        return None


def clone_pokemon(pokemon: OwnedPokemon, for_ai: bool = True) -> OwnedPokemon:
    """Create a battle-only clone of ``pokemon``."""
    if OwnedPokemon is None:
        raise RuntimeError("OwnedPokemon model not available")

    with transaction.atomic():
        clone = OwnedPokemon.objects.create(
            species=pokemon.species,
            ability=pokemon.ability,
            nature=pokemon.nature,
            gender=pokemon.gender,
            ivs=list(pokemon.ivs),
            evs=list(pokemon.evs),
            held_item=pokemon.held_item,
            tera_type=pokemon.tera_type,
            total_exp=pokemon.total_exp,
            current_hp=pokemon.current_hp,
            is_battle_instance=True,
            ai_trainer=pokemon.ai_trainer if for_ai else None,
        )
        clone.learned_moves.set(pokemon.learned_moves.all())
        for ms in pokemon.movesets.all():
            new_set = clone.movesets.create(index=ms.index)
            for slot in ms.slots.all():
                new_set.slots.create(move=slot.move, slot=slot.slot)
            if pokemon.active_moveset and ms.index == pokemon.active_moveset.index:
                clone.active_moveset = new_set
        clone.save()
        for boost in getattr(pokemon, "pp_boosts", []).all() if hasattr(pokemon, "pp_boosts") else []:
            clone.pp_boosts.create(move=boost.move, bonus_pp=boost.bonus_pp)
        for slot in pokemon.activemoveslot_set.all():
            clone.activemoveslot_set.create(
                move=slot.move,
                slot=slot.slot,
                current_pp=slot.current_pp,
            )
        return clone


def build_battle_pokemon_from_model(model, *, full_heal: bool = False) -> Pokemon:
    """Return a battle-ready ``Pokemon`` object from a stored model."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")

    calc_stats = _get_calc_stats_from_model()
    stats = calc_stats(model) if calc_stats else {"hp": getattr(model, "current_hp", 1)}

    level = getattr(model, "computed_level", getattr(model, "level", 1))
    name = getattr(model, "name", getattr(model, "species", "Pikachu"))

    move_names = getattr(model, "moves", None) or []
    slots = getattr(model, "activemoveslot_set", None)
    if slots is None:
        active_ms = getattr(model, "active_moveset", None)
        if active_ms is not None:
            slots = getattr(active_ms, "slots", None)
    if not move_names and slots is not None:
        try:
            iterable = slots.all().order_by("slot")
        except Exception:
            try:
                iterable = slots.order_by("slot")
            except Exception:
                iterable = slots
        move_names = [getattr(s.move, "name", "") for s in iterable]
    if not move_names:
        if hasattr(model, "learned_moves"):
            try:
                move_names = [m.name for m in model.learned_moves.all()[:4]]
            except Exception:
                move_names = [m.name for m in model.learned_moves][:4]
    if not move_names:
        move_names = ["Flail"]

    moves = [Move(name=m) for m in move_names[:4]]

    current_hp = stats.get("hp", level)
    if not full_heal:
        current_hp = getattr(model, "current_hp", current_hp)

    ivs = getattr(model, "ivs", [0, 0, 0, 0, 0, 0])
    evs = getattr(model, "evs", [0, 0, 0, 0, 0, 0])
    nature = getattr(model, "nature", "Hardy")

    battle_poke = Pokemon(
        name=name,
        level=level,
        hp=current_hp,
        max_hp=stats.get("hp", getattr(model, "current_hp", level)),
        moves=moves,
        ability=getattr(model, "ability", None),
        ivs=ivs,
        evs=evs,
        nature=nature,
        model_id=str(
            getattr(model, "unique_id", getattr(model, "model_id", "")) or None
        ),
    )
    if slots is not None:
        battle_poke.activemoveslot_set = slots
    return battle_poke


def battle_pokemon_from_owned(pokemon: OwnedPokemon) -> Pokemon:
    """Create a battle-ready :class:`Pokemon` object from an ``OwnedPokemon``."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")
    return build_battle_pokemon_from_model(pokemon)


def spawn_npc_pokemon(trainer, *, use_templates: bool = True) -> Pokemon:
    """Return a battle-ready Pokémon for an NPC trainer."""

    if use_templates:
        qs = OwnedPokemon.objects.filter(ai_trainer=trainer, is_template=True)
        template = qs.order_by("unique_id").first() if hasattr(qs, "order_by") else (qs[0] if qs else None)
        if template:
            clone = clone_pokemon(template, for_ai=True)
            return battle_pokemon_from_owned(clone)

    create_poke = _get_create_battle_pokemon()
    if create_poke is None:
        raise RuntimeError("Battle modules not available")
    return create_poke("Charmander", 5, trainer=trainer, is_wild=False)


def make_pokemon_from_dict(data: dict) -> Pokemon:
    """Instantiate a :class:`~pokemon.battle.battledata.Pokemon` from a dictionary.

    Parameters
    ----------
    data:
        Mapping describing the Pokémon.  The structure is intentionally
        lightweight and mirrors the arguments of
        :class:`pokemon.battle.battledata.Pokemon`.  Example::

            {
                "name": "Pikachu",  # or ``"species"``
                "level": 5,
                "stats": {"hp": 35},
                "moves": [
                    {"name": "Thunderbolt", "priority": 0},
                    {"name": "Quick Attack"},
                ],
                "ability": "Static",
                "ivs": [31, 31, 31, 31, 31, 31],
                "evs": [0, 0, 0, 0, 0, 0],
                "nature": "Hardy",
            }

    Missing fields are replaced with sensible defaults: level defaults to 1,
    hit points default to ``100`` or the provided level, and an empty move list
    results in a single "Tackle" move.

    Returns
    -------
    Pokemon
        Newly created battle Pokémon instance.
    """

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")

    name = data.get("name") or data.get("species") or "Pikachu"
    level = int(data.get("level", 1))

    stats = data.get("stats", {})
    hp = data.get("current_hp", data.get("hp", stats.get("hp", level)))
    max_hp = data.get("max_hp", stats.get("hp", hp))

    moves: list[Move] = []
    for move_data in data.get("moves", [])[:4]:
        if isinstance(move_data, Move):
            moves.append(move_data)
            continue
        if isinstance(move_data, dict):
            mname = move_data.get("name", "Tackle")
            moves.append(Move(name=mname, priority=move_data.get("priority", 0)))
        else:
            moves.append(Move(name=str(move_data)))
    if not moves:
        moves = [Move(name="Tackle")]

    ability = data.get("ability")
    ivs = data.get("ivs")
    evs = data.get("evs")
    nature = data.get("nature", "Hardy")
    model_id = data.get("model_id")

    return Pokemon(
        name=name,
        level=level,
        hp=hp,
        max_hp=max_hp,
        moves=moves,
        ability=ability,
        ivs=ivs,
        evs=evs,
        nature=nature,
        model_id=model_id,
    )


def make_move_from_dex(name: str, *, battle: bool = False):
    """Instantiate a move definition from dex data.

    Parameters
    ----------
    name:
        Name of the move to look up.
    battle:
        When ``True`` a :class:`~pokemon.battle.engine.BattleMove` is returned
        with callable hooks attached.  Otherwise a display-only
        :class:`~pokemon.dex.entities.Move` is produced.  The function degrades
        gracefully when dex data is unavailable.
    """

    # Lazy imports to avoid requiring the full dex or battle engine in tests
    try:
        from pokemon import dex as dex_mod  # type: ignore
    except Exception:
        dex_mod = None
    try:
        from pokemon.battle.engine import _normalize_key
    except Exception:
        _normalize_key = _fallback_normalize_key

    entry = None
    key = _normalize_key(name)
    if dex_mod is not None:
        try:
            entry = dex_mod.MOVEDEX.get(key)
        except Exception:
            entry = None

    if not battle:
        # ``Move`` is a lightweight dex entity used primarily for display.  If
        # we have no dex information simply return a move with the provided
        # name so callers still receive an object with the expected interface.
        from pokemon.dex.entities import Move as DexMove

        if entry is None:
            return DexMove(name=name, num=0)
        return DexMove(name=getattr(entry, "name", name), num=getattr(entry, "num", 0))

    # Battle move path --------------------------------------------------
    from pokemon.battle.engine import BattleMove

    move_name = getattr(entry, "name", name)
    power = getattr(entry, "power", 0)
    accuracy = getattr(entry, "accuracy", 100)
    mtype = getattr(entry, "type", None)
    pp = getattr(entry, "pp", None)
    raw = dict(getattr(entry, "raw", {}) or {})

    # Ensure category information reaches the battle engine so that damage
    # uses the correct offensive and defensive stats.
    cat = getattr(entry, "category", None)
    if cat and "category" not in raw:
        raw["category"] = cat
    priority = raw.get("priority", 0)

    return BattleMove(
        name=move_name,
        key=key,
        power=power,
        accuracy=accuracy,
        priority=priority,
        onHit=raw.get("onHit"),
        onTry=raw.get("onTry"),
        onBeforeMove=raw.get("onBeforeMove"),
        onAfterMove=raw.get("onAfterMove"),
        basePowerCallback=raw.get("basePowerCallback"),
        type=mtype,
        raw=raw,
        pp=pp,
    )


def make_pokemon_from_dex(species: str, *, level: int = 1, moves=None):
    """Create a :class:`~pokemon.battle.battledata.Pokemon` from dex entries.

    The helper normalises the provided ``species`` key and builds a battle-ready
    Pokémon using :func:`make_pokemon_from_dict`.  Unknown species raise a
    :class:`KeyError` to match dictionary semantics.
    """

    try:
        from pokemon import dex as dex_mod  # type: ignore
    except Exception:
        dex_mod = None
    try:
        from pokemon.battle.engine import _normalize_key
    except Exception:
        _normalize_key = _fallback_normalize_key

    if Pokemon is None:
        raise RuntimeError("Dex not available")

    sp = None
    if dex_mod is not None and getattr(dex_mod, "POKEDEX", None):
        sp = dex_mod.POKEDEX.get(_normalize_key(species)) or dex_mod.POKEDEX.get(species)
    if sp is None:
        sp = _GLOBAL_POKEDEX.get(_normalize_key(species)) or _GLOBAL_POKEDEX.get(species)
    if sp is None:
        try:
            import importlib.util, sys
            from pathlib import Path

            spec = importlib.util.spec_from_file_location(
                "pokemon.dex", Path(__file__).resolve().parents[1] / "pokemon" / "dex" / "__init__.py"
            )
            if spec and spec.loader:
                real_dex = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = real_dex
                spec.loader.exec_module(real_dex)
                sp = real_dex.POKEDEX.get(_normalize_key(species)) or real_dex.POKEDEX.get(species)
        except Exception:
            sp = None
    if sp is None:
        raise KeyError(f"Unknown species '{species}'")

    move_objs = list(moves or [])
    stats = {"hp": getattr(getattr(sp, "base_stats", {}), "hp", 1)}
    data = {"species": sp.name, "level": level, "stats": stats, "moves": move_objs}
    return make_pokemon_from_dict(data)

