"""User interface utilities for Pokémon displays."""

from importlib import import_module

__all__ = ["render_battle_ui", "render_move_gui"]


def render_battle_ui(*args, **kwargs):
	return import_module("pokemon.ui.battle_render").render_battle_ui(*args, **kwargs)


def render_move_gui(*args, **kwargs):
	return import_module("pokemon.ui.move_gui").render_move_gui(*args, **kwargs)
