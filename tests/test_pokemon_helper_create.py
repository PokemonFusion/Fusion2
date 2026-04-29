import importlib
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_create_owned_pokemon_initializes_model(monkeypatch):
	class DummyManager:
		def __init__(self):
			self.kwargs = None

		def create(self, **kwargs):
			self.kwargs = kwargs
			return OwnedPokemon(**kwargs)

	class OwnedPokemon:
		objects = DummyManager()

		def __init__(self, **kwargs):
			for k, v in kwargs.items():
				setattr(self, k, v)
			self.level = 0
			self.healed = False

		def set_level(self, level):
			self.level = level

		def heal(self):
			self.healed = True

	fake_core = types.ModuleType("pokemon.models.core")
	fake_core.OwnedPokemon = OwnedPokemon
	monkeypatch.setitem(sys.modules, "pokemon.models.core", fake_core)
	fake_models_pkg = types.ModuleType("pokemon.models")
	fake_models_pkg.__path__ = []
	monkeypatch.setitem(sys.modules, "pokemon.models", fake_models_pkg)

	# patch move management service to confirm generated moves are initialized
	called = []
	service_mod = types.ModuleType("pokemon.services.move_management")

	def fake_initialize(poke, *a, **k):
		called.append((poke, k))

	service_mod.initialize_generated_moveset = fake_initialize
	service_mod.learn_level_up_moves = lambda *a, **k: None
	services_pkg = types.ModuleType("pokemon.services")
	services_pkg.move_management = service_mod
	monkeypatch.setitem(sys.modules, "pokemon.services.move_management", service_mod)
	monkeypatch.setitem(sys.modules, "pokemon.services", services_pkg)

	pkg = sys.modules.get("pokemon")
	if pkg and getattr(pkg, "__path__", None) is None:
		monkeypatch.delitem(sys.modules, "pokemon")
		pkg = importlib.import_module("pokemon")
	else:
		pkg = importlib.import_module("pokemon")
	monkeypatch.setattr(pkg, "models", sys.modules["pokemon.models"], raising=False)
	monkeypatch.setattr(pkg, "services", services_pkg, raising=False)

	monkeypatch.delitem(sys.modules, "pokemon.helpers.pokemon_helpers", raising=False)
	from pokemon.helpers.pokemon_helpers import create_owned_pokemon

	mon = create_owned_pokemon(
		"Pikachu",
		trainer="Ash",
		level=5,
		gender="M",
		active_move_names=["thundershock"],
	)
	assert OwnedPokemon.objects.kwargs["trainer"] == "Ash"
	assert mon.level == 5
	assert mon.healed
	assert called and called[0][0] is mon
	assert called[0][1]["active_move_names"] == ["thundershock"]


def test_create_owned_pokemon_strips_legacy_temp_flags(monkeypatch):
	class DummyManager:
		def __init__(self):
			self.kwargs = None

		def create(self, **kwargs):
			self.kwargs = kwargs
			return OwnedPokemon(**kwargs)

	class OwnedPokemon:
		objects = DummyManager()

		def __init__(self, **kwargs):
			for k, v in kwargs.items():
				setattr(self, k, v)
			self.level = 0

		def set_level(self, level):
			self.level = level

		def heal(self):
			return None

	fake_core = types.ModuleType("pokemon.models.core")
	fake_core.OwnedPokemon = OwnedPokemon
	monkeypatch.setitem(sys.modules, "pokemon.models.core", fake_core)
	fake_models_pkg = types.ModuleType("pokemon.models")
	fake_models_pkg.__path__ = []
	monkeypatch.setitem(sys.modules, "pokemon.models", fake_models_pkg)

	service_mod = types.ModuleType("pokemon.services.move_management")
	service_mod.initialize_generated_moveset = lambda *a, **k: None
	service_mod.learn_level_up_moves = lambda *a, **k: None
	services_pkg = types.ModuleType("pokemon.services")
	services_pkg.move_management = service_mod
	monkeypatch.setitem(sys.modules, "pokemon.services.move_management", service_mod)
	monkeypatch.setitem(sys.modules, "pokemon.services", services_pkg)

	pkg = sys.modules.get("pokemon")
	if pkg and getattr(pkg, "__path__", None) is None:
		monkeypatch.delitem(sys.modules, "pokemon")
		pkg = importlib.import_module("pokemon")
	else:
		pkg = importlib.import_module("pokemon")
	monkeypatch.setattr(pkg, "models", sys.modules["pokemon.models"], raising=False)
	monkeypatch.setattr(pkg, "services", services_pkg, raising=False)

	monkeypatch.delitem(sys.modules, "pokemon.helpers.pokemon_helpers", raising=False)
	from pokemon.helpers.pokemon_helpers import create_owned_pokemon

	create_owned_pokemon(
		"Pikachu",
		trainer="Ash",
		level=5,
		is_wild=True,
		ai_trainer="npc",
		is_battle_instance=True,
		is_template=True,
		met_location="Viridian Forest",
	)

	assert "is_wild" not in OwnedPokemon.objects.kwargs
	assert "ai_trainer" not in OwnedPokemon.objects.kwargs
	assert "is_battle_instance" not in OwnedPokemon.objects.kwargs
	assert "is_template" not in OwnedPokemon.objects.kwargs
	assert OwnedPokemon.objects.kwargs["met_location"] == "Viridian Forest"
