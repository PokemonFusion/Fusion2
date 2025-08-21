"""Menu package exposing common EvMenu flows.

This package aggregates the various EvMenu implementations used across the
project.  Some of these menus require the Evennia framework to be installed;
when it's missing (as in the lightweight test environment) importing those
modules would normally raise :class:`ModuleNotFoundError`.  We gracefully skip
them so that other menus remain available.
"""

try:  # Optional - depends on Evennia
    from . import battle_move
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    battle_move = None  # type: ignore[assignment]

# Always import menus that do not rely on Evennia
try:
    from . import learn_new_moves
except ModuleNotFoundError:  # pragma: no cover - should always be present
    learn_new_moves = None  # type: ignore[assignment]

__all__ = [
    name
    for name in ("battle_move", "learn_new_moves")
    if globals().get(name) is not None
]

