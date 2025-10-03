"""Tests for battle UI rendering."""

import importlib.util
import os
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(ROOT, "pokemon", "ui", "battle_render.py")
_spec = importlib.util.spec_from_file_location("battle_render", MODULE_PATH)
battle_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(battle_render)
render_battle_ui = battle_render.render_battle_ui


class DummyMon:
	"""Simple Pokémon stub with minimal attributes."""

	def __init__(self, name: str, level: int = 1, hp: int = 10, max_hp: int = 10):
		self.name = name
		self.level = level
		self.hp = hp
		self.max_hp = max_hp


class DummyTrainer:
	"""Trainer stub holding an active Pokémon."""

	def __init__(self, name: str, mon: DummyMon):
		self.name = name
		self.active_pokemon = mon


class DummyState:
	"""State stub providing trainers and field information."""

	def __init__(self):
	        self.weather = "Clear"
	        self.field = "Neutral"
	        self.round_no = 5
	        self.A = DummyTrainer("Alice", DummyMon("Pikachu", level=5))
	        self.B = DummyTrainer("Bob", DummyMon("Eevee", level=5))
	        self.encounter_kind = ""

	def get_side(self, viewer):
	        return "A"

	def get_trainer(self, side):
	        return getattr(self, side)


def test_battle_ui_omits_round() -> None:
	"""The battle UI should not display a round number."""

	state = DummyState()
	viewer = state.A
	out = render_battle_ui(state, viewer)
	clean = battle_render.strip_ansi(out)
	assert "Round" not in clean
	assert "Field: Neutral" in clean
	assert "Weather: Clear" in clean


def test_wild_battle_title_uses_species() -> None:
	state = DummyState()
	state.encounter_kind = "wild"
	wild_mon = DummyMon("Oddish", level=3)
	state.B = types.SimpleNamespace(
	        name="Mystery Opponent",
	        team=[wild_mon],
	        active_pokemon=wild_mon,
	)
	viewer = state.A
	out = render_battle_ui(state, viewer)
	clean = battle_render.strip_ansi(out)
	assert "Wild Oddish" in clean
	assert "Mystery Opponent" not in clean
