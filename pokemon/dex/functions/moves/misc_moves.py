"""Miscellaneous helpers and registries for move callbacks."""

from pokemon.data import TYPE_CHART

from .damage_moves import Leechseed, Substitute
from .status_moves import Aquaring, Attract


def type_effectiveness(target, move):
    """Return the type effectiveness multiplier for ``move`` hitting ``target``."""
    if not move or not getattr(move, "type", None):
        return 1.0
    chart = TYPE_CHART.get(move.type.capitalize(), {})
    eff = 1.0
    for typ in getattr(target, "types", []):
        val = chart.get(typ.capitalize(), 0)
        if val == 1:
            eff *= 2
        elif val == 2:
            eff *= 0.5
        elif val == 3:
            eff *= 0
    return eff


VOLATILE_HANDLERS = {
    "leechseed": Leechseed(),
    "substitute": Substitute(),
    "aquaring": Aquaring(),
    "attract": Attract(),
}


__all__ = ["type_effectiveness", "VOLATILE_HANDLERS"]

