import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Stub evennia.ansi
ansi_mod = types.SimpleNamespace(
	GREEN=lambda s: s,
	YELLOW=lambda s: s,
	RED=lambda s: s,
	parse_ansi=lambda s: s,
)
utils_mod = types.ModuleType("evennia.utils")
utils_mod.ansi = ansi_mod
sys.modules["evennia.utils"] = utils_mod

iface_path = os.path.join(ROOT, "pokemon", "battle", "interface.py")
spec = importlib.util.spec_from_file_location("pokemon.battle.interface", iface_path)
iface = importlib.util.module_from_spec(spec)
sys.modules["pokemon.battle.interface"] = iface
spec.loader.exec_module(iface)
display_battle_interface = iface.display_battle_interface
from pokemon.battle.state import BattleState


class DummyMon:
	def __init__(self, name, hp, max_hp):
		self.name = name
		self.level = 5
		self.hp = hp
		self.max_hp = max_hp
		self.status = ""


class DummyTrainer:
	def __init__(self, name, mon):
		self.name = name
		self.active_pokemon = mon
		self.team = [mon]


def test_interface_numbers_for_viewer():
	mon_a = DummyMon("Pika", 15, 20)
	mon_b = DummyMon("Bulba", 30, 60)
	t_a = DummyTrainer("Ash", mon_a)
	t_b = DummyTrainer("Gary", mon_b)
	st = BattleState()

	out_a = display_battle_interface(t_a, t_b, st, viewer_team="A")
	assert "15/20" in out_a
	assert "30/60" not in out_a

	out_b = display_battle_interface(t_a, t_b, st, viewer_team="B")
	assert "30/60" in out_b
	assert "15/20" not in out_b


def test_spectator_shows_percent():
	mon_a = DummyMon("Pika", 15, 20)
	mon_b = DummyMon("Bulba", 30, 60)
	t_a = DummyTrainer("Ash", mon_a)
	t_b = DummyTrainer("Gary", mon_b)
	st = BattleState()
	out = display_battle_interface(t_a, t_b, st, viewer_team=None)
	assert "15/20" not in out and "30/60" not in out
	assert "75%" in out and "50%" in out


def test_display_interface_wild_title_uses_species():
	mon_a = DummyMon("Pika", 15, 20)
	wild_mon = DummyMon("Oddish", 30, 30)
	t_a = DummyTrainer("Ash", mon_a)
	wild_shell = DummyTrainer("Placeholder", wild_mon)
	wild_shell.name = "???"
	st = BattleState()
	st.encounter_kind = "wild"

	out = display_battle_interface(t_a, wild_shell, st, viewer_team="A")
	assert "Wild Oddish" in out
	assert "???" not in out
