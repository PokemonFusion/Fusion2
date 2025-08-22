import ast
import os
import sys
import textwrap
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

models_path = os.path.join(ROOT, "pokemon", "models", "core.py")
source = open(models_path).read()
module = ast.parse(source)
heal_code = None
for node in module.body:
	if isinstance(node, ast.ClassDef) and node.name == "OwnedPokemon":
		for sub in node.body:
			if isinstance(sub, ast.FunctionDef) and sub.name == "heal":
				heal_code = ast.get_source_segment(source, sub)
				break
if heal_code is None:
	raise RuntimeError("heal method not found")
ns = {}
exec(textwrap.dedent(heal_code), ns)
heal_func = ns["heal"]


def setup_modules():
	orig_evennia = sys.modules.get("evennia")
	orig_helpers = sys.modules.get("pokemon.helpers.pokemon_helpers")
	orig_dex = sys.modules.get("pokemon.dex")

	# minimal evennia stub
	evennia = types.ModuleType("evennia")
	evennia.DefaultObject = type("DefaultObject", (), {})
	utils_mod = types.ModuleType("evennia.utils")
	idmapper_mod = types.ModuleType("evennia.utils.idmapper")
	id_models = types.ModuleType("evennia.utils.idmapper.models")
	id_models.SharedMemoryModel = object
	utils_mod.idmapper = types.SimpleNamespace(models=id_models)
	evennia.utils = utils_mod
	obj_mod = types.ModuleType("evennia.objects")
	obj_models = types.ModuleType("evennia.objects.models")
	obj_models.ObjectDB = type("ObjectDB", (), {})
	obj_mod.models = obj_models
	evennia.objects = obj_mod
	sys.modules["evennia"] = evennia
	sys.modules["evennia.utils"] = utils_mod
	sys.modules["evennia.utils.idmapper"] = idmapper_mod
	sys.modules["evennia.utils.idmapper.models"] = id_models
	sys.modules["evennia.objects"] = obj_mod
	sys.modules["evennia.objects.models"] = obj_models

	helpers_mod = types.ModuleType("pokemon.helpers.pokemon_helpers")
	helpers_mod.get_max_hp = lambda poke: 50
	sys.modules["pokemon.helpers.pokemon_helpers"] = helpers_mod

	dex_mod = types.ModuleType("pokemon.dex")
	dex_mod.MOVEDEX = {"tackle": {"pp": 10}, "growl": {"pp": 40}}
	sys.modules["pokemon.dex"] = dex_mod

	return orig_evennia, orig_helpers, orig_dex


def restore_modules(orig_evennia, orig_helpers, orig_dex):
	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	sys.modules.pop("evennia.utils", None)
	sys.modules.pop("evennia.utils.idmapper", None)
	sys.modules.pop("evennia.utils.idmapper.models", None)
	sys.modules.pop("evennia.objects", None)
	sys.modules.pop("evennia.objects.models", None)

	if orig_helpers is not None:
		sys.modules["pokemon.helpers.pokemon_helpers"] = orig_helpers
	else:
		sys.modules.pop("pokemon.helpers.pokemon_helpers", None)

	if orig_dex is not None:
		sys.modules["pokemon.dex"] = orig_dex
	else:
		sys.modules.pop("pokemon.dex", None)


class FakeBoost:
	def __init__(self, move_name, bonus):
		self.move = types.SimpleNamespace(name=move_name)
		self.bonus_pp = bonus


class BoostManager(list):
	def all(self):
		return self


class FakeSlot:
	def __init__(self, move_name):
		self.move = types.SimpleNamespace(name=move_name)
		self.current_pp = 0
		self.save_calls = 0

	def save(self):
		self.save_calls += 1


class SlotManager(list):
	def __init__(self, slots):
		super().__init__(slots)
		self.bulk_calls = 0

	def all(self):
		return self

	def bulk_update(self, objs, fields):
		self.bulk_calls += 1


class FakePokemon:
	heal = None

	def __init__(self):
		self.current_hp = 0
		self.status = "poisoned"
		self.pp_boosts = BoostManager([FakeBoost("tackle", 2)])
		self.activemoveslot_set = SlotManager([FakeSlot("tackle"), FakeSlot("growl")])
		self.saved = False

	def get_max_hp(self):
		from pokemon.helpers.pokemon_helpers import get_max_hp

		return get_max_hp(self)

	def save(self):
		self.saved = True


def test_heal_resets_pp_and_status():
	orig_evennia, orig_helpers, orig_dex = setup_modules()
	FakePokemon.heal = heal_func
	mon = FakePokemon()
	mon.heal()
	restore_modules(orig_evennia, orig_helpers, orig_dex)
	vals = [s.current_pp for s in mon.activemoveslot_set]
	assert vals == [12, 40]
	assert mon.current_hp == 50
	assert mon.status == ""


def test_heal_uses_bulk_update_once():
	orig_evennia, orig_helpers, orig_dex = setup_modules()
	FakePokemon.heal = heal_func
	mon = FakePokemon()
	mon.heal()
	restore_modules(orig_evennia, orig_helpers, orig_dex)
	slots = mon.activemoveslot_set
	assert slots.bulk_calls == 1
	assert all(s.save_calls == 0 for s in slots)
