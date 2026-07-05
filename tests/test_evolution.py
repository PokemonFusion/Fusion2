import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Build minimal pokemon.dex package
entities_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", entities_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)

pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = [os.path.join(ROOT, "pokemon", "dex")]
pokemon_dex.entities = ent_mod
pokemon_dex.POKEDEX = {
	"Bulbasaur": ent_mod.Pokemon(
		name="Bulbasaur",
		num=1,
		types=["Grass"],
		gender_ratio=None,
		base_stats=ent_mod.Stats(),
		abilities={},
		evos=["Ivysaur"],
		raw={"evos": ["Ivysaur"]},
	),
	"Ivysaur": ent_mod.Pokemon(
		name="Ivysaur",
		num=2,
		types=["Grass"],
		gender_ratio=None,
		base_stats=ent_mod.Stats(),
		abilities={},
		prevo="Bulbasaur",
		evo_level=16,
		evos=["Venusaur"],
		raw={"prevo": "Bulbasaur", "evoLevel": 16},
	),
}
sys.modules["pokemon.dex"] = pokemon_dex

evo_path = os.path.join(ROOT, "pokemon", "data", "evolution.py")
evo_spec = importlib.util.spec_from_file_location("pokemon.data.evolution", evo_path)
evo_mod = importlib.util.module_from_spec(evo_spec)
sys.modules[evo_spec.name] = evo_mod
evo_spec.loader.exec_module(evo_mod)

evo_mod.POKEDEX = pokemon_dex.POKEDEX


class DummyMon:
	def __init__(self, name, level):
		self.name = name
		self.level = level
		self.type_ = "Grass"


def _owned_pokemon_model():
	os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
	import django

	try:
		django.setup()
	except RuntimeError:
		pass
	from pokemon.models.core import OwnedPokemon

	return OwnedPokemon


def test_get_evolution_items_empty():
	assert evo_mod.get_evolution_items() == []


def test_attempt_evolution_by_level():
	mon = DummyMon("Bulbasaur", 20)
	assert evo_mod.attempt_evolution(mon) == "Ivysaur"
	assert mon.name == "Ivysaur"


def test_attempt_evolution_updates_ownedpokemon_species_without_name_setter():
	OwnedPokemon = _owned_pokemon_model()

	mon = OwnedPokemon(species="Bulbasaur", level=20)

	assert evo_mod.attempt_evolution(mon) == "Ivysaur"
	assert mon.species == "Ivysaur"
	assert mon.name == "Ivysaur"


def test_attempt_evolution_preserves_ownedpokemon_nickname():
	OwnedPokemon = _owned_pokemon_model()

	mon = OwnedPokemon(species="Bulbasaur", nickname="Buddy", level=20)

	assert evo_mod.attempt_evolution(mon) == "Ivysaur"
	assert mon.species == "Ivysaur"
	assert mon.name == "Buddy"
