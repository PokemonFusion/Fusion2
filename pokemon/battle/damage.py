from dataclasses import dataclass, field
from typing import Dict, List, Any
import random
from math import floor

from ..dex import Move, Pokemon
from ..data import TYPE_CHART


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


def base_damage(level: int, power: int, atk: int, defense: int) -> int:
    dmg = floor(floor(floor(((2 * level) / 5) + 2) * power * (atk * 1.0) / defense) / 50) + 2
    rand_mod = random.randint(85, 100) / 100.0
    return floor(dmg * rand_mod)


def stab_multiplier(attacker: Pokemon, move: Move) -> float:
    """Return the STAB multiplier for ``attacker`` using ``move``.

    This helper tolerates different container layouts.  If ``attacker`` does
    not define a ``types`` attribute, the function falls back to common
    alternatives such as ``species.types`` or ``data['types']``.  Ability hooks
    may further modify the multiplier via ``onModifySTAB``.
    """

    if not move.type:
        return 1.0

    types = getattr(attacker, "types", None)
    if types is None:
        if hasattr(attacker, "species") and getattr(attacker.species, "types", None):
            types = attacker.species.types
        elif hasattr(attacker, "data"):
            types = attacker.data.get("types")
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
    maxhp = target.base_stats.hp
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


def damage_calc(attacker: Pokemon, target: Pokemon, move: Move, battle=None) -> DamageResult:
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

        from . import utils

        atk_key = "atk" if move.category == "Physical" else "spa"
        def_key = "def_" if move.category == "Physical" else "spd"

        if hasattr(utils, "get_modified_stat"):
            atk_stat = utils.get_modified_stat(attacker, atk_key)
            def_stat = utils.get_modified_stat(target, def_key)
        else:
            atk_stat = getattr(attacker.base_stats, atk_key)
            def_stat = getattr(target.base_stats, def_key)

        power = move.power or 0
        if move.raw:
            cb = move.raw.get("basePowerCallback")
            if callable(cb):
                try:
                    new_power = cb(attacker, target, move, battle=battle)
                    if isinstance(new_power, (int, float)):
                        power = int(new_power)
                except Exception:
                    pass

        dmg = base_damage(attacker.num, power, atk_stat, def_stat)
        dmg = floor(dmg * stab_multiplier(attacker, move))
        eff = type_effectiveness(target, move)
        dmg = floor(dmg * eff)
        if critical_hit_check():
            dmg = floor(dmg * 1.5)
        phrase = damage_phrase(target, dmg)
        result.text.append(
            f"{attacker.name} uses {move.name} on {target.name} and deals {phrase} damage!"
        )
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
