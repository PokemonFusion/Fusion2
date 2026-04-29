import sys
import logging

from django.db import transaction
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from pokemon.services.encounters import create_encounter_pokemon, encounter_ref
from pokemon.services.pokemon_refs import build_owned_ref

try:
    from pokemon.models.core import OwnedPokemon
except (ImportError, AppRegistryNotReady, ImproperlyConfigured):  # pragma: no cover - optional in tests
    OwnedPokemon = None

try:
    from pokemon.battle.battledata import Move, Pokemon
except ImportError:  # pragma: no cover - allow tests to stub
    Pokemon = Move = None

logger = logging.getLogger(__name__)


def _fallback_normalize_key(val: str) -> str:
    """Simplified key normalisation used when engine helpers are unavailable."""

    return val.replace(" ", "").replace("-", "").replace("'", "").lower()


try:
    from pokemon.dex import POKEDEX as _GLOBAL_POKEDEX  # type: ignore
except ImportError:  # pragma: no cover - optional in tests
    _GLOBAL_POKEDEX = {}


def _get_calc_stats_from_model():
    """Return the battle stat calculator if available.

    Tests often stub ``pokemon.battle.battleinstance`` directly into
    :mod:`sys.modules` without creating the full package hierarchy. Looking
    up the module via :data:`sys.modules` first avoids importing the real
    battle package which may have heavy dependencies.
    """

    bi = sys.modules.get("pokemon.battle.battleinstance")
    if bi is not None:
        return getattr(bi, "_calc_stats_from_model", None)
    try:  # pragma: no cover - fallback when running with real package
        from pokemon.battle import battleinstance as bi  # type: ignore

        return getattr(bi, "_calc_stats_from_model", None)
    except ImportError:  # pragma: no cover
        return None


def _get_create_battle_pokemon():
    """Return the battle Pokémon factory callable if available."""

    bi = sys.modules.get("pokemon.battle.battleinstance")
    if bi is not None:
        return getattr(bi, "create_battle_pokemon", None)
    try:  # pragma: no cover - fallback to importing real package
        from pokemon.battle import battleinstance as bi  # type: ignore

        return getattr(bi, "create_battle_pokemon", None)
    except ImportError:  # pragma: no cover
        return None


def build_battle_pokemon_from_model(model, *, full_heal: bool = False) -> Pokemon:
    """Return a battle-ready ``Pokemon`` object from a stored model."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")

    calc_stats = _get_calc_stats_from_model()
    if calc_stats:
        try:
            stats = calc_stats(model)
        except Exception:
            stats = {"hp": getattr(model, "max_hp", getattr(model, "current_hp", 1))}
    else:
        stats = {"hp": getattr(model, "current_hp", 1)}

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
        except AttributeError:
            try:
                iterable = slots.order_by("slot")
            except AttributeError:
                iterable = slots
        move_names = [getattr(s.move, "name", "") for s in iterable]
    if not move_names:
        if hasattr(model, "learned_moves"):
            try:
                move_names = [m.name for m in model.learned_moves.all()[:4]]
            except TypeError:
                move_names = [m.name for m in model.learned_moves][:4]
    if not move_names:
        move_names = ["Flail"]

    moves = [Move(name=m) for m in move_names[:4]]

    if full_heal:
        current_hp = stats.get("hp", level)
    else:
        stored_hp = getattr(model, "current_hp", None)
        if stored_hp is None:
            stored_hp = getattr(model, "hp", None)
        current_hp = stored_hp if stored_hp is not None else stats.get("hp", level)
    try:
        current_hp = int(current_hp)
    except (TypeError, ValueError):
        current_hp = stats.get("hp", level)

    max_hp = stats.get("hp")
    if max_hp is None:
        max_hp = getattr(model, "max_hp", None)
    if max_hp is None:
        max_hp = getattr(model, "current_hp", None)
    if max_hp is None:
        max_hp = getattr(model, "hp", level)
    try:
        max_hp = int(max_hp)
    except (TypeError, ValueError):
        max_hp = stats.get("hp", getattr(model, "current_hp", level))

    ivs = getattr(model, "ivs", [0, 0, 0, 0, 0, 0])
    evs = getattr(model, "evs", [0, 0, 0, 0, 0, 0])
    nature = getattr(model, "nature", "Hardy")

    model_id = build_owned_ref(getattr(model, "unique_id", getattr(model, "model_id", None)))

    battle_poke = Pokemon(
        name=name,
        level=level,
        hp=max(0, current_hp),
        max_hp=max_hp if max_hp is not None else current_hp,
        moves=moves,
        ability=getattr(model, "ability", None),
        ivs=ivs,
        evs=evs,
        nature=nature,
        model_id=model_id,
        gender=getattr(model, "gender", "N"),
    )
    if slots is not None:
        battle_poke.activemoveslot_set = slots
    return battle_poke


def grant_generated_pokemon(
    target,
    species: str,
    level: int,
    *,
    caller=None,
    item: str | None = None,
):
    """Generate, persist, and grant a Pokemon to ``target``."""

    from pokemon.data.generation import generate_pokemon
    from pokemon.helpers.pokemon_helpers import create_owned_pokemon

    instance = generate_pokemon(species, level=level)
    pokemon = create_owned_pokemon(
        instance.species.name,
        target.trainer,
        instance.level,
        gender=getattr(instance, "gender", "N"),
        nature=getattr(instance, "nature", ""),
        ability=getattr(instance, "ability", ""),
        ivs=[
            getattr(getattr(instance, "ivs", None), "hp", 0),
            getattr(getattr(instance, "ivs", None), "attack", 0),
            getattr(getattr(instance, "ivs", None), "defense", 0),
            getattr(getattr(instance, "ivs", None), "special_attack", 0),
            getattr(getattr(instance, "ivs", None), "special_defense", 0),
            getattr(getattr(instance, "ivs", None), "speed", 0),
        ],
        evs=[0, 0, 0, 0, 0, 0],
        held_item=item or "",
    )

    if item and hasattr(pokemon, "held_item"):
        pokemon.held_item = item
        if hasattr(pokemon, "save"):
            try:
                pokemon.save(update_fields=["held_item"])
            except Exception:
                try:
                    pokemon.save()
                except Exception:
                    logger.debug("Unable to persist held item on granted pokemon.", exc_info=True)

    target.storage.add_active_pokemon(pokemon)

    if caller is not None and hasattr(caller, "msg"):
        caller.msg(
            f"Gave {pokemon.species} (Lv {pokemon.computed_level}) to {target.key}."
        )
    if caller is not None and target != caller and hasattr(target, "msg"):
        target.msg(
            f"You received {pokemon.species} (Lv {pokemon.computed_level}) from {caller.key}."
        )

    return pokemon


def battle_pokemon_from_owned(pokemon: OwnedPokemon) -> Pokemon:
    """Create a battle-ready :class:`Pokemon` object from an ``OwnedPokemon``."""

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")
    return build_battle_pokemon_from_model(pokemon)


def spawn_npc_pokemon(trainer, *, use_templates: bool = True) -> Pokemon:
    """Return a battle-ready Pokémon for an NPC trainer."""

    if use_templates:
        try:
            from pokemon.models.trainer import NPCPokemonTemplate
        except Exception:  # pragma: no cover - optional in tests
            NPCPokemonTemplate = None
        qs = NPCPokemonTemplate.objects.filter(npc_trainer=trainer) if NPCPokemonTemplate else []
        template = qs.order_by("sort_order", "id").first() if hasattr(qs, "order_by") else (qs[0] if qs else None)
        if template:
            encounter = create_encounter_pokemon(
                species=template.species,
                level=template.level,
                source_kind="npc",
                gender=template.gender,
                nature=template.nature,
                ability=template.ability,
                ivs=list(template.ivs),
                evs=list(template.evs),
                held_item=template.held_item,
                move_names=list(template.move_names or []),
                npc_trainer=trainer,
                template_key=template.template_key,
            )
            if Pokemon is None:
                raise RuntimeError("Battle modules not available")
            moves = [Move(name=name) for name in list(template.move_names or [])[:4]] or [Move(name="Tackle")]
            hp = getattr(encounter, "current_hp", 20) or 20
            return Pokemon(
                name=template.species,
                level=template.level,
                hp=hp,
                max_hp=hp,
                moves=moves,
                ability=template.ability,
                ivs=list(template.ivs),
                evs=list(template.evs),
                nature=template.nature or "Hardy",
                model_id=encounter_ref(encounter),
                gender=template.gender or "N",
                item=template.held_item,
            )

    create_poke = _get_create_battle_pokemon()
    if create_poke is not None:
        return create_poke("Charmander", 5, trainer=trainer, is_wild=False)

    if Pokemon is None:
        raise RuntimeError("Battle modules not available")
    return Pokemon(name="Charmander", level=5, hp=20, max_hp=20, moves=[Move(name="Tackle")])


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
    gender = data.get("gender", "N")

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
        gender=gender,
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
    except ImportError:  # boundary: optional dex module
        dex_mod = None
    try:
        from pokemon.battle.engine import _normalize_key
    except ImportError:
        _normalize_key = _fallback_normalize_key

    entry = None
    key = _normalize_key(name)
    if dex_mod is not None:
        try:
            entry = dex_mod.MOVEDEX.get(key)
        except AttributeError:
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

    # In battle contexts we defer to the calling code to supply the current PP
    # for a move so that deductions affect the Pokémon rather than this
    # instance.  As such the ``pp`` value is omitted from the returned
    # :class:`BattleMove` and any remaining power points must be provided
    # separately when an action is declared.
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
        pp=None,
    )


def make_pokemon_from_dex(species: str, *, level: int = 1, moves=None):
    """Create a :class:`~pokemon.battle.battledata.Pokemon` from dex entries.

    The helper normalises the provided ``species`` key and builds a battle-ready
    Pokémon using :func:`make_pokemon_from_dict`.  Unknown species raise a
    :class:`KeyError` to match dictionary semantics.
    """

    try:
        from pokemon import dex as dex_mod  # type: ignore
    except ImportError:  # boundary: optional dex module
        dex_mod = None
    try:
        from pokemon.battle.engine import _normalize_key
    except ImportError:
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
            import importlib.util
            import sys
            from pathlib import Path

            spec = importlib.util.spec_from_file_location(
                "pokemon.dex", Path(__file__).resolve().parents[1] / "pokemon" / "dex" / "__init__.py"
            )
            if spec and spec.loader:
                real_dex = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = real_dex
                spec.loader.exec_module(real_dex)
                sp = real_dex.POKEDEX.get(_normalize_key(species)) or real_dex.POKEDEX.get(species)
        except (ImportError, AttributeError):
            logger.debug("Unable to lazy-load dex module for species lookup.", exc_info=True)
            sp = None
    if sp is None:
        raise KeyError(f"Unknown species '{species}'")

    move_objs = list(moves or [])
    stats = {"hp": getattr(getattr(sp, "base_stats", {}), "hp", 1)}
    data = {"species": sp.name, "level": level, "stats": stats, "moves": move_objs}
    return make_pokemon_from_dict(data)
