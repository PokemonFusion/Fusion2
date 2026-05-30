import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


class FakeQS(list):
	def order_by(self, *fields):
		return self

	def first(self):
		return self[0] if self else None


class FakeTemplateManager:
	def __init__(self):
		self.data = []

	def create(self, **kwargs):
		obj = types.SimpleNamespace(**kwargs)
		self.data.append(obj)
		return obj

	def filter(self, **kwargs):
		rows = []
		for obj in self.data:
			if all(getattr(obj, key, None) == value for key, value in kwargs.items()):
				rows.append(obj)
		return FakeQS(rows)


class FakeNPCPokemonTemplate:
	objects = FakeTemplateManager()


class Move:
	def __init__(self, name, priority=0):
		self.name = name
		self.priority = priority


class Pokemon:
	def __init__(self, name, level=1, hp=10, max_hp=10, moves=None, ability=None, ivs=None, evs=None, nature="Hardy", model_id=None, species=None, gender="N", item=None):
		self.name = name
		self.species = species or name
		self.level = level
		self.hp = hp
		self.max_hp = max_hp
		self.moves = moves or []
		self.ability = ability
		self.ivs = ivs or [0, 0, 0, 0, 0, 0]
		self.evs = evs or [0, 0, 0, 0, 0, 0]
		self.nature = nature
		self.model_id = model_id
		self.gender = gender
		self.item = item


def load_utils():
	path = os.path.join(ROOT, "utils", "pokemon_utils.py")
	spec = importlib.util.spec_from_file_location("utils.pokemon_utils", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def setup_module(module):
	module.prev_bd = sys.modules.get("pokemon.battle.battledata")
	module.prev_bi = sys.modules.get("pokemon.battle.battleinstance")
	module.prev_models_core = sys.modules.get("pokemon.models.core")
	module.prev_models_trainer = sys.modules.get("pokemon.models.trainer")
	module.prev_encounters = sys.modules.get("pokemon.services.encounters")
	module.prev_refs = sys.modules.get("pokemon.services.pokemon_refs")

	battledata = types.ModuleType("pokemon.battle.battledata")
	battledata.Move = Move
	battledata.Pokemon = Pokemon
	sys.modules["pokemon.battle.battledata"] = battledata

	battleinstance = types.ModuleType("pokemon.battle.battleinstance")
	battleinstance._calc_stats_from_model = lambda p: {"hp": 30}
	battleinstance.create_battle_pokemon = lambda name, level, trainer=None, is_wild=False: Pokemon(name, level)
	sys.modules["pokemon.battle.battleinstance"] = battleinstance

	models_core = types.ModuleType("pokemon.models.core")
	models_core.OwnedPokemon = object
	sys.modules["pokemon.models.core"] = models_core

	models_trainer = types.ModuleType("pokemon.models.trainer")
	models_trainer.NPCPokemonTemplate = FakeNPCPokemonTemplate
	sys.modules["pokemon.models.trainer"] = models_trainer

	encounters = types.ModuleType("pokemon.services.encounters")
	encounters.create_encounter_pokemon = lambda **kwargs: types.SimpleNamespace(encounter_id="enc-1", current_hp=30, **kwargs)
	encounters.encounter_ref = lambda encounter: f"encounter:{encounter.encounter_id}"
	sys.modules["pokemon.services.encounters"] = encounters

	refs = types.ModuleType("pokemon.services.pokemon_refs")
	refs.build_owned_ref = lambda identifier: f"owned:{identifier}"
	sys.modules["pokemon.services.pokemon_refs"] = refs

	module.mod = load_utils()


def teardown_module(module):
	for name, old in [
		("pokemon.battle.battledata", module.prev_bd),
		("pokemon.battle.battleinstance", module.prev_bi),
		("pokemon.models.core", module.prev_models_core),
		("pokemon.models.trainer", module.prev_models_trainer),
		("pokemon.services.encounters", module.prev_encounters),
		("pokemon.services.pokemon_refs", module.prev_refs),
	]:
		if old is not None:
			sys.modules[name] = old
		else:
			sys.modules.pop(name, None)


def test_spawn_npc_pokemon_from_template():
	trainer = object()
	FakeNPCPokemonTemplate.objects.create(
		npc_trainer=trainer,
		template_key="lead",
		species="Pikachu",
		level=5,
		ability="Static",
		gender="M",
		nature="Hardy",
		ivs=[0, 0, 0, 0, 0, 0],
		evs=[0, 0, 0, 0, 0, 0],
		held_item="",
		move_names=["Thunder Shock"],
		sort_order=1,
	)
	p = mod.spawn_npc_pokemon(trainer)
	assert p.name == "Pikachu"
	assert p.model_id == "encounter:enc-1"


def test_spawn_npc_pokemon_generated_fallback():
	trainer = object()
	p = mod.spawn_npc_pokemon(trainer, use_templates=False)
	assert p.name == "Charmander"
