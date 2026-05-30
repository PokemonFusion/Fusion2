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

	def __init__(
		self,
		name: str,
		level: int = 1,
		hp: int = 10,
		max_hp: int = 10,
		gender: str = "N",
		status: str = "",
	):
		self.name = name
		self.level = level
		self.hp = hp
		self.max_hp = max_hp
		self.gender = gender
		self.status = status


class DummyTrainer:
	"""Trainer stub holding an active Pokémon."""

	def __init__(self, name: str, mon: DummyMon):
		self.name = name
		self.active_pokemon = mon
		self.team = [mon]


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
	"""The legacy boxed battle UI should not display a round number."""

	state = DummyState()
	viewer = state.A
	out = render_battle_ui(state, viewer, style="legacy")
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


def test_classic_modern_renderer_uses_ascii_separators_and_width() -> None:
	state = DummyState()
	state.A.active_pokemon.gender = "F"
	state.B.active_pokemon.gender = "M"
	viewer = state.A

	out = render_battle_ui(state, viewer, total_width=78, style="classic_modern")
	clean = battle_render.strip_ansi(out)

	assert clean.splitlines()[0].startswith("== Turn 5 ")
	assert "Team A" in clean
	assert "Weather: Clear" in clean
	assert "Field: Neutral" in clean
	assert "Round: 5" in clean
	assert "HP: ||" in clean
	assert not any(ch in clean for ch in "┌┐└┘│─╭╮╰╯")
	assert not any(line.lstrip().startswith("|") or line.rstrip().endswith("|") for line in clean.splitlines())
	assert max(len(line) for line in clean.splitlines()) <= 78


def test_classic_modern_is_default_renderer() -> None:
	state = DummyState()
	out = render_battle_ui(state, state.A, total_width=78)
	clean = battle_render.strip_ansi(out)

	assert clean.startswith("== Turn 5 ")
	assert "Team A" in clean
	assert not any(ch in clean for ch in "┌┐└┘│─╭╮╰╯")


def test_classic_modern_hp_visibility_for_viewer() -> None:
	state = DummyState()
	state.A.active_pokemon.hp = 15
	state.A.active_pokemon.max_hp = 20
	state.B.active_pokemon.hp = 30
	state.B.active_pokemon.max_hp = 60

	out = render_battle_ui(state, state.A, total_width=78, style="classic_modern")
	clean = battle_render.strip_ansi(out)

	assert "15/20 75%" in clean
	assert "30/60" not in clean
	assert "50%" in clean


def test_classic_modern_wild_opponent_shows_percent_only() -> None:
	state = DummyState()
	state.encounter_kind = "wild"
	wild_mon = DummyMon("Pidgey", level=4, hp=12, max_hp=24, gender="M")
	state.B = types.SimpleNamespace(
		name="Placeholder",
		team=[wild_mon],
		active_pokemon=wild_mon,
		is_wild=True,
	)

	out = render_battle_ui(state, state.A, total_width=78, style="classic_modern")
	clean = battle_render.strip_ansi(out)

	assert "WILD Pokemon" in clean
	assert "12/24" not in clean
	assert "50%" in clean


def test_classic_modern_gender_colors_and_ascii_team_markers() -> None:
	state = DummyState()
	state.A.active_pokemon.gender = "F"
	state.B.active_pokemon.gender = "M"

	out = render_battle_ui(state, state.A, total_width=78, style="classic_modern")
	clean = battle_render.strip_ansi(out)

	assert "|M♀|n" in out
	assert "|C♂|n" in out
	assert "Team: O . . . . ." in clean


def test_pf1_renderer_uses_muck_rows_and_width() -> None:
	state = DummyState()
	state.A.active_pokemon.gender = "F"
	state.B.active_pokemon.gender = "M"
	state.A.active_pokemon.hp = 15
	state.A.active_pokemon.max_hp = 20
	state.B.active_pokemon.hp = 30
	state.B.active_pokemon.max_hp = 60

	out = render_battle_ui(state, state.A, total_width=78, style="pf1")
	clean = battle_render.strip_ansi(out)

	assert "Team A" in clean
	assert "Team B" in clean
	assert "A1" in clean
	assert "B1" in clean
	assert "NRM" in clean
	assert "Weather: Clear" in clean
	assert "Field: Neutral" in clean
	assert "Round: 5" in clean
	assert "HP:" in clean
	assert "15/" in clean
	assert "30/" not in clean
	assert "50%" in clean
	assert not any(ch in clean for ch in "┌┐└┘│─╭╮╰╯")
	assert not any(line.rstrip().endswith("|") for line in clean.splitlines())
	assert max(len(line) for line in clean.splitlines()) <= 78


def test_pf1_renderer_wild_side_and_party_markers() -> None:
	state = DummyState()
	state.encounter_kind = "wild"
	state.A.team = [
		state.A.active_pokemon,
		DummyMon("Charmander", hp=5, max_hp=20, status="BRN"),
		DummyMon("Squirtle", hp=0, max_hp=20),
	]
	wild_mon = DummyMon("Pidgey", level=4, hp=12, max_hp=24, gender="M")
	state.B = types.SimpleNamespace(
		name="Placeholder",
		team=[wild_mon],
		active_pokemon=wild_mon,
		is_wild=True,
	)

	out = render_battle_ui(state, state.A, total_width=78, style="pf1")
	clean = battle_render.strip_ansi(out)

	assert "OSX" in clean
	assert "WILD Pokemon" in clean
	assert "Placeholder" not in clean
	assert "12/" not in clean
	assert "50%" in clean


def test_hp_bar_ascii_color_rules() -> None:
	high = battle_render.hp_bar_ascii(80, 100, width=10)
	mid = battle_render.hp_bar_ascii(40, 100, width=10)
	low = battle_render.hp_bar_ascii(10, 100, width=10)

	assert high.startswith("|g")
	assert mid.startswith("|y")
	assert low.startswith("|r")
	assert len(battle_render.strip_ansi(high)) == 10
	assert len(battle_render.strip_ansi(mid)) == 10
	assert len(battle_render.strip_ansi(low)) == 10


def test_gender_chip_ascii_fallback() -> None:
	male = types.SimpleNamespace(gender="M")
	female = types.SimpleNamespace(gender="F")
	unknown = types.SimpleNamespace(gender="N")

	assert battle_render.gender_chip(male, ascii_symbols=True) == "|CM|n"
	assert battle_render.gender_chip(female, ascii_symbols=True) == "|MF|n"
	assert battle_render.gender_chip(unknown, ascii_symbols=True) == "|x-|n"


def test_party_pips_ascii_low_hp_uses_lowercase_o() -> None:
	mon = DummyMon("Pidgey", hp=1, max_hp=10)
	trainer = DummyTrainer("Wild", mon)

	out = battle_render.party_pips(trainer, ascii_symbols=True)

	assert out.startswith("|yo|n")


def test_beip_viewer_uses_ascii_symbol_fallback() -> None:
	state = DummyState()
	state.A.active_pokemon.gender = "F"
	state.B.active_pokemon.gender = "M"
	state.A.sessions = types.SimpleNamespace(
		all=lambda: [types.SimpleNamespace(protocol_flags={"CLIENTNAME": "BEIP"})]
	)

	out = render_battle_ui(state, state.A, total_width=78)

	assert "|MF|n" in out
	assert "|CM|n" in out
	assert "\u2640" not in out
	assert "\u2642" not in out
