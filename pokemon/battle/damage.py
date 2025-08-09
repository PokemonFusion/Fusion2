from dataclasses import dataclass, field
from typing import Dict, List, Any
import random
from math import floor

from ..dex import Move, Pokemon
from ..data import TYPE_CHART

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


def percent_check(chance: float) -> bool:
    """Return True if random roll succeeds."""
    return chance > random.random()


def accuracy_check(move: Move) -> bool:
    """Very small accuracy check using move.accuracy."""
    if move.accuracy is True:
        return True
    if isinstance(move.accuracy, (int, float)):
        return percent_check(float(move.accuracy) / 100.0)
    return True


def critical_hit_check() -> bool:
    """Simplified crit check."""
    return percent_check(1 / 24)


def base_damage(level: int, power: int, atk: int, defense: int, *, return_roll: bool = False):
    """Return base damage and optionally the random roll used."""

    dmg = floor(
        floor(floor(((2 * level) / 5) + 2) * power * (atk * 1.0) / defense) / 50
    ) + 2
    rand_mod = random.randint(85, 100) / 100.0
    result = floor(dmg * rand_mod)
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

    types = getattr(attacker, "types", None)
    if types is None and hasattr(attacker, "species") and getattr(attacker.species, "types", None):
        types = attacker.species.types
    types = types or []

    has_type = move.type.lower() in {t.lower() for t in types}
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
    try:
        from pokemon.utils.pokemon_helpers import get_max_hp
        maxhp = get_max_hp(target)
    except Exception:  # pragma: no cover - fallback when helpers unavailable
        maxhp = getattr(getattr(target, "base_stats", None), "hp", 0)
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


def damage_calc(attacker: Pokemon, target: Pokemon, move: Move, battle=None, *, spread: bool = False) -> DamageResult:
    result = DamageResult()
    numhits = 1
    multihit = move.raw.get("multihit") if move.raw else None
    if isinstance(multihit, list):
        population, weights = zip(*MULTIHITCOUNT.items())
        numhits = random.choices(population, weights)[0]
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

        if not accuracy_check(move):
            result.text.append(f"{attacker.name} uses {move.name} but it missed!")
            continue

        from pokemon.battle.utils import get_modified_stat

        atk_key = "attack" if move.category == "Physical" else "special_attack"
        def_key = "defense" if move.category == "Physical" else "special_defense"
        atk_stat = get_modified_stat(attacker, atk_key)
        def_stat = get_modified_stat(target, def_key)

        power = move.power or 0
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

        # ``base_damage`` expects the attacker's level.  Older stubs used in
        # tests only define ``num`` so we fall back to that when ``level`` is
        # missing for backwards compatibility.
        level = getattr(attacker, "level", None)
        if level is None:
            level = getattr(attacker, "num", 1)
        dmg, rand_mod = base_damage(level, power, atk_stat, def_stat, return_roll=True)
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
            result.text.append(
                DEFAULT_TEXT["default"]["immune"].replace("[POKEMON]", target.name)
            )
            continue
        dmg = floor(dmg * eff)

        # Critical hit calculation with simple ratio handling
        crit_ratio = 0
        if move.raw:
            crit_ratio = int(move.raw.get("critRatio", 0))
        ability = getattr(attacker, "ability", None)
        if ability and hasattr(ability, "call"):
            try:
                new_ratio = ability.call("onModifyCritRatio", crit_ratio, attacker=attacker, defender=target, move=move)
            except Exception:
                new_ratio = ability.call("onModifyCritRatio", crit_ratio)
            if isinstance(new_ratio, (int, float)):
                crit_ratio = int(new_ratio)
        item = getattr(attacker, "item", None) or getattr(attacker, "held_item", None)
        if item and hasattr(item, "call"):
            try:
                new_ratio = item.call("onModifyCritRatio", crit_ratio, pokemon=attacker, target=target)
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
            crit = percent_check(chance)
        if crit:
            dmg = floor(dmg * 1.5)
            result.debug.setdefault("critical", []).append(True)
        else:
            result.debug.setdefault("critical", []).append(False)
        phrase = damage_phrase(target, dmg)
        result.text.append(
            f"{attacker.name} uses {move.name} on {target.name} and deals {phrase} damage!"
        )
        if spread:
            dmg = int(dmg * 0.75)
        result.debug.setdefault("damage", []).append(dmg)

        # apply simple status effects like burns
        if move.raw:
            status = move.raw.get("status")
            chance = move.raw.get("statusChance", 100)
            secondary = move.raw.get("secondary")
            if secondary and isinstance(secondary, dict):
                status = secondary.get("status", status)
                chance = secondary.get("chance", chance)
            if status and percent_check(chance / 100.0):
                setattr(target, "status", status)
                try:
                    from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
                except Exception:
                    CONDITION_HANDLERS = {}
                handler = CONDITION_HANDLERS.get(status)
                if handler and hasattr(handler, "onStart"):
                    handler.onStart(target, source=attacker, battle=battle)
                if status == "brn":
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

    if update_hp and hasattr(target, "hp"):
        target.hp = max(0, target.hp - dmg)
        if dmg > 0:
            try:
                target.tempvals["took_damage"] = True
            except Exception:  # pragma: no cover - simple data containers
                pass

    raw_damages = result.debug.get("damage", [])
    result.debug["damage"] = [dmg]
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


def calculate_damage(attacker: Pokemon, defender: Pokemon, move: Move, battle=None) -> DamageResult:
    """Public helper mirroring :func:`damage_calc`."""
    return damage_calc(attacker, defender, move, battle=battle)


def check_move_accuracy(attacker: Pokemon, defender: Pokemon, move: Move) -> bool:
    """Return ``True`` if ``move`` would hit ``defender``."""
    return accuracy_check(move)


def calculate_critical_hit() -> bool:
    """Proxy for :func:`critical_hit_check`."""
    return critical_hit_check()


def calculate_type_effectiveness(target: Pokemon, move: Move) -> float:
    """Proxy for :func:`type_effectiveness`."""
    return type_effectiveness(target, move)
