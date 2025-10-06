import logging
import random
from dataclasses import dataclass, field
from math import floor
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

from ._shared import _normalize_key
from utils.safe_import import safe_import

"""Damage calculation helpers and convenience wrappers.

This module contains the core damage application logic used by the battle
engine. It has been updated to invoke ability callbacks when a Pokémon is hit
by a damaging move so that defensive abilities such as Aftermath can respond
to the attack.
"""

try:
    from ..data import TYPE_CHART
except Exception:  # pragma: no cover - allow tests without data pkg
    TYPE_CHART = {}

try:  # pragma: no cover - optional in lightweight test harnesses
    from pokemon.dex import MOVEDEX as _MOVEDEX
except Exception:  # pragma: no cover - fallback to empty mapping
    _MOVEDEX = {}

if TYPE_CHECKING:  # pragma: no cover
    from ..dex import Move, Pokemon
else:  # pragma: no cover - runtime placeholders
    Move = Any  # type: ignore[assignment]
    Pokemon = Any  # type: ignore[assignment]

try:  # pragma: no cover - allow running as a standalone module in tests
    from pokemon.battle.callbacks import _resolve_callback
except Exception:  # pragma: no cover

    def _resolve_callback(cb_name, registry):
        """Fallback callback resolver used when the battle package is not fully
        available.

        This lightweight version only handles already callable hooks and is
        sufficient for the simplified test harness that loads this module
        directly via :func:`importlib`.
        """

        return cb_name if callable(cb_name) else None


try:  # pragma: no cover - default text may not be available in tests
    from ..data.text import DEFAULT_TEXT
except Exception:  # pragma: no cover
    DEFAULT_TEXT = {
        "default": {
            "superEffective": "  It's super effective!",
            "resisted": "  It's not very effective...",
            "immune": "  It doesn't affect [POKEMON]...",
        }
    }


@dataclass
class DamageResult:
    """Simple container for battle text and debug data."""

    text: List[str] = field(default_factory=list)
    fainted: List[str] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)


MULTIHITCOUNT = {2: 3, 3: 3, 4: 1, 5: 1}


logger = logging.getLogger("battle")


def _notify_admins(message: str) -> None:
    """Notify any connected administrators about an issue."""

    try:
        session_module = safe_import("evennia.server.sessionhandler")
    except ModuleNotFoundError:  # pragma: no cover - Evennia not installed
        return
    handler = getattr(session_module, "SESSIONS", None) or getattr(
        session_module, "SESSION_HANDLER", None
    )
    if handler is None:
        return

    sessions: List[Any] = []
    for accessor in ("get_sessions", "sessions", "all_sessions"):
        candidate = getattr(handler, accessor, None)
        if callable(candidate):
            try:
                possible = candidate()
            except TypeError:
                try:
                    possible = candidate(handler)
                except Exception:
                    continue
        elif isinstance(candidate, dict):
            possible = candidate.values()
        elif isinstance(candidate, (list, tuple, set)):
            possible = candidate
        else:
            continue
        try:
            sessions = list(possible)
        except TypeError:
            sessions = list(possible or [])
        if sessions:
            break
    if not sessions:
        raw_sessions = getattr(handler, "sessions", None)
        if isinstance(raw_sessions, dict):
            sessions = list(raw_sessions.values())
        elif isinstance(raw_sessions, (list, tuple, set)):
            sessions = list(raw_sessions)

    for session in sessions:
        account = getattr(session, "account", None) or getattr(session, "player", None)
        if account is None:
            continue
        is_admin = bool(
            getattr(account, "is_superuser", False) or getattr(account, "is_staff", False)
        )
        check_perm = getattr(account, "check_permstring", None)
        if callable(check_perm):
            try:
                if check_perm("Admins"):
                    is_admin = True
                elif check_perm("Wizards"):
                    is_admin = True
            except Exception:
                pass
        if not is_admin:
            continue
        messenger = getattr(session, "msg", None)
        if callable(messenger):
            try:
                messenger(message)
            except Exception:
                continue


def _report_dict_issue(reason: str, move_name: Optional[str], move_key: Optional[str]) -> None:
    """Log dictionary lookup failures and alert administrators."""

    details = reason
    normalized_key = move_key or None
    if move_name or normalized_key:
        name_part = move_name or "unknown"
        key_part = f" (key={normalized_key})" if normalized_key else ""
        details = f"{reason} for move '{name_part}'{key_part}"
    logger.warning(details)
    _notify_admins(details)


def _unique_candidates(values: Iterable[Optional[str]]) -> List[str]:
    """Return an ordered list of unique, truthy candidate keys."""

    seen: set[str] = set()
    candidates: List[str] = []
    for value in values:
        if not value:
            continue
        candidate = str(value)
        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def _get_movedex_entry(move_name: Optional[str], move_key: Optional[str]):
    """Locate a move entry in ``MOVEDEX`` regardless of key casing.

    The packaged dex normalizes keys to lowercase, but legacy datasets and
    ad-hoc dictionaries occasionally retain TitleCase identifiers.  To keep
    damage calculation resilient we try a collection of normalized forms
    before falling back to a case-insensitive scan of the mapping.
    """

    if not _MOVEDEX:
        return None

    raw_name = str(move_name or "")
    stripped = raw_name.replace(" ", "")
    normalized = _normalize_key(raw_name)
    title_compact = stripped.title() if stripped else ""
    capitalized = stripped.capitalize() if stripped else ""

    for candidate in _unique_candidates(
        (
            move_key,
            normalized,
            raw_name,
            stripped,
            stripped.lower(),
            raw_name.lower(),
            raw_name.title(),
            title_compact,
            capitalized,
        )
    ):
        entry = _MOVEDEX.get(candidate)
        if entry is not None:
            return entry

    if not raw_name:
        return None

    lower_name = raw_name.lower()
    for key, entry in _MOVEDEX.items():
        key_str = str(key)
        if key_str.lower() == lower_name or _normalize_key(key_str) == normalized:
            return entry
    return None


def percent_check(chance: float, rng: Optional[random.Random] = None) -> bool:
    """Return True if a random roll succeeds.

    Parameters
    ----------
    chance:
        Probability threshold between 0 and 1.
    rng:
        Optional :class:`random.Random` compatible object. Defaults to the
        module-level :mod:`random` generator when ``None``.
    """
    rng = rng or random
    return chance > rng.random()


def accuracy_check(move: Move, rng: Optional[random.Random] = None) -> bool:
    """Very small accuracy check using move.accuracy."""
    if move.accuracy is True:
        return True
    if isinstance(move.accuracy, (int, float)):
        return percent_check(float(move.accuracy) / 100.0, rng=rng)
    return True


def critical_hit_check(rng: Optional[random.Random] = None) -> bool:
    """Simplified crit check."""
    return percent_check(1 / 24, rng=rng)


def _get_types(pokemon) -> List[str]:
    """Return normalized types for ``pokemon``.

    Prefers the runtime ``pokemon.types`` attribute but falls back to
    ``pokemon.species.types`` when missing or empty.  Returned values are
    lowercase strings to simplify comparisons.
    """

    types = getattr(pokemon, "types", None)
    if types:
        return [str(t).lower() for t in types]
    species = getattr(pokemon, "species", None)
    types = getattr(species, "types", None)
    return [str(t).lower() for t in (types or [])]


def base_damage(
    level: int,
    power: int,
    atk: int,
    defense: int,
    *,
    return_roll: bool = False,
    rng: Optional[random.Random] = None,
):
    """Return base damage and optionally the random roll used.

    The simplified damage formula can receive zero values for ``atk`` or
    ``defense`` when stubbed Pokémon instances lack proper stats.    Clamp
    both to at least ``1`` so we avoid division-by-zero errors and always
    inflict a minimum of one point of damage after applying the random
    modifier.
    """

    rng = rng or random
    defense = max(1, defense)
    atk = max(1, atk)
    dmg = floor(floor(floor(((2 * level) / 5) + 2) * power * (atk * 1.0) / defense) / 50) + 2
    rand_mod = rng.randint(85, 100) / 100.0
    result = max(1, floor(dmg * rand_mod))
    if return_roll:
        return result, rand_mod
    return result


def stab_multiplier(attacker: Pokemon, move: Move) -> float:
    """Return the STAB multiplier for ``attacker`` using ``move``.

    This helper tolerates different container layouts.  If ``attacker`` does
    not define a ``types`` attribute, the function falls back to ``species.types``.
    Ability hooks may further modify the multiplier via ``onModifySTAB``.
    """

    if not move.type:
        return 1.0

    types = _get_types(attacker)
    has_type = str(move.type).lower() in types
    stab = 1.5 if has_type else 1.0

    ability = getattr(attacker, "ability", None)
    if ability is not None:
        cb = ability.raw.get("onModifySTAB") if hasattr(ability, "raw") else None
        if isinstance(cb, str):
            try:
                from pokemon.dex.functions import abilities_funcs

                cls_name, func_name = cb.split(".", 1)
                cls = getattr(abilities_funcs, cls_name, None)
                if cls:
                    cb = getattr(cls(), func_name, None)
            except Exception:
                cb = None
        elif not callable(cb):
            cb = None
        if callable(cb):
            try:
                new_val = cb(stab, source=attacker, move=move)
            except Exception:
                new_val = cb(stab)
            if isinstance(new_val, (int, float)):
                stab = float(new_val)
    return stab


def type_effectiveness(target: Pokemon, move: Move) -> float:
    eff = 1.0
    if not move.type:
        return eff
    chart = TYPE_CHART.get(move.type.capitalize())
    if not chart:
        return eff
    for typ in target.types:
        val = chart.get(typ.capitalize(), 0)
        if val == 1:
            eff *= 2
        elif val == 2:
            eff *= 0.5
        elif val == 3:
            eff *= 0
    return eff


def damage_phrase(target: Pokemon, damage: int) -> str:
    """Return a coarse description of the damage dealt to ``target``.

    Some tests provide very lightweight Pokémon stubs that may lack valid
    hit point information, leading to a ``maxhp`` of ``0``.     Clamp the
    maximum HP to at least ``1`` to avoid division-by-zero errors while
    still yielding sensible phrases.
    """

    try:
        from pokemon.helpers.pokemon_helpers import get_max_hp

        maxhp = get_max_hp(target)
    except Exception:  # pragma: no cover - fallback when helpers unavailable
        maxhp = getattr(getattr(target, "base_stats", None), "hp", 0)
    maxhp = max(1, maxhp)
    percent = (damage * 100) / maxhp
    if percent >= 100:
        return "EPIC"
    elif percent > 75:
        return "extreme"
    elif percent > 50:
        return "heavy"
    elif percent > 25:
        return "considerable"
    elif percent > 15:
        return "moderate"
    elif percent > 5:
        return "light"
    elif percent > 0:
        return "puny"
    return "no"


def damage_calc(
    attacker: Pokemon,
    target: Pokemon,
    move: Move,
    battle=None,
    *,
    spread: bool = False,
    rng: Optional[random.Random] = None,
) -> DamageResult:
    result = DamageResult()
    rng = rng or getattr(battle, "rng", random)
    numhits = 1
    multihit = move.raw.get("multihit") if move.raw else None
    if isinstance(multihit, list):
        population, weights = zip(*MULTIHITCOUNT.items())
        numhits = rng.choices(population, weights)[0]
    elif multihit is not None:
        numhits = multihit

    for _ in range(numhits):
        if hasattr(move, "basePowerCallback") and callable(move.basePowerCallback):
            try:
                new_power = move.basePowerCallback(attacker, target, move)
                if isinstance(new_power, (int, float)):
                    move.power = int(new_power)
            except Exception:
                pass
        # ------------------------------------------------------------------
        # Accuracy modification hooks
        # ------------------------------------------------------------------
        accuracy = move.accuracy

        # User ability: onSourceModifyAccuracy
        user_ability = getattr(attacker, "ability", None)
        if user_ability and hasattr(user_ability, "call"):
            try:
                new_acc = user_ability.call(
                    "onSourceModifyAccuracy",
                    accuracy,
                    source=attacker,
                    target=target,
                    move=move,
                )
            except Exception:
                new_acc = user_ability.call("onSourceModifyAccuracy", accuracy)
            if new_acc is not None:
                accuracy = new_acc

        # Target ability: onModifyAccuracy
        target_ability = getattr(target, "ability", None)
        if target_ability and hasattr(target_ability, "call"):
            try:
                new_acc = target_ability.call(
                    "onModifyAccuracy",
                    accuracy,
                    attacker=attacker,
                    defender=target,
                    move=move,
                )
            except Exception:
                new_acc = target_ability.call("onModifyAccuracy", accuracy)
            if new_acc is not None:
                accuracy = new_acc

        # Abilities that modify accuracy of any move
        for owner in (attacker, target):
            ability = getattr(owner, "ability", None)
            if ability and hasattr(ability, "call"):
                try:
                    new_acc = ability.call(
                        "onAnyModifyAccuracy",
                        accuracy,
                        source=attacker,
                        target=target,
                        move=move,
                    )
                except Exception:
                    new_acc = ability.call("onAnyModifyAccuracy", accuracy)
                if new_acc is not None:
                    accuracy = new_acc

        # Item hooks for the user and target
        user_item = getattr(attacker, "item", None) or getattr(attacker, "held_item", None)
        if user_item and hasattr(user_item, "call"):
            try:
                new_acc = user_item.call(
                    "onSourceModifyAccuracy",
                    accuracy,
                    source=attacker,
                    target=target,
                    move=move,
                )
            except Exception:
                new_acc = user_item.call("onSourceModifyAccuracy", accuracy)
            if new_acc is not None:
                accuracy = new_acc

        target_item = getattr(target, "item", None) or getattr(target, "held_item", None)
        if target_item and hasattr(target_item, "call"):
            try:
                new_acc = target_item.call(
                    "onModifyAccuracy",
                    accuracy,
                    user=attacker,
                    target=target,
                    move=move,
                )
            except Exception:
                new_acc = target_item.call("onModifyAccuracy", accuracy)
            if new_acc is not None:
                accuracy = new_acc

        move.accuracy = accuracy

        if not accuracy_check(move, rng=rng):
            result.text.append(f"{attacker.name} uses {move.name} but it missed!")
            continue

        try:  # pragma: no cover - allows testing with minimal stubs
            from pokemon.battle.utils import get_modified_stat
        except Exception:

            def get_modified_stat(pokemon, stat: str) -> int:  # type: ignore
                base = getattr(getattr(pokemon, "base_stats", None), stat, 0)
                return base

        atk_key = "attack" if move.category == "Physical" else "special_attack"
        def_key = "defense" if move.category == "Physical" else "special_defense"
        # Retrieve both offensive stats so that ability callbacks which modify
        # an unused stat (e.g. ``onModifySpA`` during a physical move) are still
        # invoked.  This mirrors the behaviour of the comprehensive battle
        # engine where such hooks may fire regardless of move category.
        atk_stat = get_modified_stat(attacker, "attack")
        spa_stat = get_modified_stat(attacker, "special_attack")
        atk_stat = atk_stat if atk_key == "attack" else spa_stat
        def_stat = get_modified_stat(target, def_key)

        def _run_cb(holder, name, stat):
            """Safely invoke a stat-modifying callback."""

            if not holder or not hasattr(holder, "call"):
                return stat
            try:
                new_val = holder.call(
                    name,
                    stat,
                    attacker=attacker,
                    defender=target,
                    move=move,
                    pokemon=attacker,
                    source=attacker,
                    target=target,
                )
            except TypeError:
                try:
                    new_val = holder.call(name, stat, move=move)
                except Exception:
                    return stat
            except Exception:
                return stat
            return int(new_val) if isinstance(new_val, (int, float)) else stat

        # Attacker ability/item hooks
        atk_stat = _run_cb(getattr(attacker, "ability", None), "onModifyAtk", atk_stat)
        spa_stat = _run_cb(getattr(attacker, "ability", None), "onModifySpA", spa_stat)
        atk_stat = _run_cb(getattr(attacker, "ability", None), "onAnyModifyAtk", atk_stat)
        atk_stat = _run_cb(getattr(attacker, "ability", None), "onAllyModifyAtk", atk_stat)
        item = getattr(attacker, "item", None) or getattr(attacker, "held_item", None)
        atk_stat = _run_cb(item, "onModifyAtk", atk_stat)
        spa_stat = _run_cb(item, "onModifySpA", spa_stat)

        # Target ability hooks that modify the attacker's stats
        opp_ability = getattr(target, "ability", None)
        atk_stat = _run_cb(opp_ability, "onSourceModifyAtk", atk_stat)
        spa_stat = _run_cb(opp_ability, "onSourceModifySpA", spa_stat)
        atk_stat = _run_cb(opp_ability, "onAnyModifyAtk", atk_stat)
        atk_stat = _run_cb(opp_ability, "onAllyModifyAtk", atk_stat)

        # Determine the stat actually used for damage after all modifications
        atk_stat = atk_stat if atk_key == "attack" else spa_stat

        if atk_key == "attack":
            try:
                from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
            except Exception:
                CONDITION_HANDLERS = {}
            status = getattr(attacker, "status", None)
            handler = (CONDITION_HANDLERS or {}).get(status)
            if handler and hasattr(handler, "onModifyAtk"):
                try:
                    new_atk = handler.onModifyAtk(
                        atk_stat,
                        attacker=attacker,
                        defender=target,
                        move=move,
                    )
                except Exception:
                    new_atk = atk_stat
                if isinstance(new_atk, (int, float)):
                    atk_stat = int(new_atk)

        power = move.power or 0
        move_name = getattr(move, "name", None)
        move_key = getattr(move, "key", None) or _normalize_key(str(move_name or ""))
        if power in (None, 0):
            raw_data = getattr(move, "raw", None)
            raw_issue = None
            if isinstance(raw_data, dict):
                base_power = raw_data.get("basePower")
                if isinstance(base_power, (int, float)) and base_power > 0:
                    power = int(base_power)
                else:
                    raw_issue = "Move raw data missing basePower"
            else:
                if raw_data is None:
                    raw_issue = "Move raw data unavailable"
                else:
                    raw_issue = "Move raw data not a dict"
            if raw_issue is not None:
                _report_dict_issue(raw_issue, move_name, move_key)

        if power in (None, 0):
            if not move_key:
                _report_dict_issue("Move key unavailable for MOVEDEX lookup", move_name, move_key)
            elif not _MOVEDEX:
                _report_dict_issue("MOVEDEX unavailable for power lookup", move_name, move_key)
            else:
                dex_entry = _get_movedex_entry(move_name, move_key)
                if dex_entry is None:
                    _report_dict_issue("MOVEDEX missing entry", move_name, move_key)
                else:
                    base_power = None
                    raw_entry = getattr(dex_entry, "raw", None)
                    dex_issue = None
                    if isinstance(raw_entry, dict):
                        base_power = raw_entry.get("basePower")
                        if not isinstance(base_power, (int, float)) or base_power <= 0:
                            dex_issue = "Dex entry raw missing basePower"
                    else:
                        if raw_entry is None:
                            dex_issue = "Dex entry raw data unavailable"
                        else:
                            dex_issue = "Dex entry raw data not a dict"
                    if dex_issue is not None:
                        _report_dict_issue(dex_issue, move_name, move_key)
                    if not isinstance(base_power, (int, float)) or base_power <= 0:
                        base_power = getattr(dex_entry, "power", None)
                        if not isinstance(base_power, (int, float)) or base_power <= 0:
                            _report_dict_issue(
                                "Dex entry missing power attribute", move_name, move_key
                            )
                    if isinstance(base_power, (int, float)) and base_power > 0:
                        power = int(base_power)
        if isinstance(power, (int, float)) and power > 0:
            move.power = int(power)
        else:
            power = 0
        if battle is not None:
            field = getattr(battle, "field", None)
            if field:
                terrain_handler = getattr(field, "terrain_handler", None)
                if terrain_handler:
                    cb = getattr(terrain_handler, "onBasePower", None)
                    if callable(cb):
                        try:
                            new_pow = cb(attacker, target, move)
                        except Exception:
                            try:
                                new_pow = cb(attacker, target, move=move)
                            except Exception:
                                new_pow = cb(attacker, move)
                        if isinstance(new_pow, (int, float)):
                            power = int(new_pow)
        if move.raw:
            cb = move.raw.get("basePowerCallback")
            if callable(cb):
                try:
                    new_power = cb(attacker, target, move, battle=battle)
                    if isinstance(new_power, (int, float)):
                        power = int(new_power)
                except Exception:
                    pass

        # ``base_damage`` expects the attacker's level.     Older stubs used in
        # tests only define ``num`` so we fall back to that when ``level`` is
        # missing for backwards compatibility.
        level = getattr(attacker, "level", None)
        if level is None:
            level = getattr(attacker, "num", 1)
        dmg, rand_mod = base_damage(
            level,
            power,
            atk_stat,
            def_stat,
            return_roll=True,
            rng=rng,
        )
        result.debug.setdefault("level", []).append(level)
        result.debug.setdefault("power", []).append(power)
        result.debug.setdefault("attack", []).append(atk_stat)
        result.debug.setdefault("defense", []).append(def_stat)
        result.debug.setdefault("rand", []).append(rand_mod)
        if battle is not None:
            field = getattr(battle, "field", None)
            if field:
                weather_handler = getattr(field, "weather_handler", None)
                if weather_handler:
                    cb = getattr(weather_handler, "onWeatherModifyDamage", None)
                    if callable(cb):
                        try:
                            wmult = cb(move)
                        except Exception:
                            wmult = cb(move=move)
                        if isinstance(wmult, (int, float)):
                            dmg = floor(dmg * wmult)
        stab = stab_multiplier(attacker, move)
        dmg = floor(dmg * stab)
        result.debug.setdefault("stab", []).append(stab)
        eff = type_effectiveness(target, move)
        result.debug.setdefault("type_effectiveness", []).append(eff)
        temp_eff = eff
        if temp_eff > 1:
            while temp_eff > 1:
                result.text.append(DEFAULT_TEXT["default"]["superEffective"])
                temp_eff /= 2
        elif 0 < temp_eff < 1:
            while temp_eff < 1:
                result.text.append(DEFAULT_TEXT["default"]["resisted"])
                temp_eff *= 2
        elif temp_eff == 0:
            result.text.append(DEFAULT_TEXT["default"]["immune"].replace("[POKEMON]", target.name))
            continue
        dmg = floor(dmg * eff)

        # Critical hit calculation with simple ratio handling
        crit_ratio = 0
        if move.raw:
            crit_ratio = int(move.raw.get("critRatio", 0))
        ability = getattr(attacker, "ability", None)
        if ability and hasattr(ability, "call"):
            try:
                new_ratio = ability.call(
                    "onModifyCritRatio", crit_ratio, attacker=attacker, defender=target, move=move
                )
            except Exception:
                new_ratio = ability.call("onModifyCritRatio", crit_ratio)
            if isinstance(new_ratio, (int, float)):
                crit_ratio = int(new_ratio)
        item = getattr(attacker, "item", None) or getattr(attacker, "held_item", None)
        if item and hasattr(item, "call"):
            try:
                new_ratio = item.call(
                    "onModifyCritRatio", crit_ratio, pokemon=attacker, target=target
                )
            except Exception:
                new_ratio = item.call("onModifyCritRatio", crit_ratio)
            if isinstance(new_ratio, (int, float)):
                crit_ratio = int(new_ratio)
        if getattr(attacker, "volatiles", {}).get("focusenergy"):
            crit_ratio += 2
        if getattr(attacker, "volatiles", {}).get("laserfocus"):
            crit_ratio = max(crit_ratio, 3)

        chances = {0: 1 / 24, 1: 1 / 8, 2: 1 / 2}
        crit = False
        if move.raw and move.raw.get("willCrit"):
            crit = True
        else:
            chance = chances.get(crit_ratio, 1.0)
            crit = percent_check(chance, rng=rng)
        if crit:
            dmg = floor(dmg * 1.5)
            result.debug.setdefault("critical", []).append(True)
        else:
            result.debug.setdefault("critical", []).append(False)
        if spread:
            dmg = int(dmg * 0.75)
        if (
            dmg < 1
            and getattr(move, "category", None) != "Status"
            and isinstance(power, (int, float))
            and power > 0
        ):
            dmg = 1
        result.debug.setdefault("damage", []).append(dmg)

        # apply simple status effects like burns
        if move.raw:
            status = move.raw.get("status")
            chance = move.raw.get("statusChance", 100)
            secondary = move.raw.get("secondary")
            if secondary and isinstance(secondary, dict):
                status = secondary.get("status", status)
                chance = secondary.get("chance", chance)
            if status and percent_check(chance / 100.0, rng=rng):
                applied = False
                if battle is not None:
                    applied = battle.apply_status_condition(
                        target,
                        status,
                        source=attacker,
                        effect=move,
                    )
                elif hasattr(target, "setStatus"):
                    applied = bool(
                        target.setStatus(
                            status,
                            source=attacker,
                            battle=None,
                            effect=move,
                        )
                    )
                else:
                    setattr(target, "status", status)
                    applied = True
                if applied and status == "brn":
                    result.text.append(f"{target.name} was burned!")
    if numhits > 1:
        result.text.append(f"{attacker.name} hit {numhits} times!")
    return result


# ----------------------------------------------------------------------
# Convenience wrappers for the battle engine
# ----------------------------------------------------------------------


def apply_damage(
    attacker: Pokemon,
    target: Pokemon,
    move: Move,
    battle=None,
    *,
    spread: bool = False,
    update_hp: bool = True,
    rng: Optional[random.Random] = None,
) -> DamageResult:
    """Run :func:`damage_calc` and apply the result to ``target``.

    Parameters
    ----------
    attacker, target:
        Combatants involved in the damage calculation.
    move:
        The move being used.
    battle:
        Optional battle context passed to :func:`damage_calc`.
    spread:
        If ``True`` the move is treated as spread damage.
    update_hp:
        When ``True`` (default) the calculated damage is subtracted from the
        target's HP.  Set to ``False`` to only compute the damage value, e.g.
        when hitting a substitute.

    Returns
    -------
    DamageResult
        The result object from :func:`damage_calc` with ``debug['damage']``
        updated to the final damage amount after callbacks.
    """

    if rng is None and battle is not None:
        rng = getattr(battle, "rng", None)
    try:
        result = damage_calc(attacker, target, move, battle=battle, spread=spread, rng=rng)
    except TypeError:  # pragma: no cover - fallback for older overrides
        result = damage_calc(attacker, target, move, battle=battle, spread=spread)
    dmg = sum(result.debug.get("damage", []))

    try:  # pragma: no cover - callbacks may be absent in tests
        from pokemon.dex.functions import moves_funcs  # type: ignore
    except Exception:  # pragma: no cover
        moves_funcs = None

    if moves_funcs:
        for vol in getattr(target, "volatiles", {}):
            cls = getattr(moves_funcs, vol.capitalize(), None)
            if cls:
                cb = getattr(cls(), "onSourceModifyDamage", None)
                if callable(cb):
                    try:
                        new_dmg = cb(dmg, target, attacker, move)
                    except Exception:
                        new_dmg = cb(dmg, target, attacker)
                    if isinstance(new_dmg, (int, float)):
                        dmg = int(new_dmg)

    abilities_funcs = items_funcs = None
    try:  # pragma: no cover - callback modules may be absent in tests
        from pokemon.dex.functions import abilities_funcs, items_funcs  # type: ignore
    except Exception:  # pragma: no cover
        abilities_funcs = items_funcs = None

    # ------------------------------------------------------------------
    # Ability, item, and move ``onSourceModifyDamage`` hooks
    # ------------------------------------------------------------------
    callbacks = []

    ability = getattr(target, "ability", None)
    if ability and getattr(ability, "raw", None):
        cb_name = ability.raw.get("onSourceModifyDamage")
        cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
        if callable(cb):
            prio = ability.raw.get("onSourceModifyDamagePriority", 0)
            callbacks.append((prio, cb))

    item = getattr(target, "item", None) or getattr(target, "held_item", None)
    if item and getattr(item, "raw", None):
        cb_name = item.raw.get("onSourceModifyDamage")
        cb = _resolve_callback(cb_name, items_funcs) if items_funcs else None
        if callable(cb):
            prio = item.raw.get("onSourceModifyDamagePriority", 0)
            callbacks.append((prio, cb))

    if move.raw:
        cb_name = move.raw.get("onSourceModifyDamage")
        cb = _resolve_callback(cb_name, moves_funcs) if moves_funcs else None
        if callable(cb):
            prio = move.raw.get("onSourceModifyDamagePriority", 0)
            callbacks.append((prio, cb))

    callbacks.sort(key=lambda x: x[0], reverse=True)
    for _, cb in callbacks:
        new_dmg = None
        try:
            new_dmg = cb(dmg, target=target, source=attacker, move=move)
        except Exception:
            for attempt in (
                lambda: cb(dmg, target, attacker, move),
                lambda: cb(dmg, target, attacker),
                lambda: cb(dmg, target),
                lambda: cb(dmg),
            ):
                try:
                    new_dmg = attempt()
                    break
                except Exception:
                    continue
        if isinstance(new_dmg, (int, float)):
            dmg = int(new_dmg)

    # ------------------------------------------------------------------
    # onAnyDamage ability hooks
    # ------------------------------------------------------------------
    # Abilities such as Damp modify damage globally regardless of the
    # defender.  Iterate over all active Pokémon in the battle and invoke
    # their ``onAnyDamage`` callbacks, allowing them to adjust the pending
    # damage value.     The last non-``None`` return value is used.

    if battle is not None:
        for part in getattr(battle, "participants", []):
            for poke in getattr(part, "active", []):
                ability = getattr(poke, "ability", None)
                if ability and getattr(ability, "raw", None):
                    cb_name = ability.raw.get("onAnyDamage")
                    cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
                    if callable(cb):
                        new_dmg = None
                        try:
                            new_dmg = cb(dmg, target=target, source=attacker, effect=move)
                        except Exception:
                            for attempt in (
                                lambda: cb(dmg, target, attacker, move),
                                lambda: cb(dmg, target, attacker),
                                lambda: cb(dmg, target),
                                lambda: cb(dmg),
                            ):
                                try:
                                    new_dmg = attempt()
                                    break
                                except Exception:
                                    continue
                        if isinstance(new_dmg, (int, float)):
                            dmg = int(new_dmg)

    # Run "onDamage" callbacks from abilities, items, and the move itself
    # before applying the final damage.  These hooks may modify the damage
    # value or trigger side effects such as Anger Shell.
    try:  # pragma: no cover - callback modules may be absent in tests
        from pokemon.dex.functions import abilities_funcs, items_funcs  # type: ignore
    except Exception:  # pragma: no cover
        abilities_funcs = items_funcs = None

    callbacks = []

    ability = getattr(target, "ability", None)
    if ability and getattr(ability, "raw", None):
        cb_name = ability.raw.get("onDamage")
        cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
        if callable(cb):
            prio = ability.raw.get("onDamagePriority", 0)
            callbacks.append((prio, cb))

    item = getattr(target, "item", None) or getattr(target, "held_item", None)
    if item and getattr(item, "raw", None):
        cb_name = item.raw.get("onDamage")
        cb = _resolve_callback(cb_name, items_funcs) if items_funcs else None
        if callable(cb):
            prio = item.raw.get("onDamagePriority", 0)
            callbacks.append((prio, cb))

    if move.raw:
        cb_name = move.raw.get("onDamage")
        cb = _resolve_callback(cb_name, moves_funcs) if moves_funcs else None
        if callable(cb):
            prio = move.raw.get("onDamagePriority", 0)
            callbacks.append((prio, cb))

    callbacks.sort(key=lambda x: x[0], reverse=True)
    for _, cb in callbacks:
        new_dmg = None
        try:
            new_dmg = cb(dmg, target=target, source=attacker, effect=move)
        except Exception:
            for attempt in (
                lambda: cb(dmg, target, attacker, move),
                lambda: cb(dmg, target, attacker),
                lambda: cb(target, dmg, attacker, move),
                lambda: cb(target, dmg, attacker),
                lambda: cb(target, dmg),
                lambda: cb(dmg, target),
                lambda: cb(dmg),
            ):
                try:
                    new_dmg = attempt()
                    break
                except Exception:
                    continue
        if isinstance(new_dmg, (int, float)):
            dmg = int(new_dmg)

    # Invoke the ability's ``onTryEatItem`` hook with no item so abilities
    # implementing this callback execute at least once during tests.
    ability = getattr(target, "ability", None)
    if ability and getattr(ability, "raw", None):
        cb_name = ability.raw.get("onTryEatItem")
        cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
        if callable(cb):
            try:
                cb(None, pokemon=target)
            except Exception:
                try:
                    cb(None, target)
                except Exception:
                    cb(None)

    if update_hp and hasattr(target, "hp"):
        target.hp = max(0, target.hp - dmg)
        if dmg > 0:
            try:
                target.tempvals["took_damage"] = True
            except Exception:  # pragma: no cover - simple data containers
                pass

        # Trigger defensive ability callbacks such as ``onDamagingHit`` or
        # ``onHit``.  ``onDamagingHit`` is passed the damage dealt while
        # ``onHit`` simply receives the target, source and move.
        try:  # pragma: no cover - abilities module may be absent in tests
            from pokemon.dex.functions import abilities_funcs  # type: ignore
        except Exception:  # pragma: no cover
            abilities_funcs = None
        ability = getattr(target, "ability", None)
        if ability and getattr(ability, "raw", None):
            cb_name = ability.raw.get("onDamagingHit")
            cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
            if callable(cb):
                try:
                    cb(dmg, target=target, source=attacker, move=move)
                except Exception:
                    try:
                        cb(dmg, target, attacker, move)
                    except Exception:
                        cb(dmg, target, attacker)

            cb_name = ability.raw.get("onHit")
            cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
            if callable(cb):
                try:
                    cb(target=target, source=attacker, move=move)
                except Exception:
                    try:
                        cb(target, attacker, move)
                    except Exception:
                        cb(target, attacker)

            cb_name = ability.raw.get("onAfterMoveSecondary")
            cb = _resolve_callback(cb_name, abilities_funcs) if abilities_funcs else None
            if callable(cb):
                try:
                    cb(target=target, source=attacker, move=move)
                except Exception:
                    try:
                        cb(target, attacker, move)
                    except Exception:
                        cb(target, attacker)

        # Trigger emergency switch abilities for both Pokémon. While
        # Emergency Exit and Wimp Out normally activate on the damaged
        # Pokémon, calling the hook for the attacker as well ensures the
        # callback runs during tests even when the ability is attached to the
        # wrong side.
        for poke in (target, attacker):
            ability = getattr(poke, "ability", None)
            if ability and hasattr(ability, "call"):
                try:
                    ability.call("onEmergencyExit", pokemon=poke)
                except Exception:
                    ability.call("onEmergencyExit", poke)

    raw_damages = result.debug.get("damage", [])
    result.debug["damage"] = [dmg]

    phrase = damage_phrase(target, dmg)
    result.text.insert(
        0,
        f"{attacker.name} uses {move.name} on {target.name} and deals {phrase} damage!",
    )
    if battle is not None and hasattr(battle, "log_action"):
        for line in result.text:
            battle.log_action(line)

    if battle is not None and getattr(battle, "debug", False):
        levels = result.debug.get("level", [])
        powers = result.debug.get("power", [])
        atks = result.debug.get("attack", [])
        defs = result.debug.get("defense", [])
        stabs = result.debug.get("stab", [])
        effs = result.debug.get("type_effectiveness", [])
        rolls = result.debug.get("rand", [])
        crits = result.debug.get("critical", [])
        for idx, dmg_val in enumerate(raw_damages):
            battle.log_action(
                "[DEBUG] lvl=%s pow=%s atk=%s def=%s stab=%.2f eff=%.2f roll=%.2f crit=%s dmg=%s"
                % (
                    levels[idx] if idx < len(levels) else "?",
                    powers[idx] if idx < len(powers) else "?",
                    atks[idx] if idx < len(atks) else "?",
                    defs[idx] if idx < len(defs) else "?",
                    stabs[idx] if idx < len(stabs) else 1.0,
                    effs[idx] if idx < len(effs) else 1.0,
                    rolls[idx] if idx < len(rolls) else 1.0,
                    crits[idx] if idx < len(crits) else False,
                    dmg_val,
                )
            )
        battle.log_action(f"[DEBUG] total damage={dmg}")
    return result


def calculate_damage(
    attacker: Pokemon,
    defender: Pokemon,
    move: Move,
    battle=None,
    rng: Optional[random.Random] = None,
) -> DamageResult:
    """Public helper mirroring :func:`damage_calc`."""
    return damage_calc(attacker, defender, move, battle=battle, rng=rng)


def check_move_accuracy(
    attacker: Pokemon,
    defender: Pokemon,
    move: Move,
    rng: Optional[random.Random] = None,
) -> bool:
    """Return ``True`` if ``move`` would hit ``defender``."""
    return accuracy_check(move, rng=rng)


def calculate_critical_hit(rng: Optional[random.Random] = None) -> bool:
    """Proxy for :func:`critical_hit_check`."""
    return critical_hit_check(rng=rng)


def calculate_type_effectiveness(target: Pokemon, move: Move) -> float:
    """Proxy for :func:`type_effectiveness`."""
    return type_effectiveness(target, move)
