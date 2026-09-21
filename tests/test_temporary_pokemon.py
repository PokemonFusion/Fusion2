import importlib
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_helper_never_creates_temp_owned_rows(monkeypatch):
	class DummyManager:
		def __init__(self):
			self.kwargs = None

		def create(self, **kwargs):
			self.kwargs = kwargs
			return OwnedPokemon(**kwargs)

	class OwnedPokemon:
		objects = DummyManager()

		def __init__(self, **kwargs):
			for key, value in kwargs.items():
				setattr(self, key, value)
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
		"Bulbasaur",
		trainer=types.SimpleNamespace(user_id=1),
		level=5,
		is_wild=True,
		ai_trainer="npc",
		is_template=True,
		is_battle_instance=True,
	)

	assert OwnedPokemon.objects.kwargs["trainer"].user_id == 1
	assert "is_wild" not in OwnedPokemon.objects.kwargs
	assert "ai_trainer" not in OwnedPokemon.objects.kwargs
	assert "is_template" not in OwnedPokemon.objects.kwargs
	assert "is_battle_instance" not in OwnedPokemon.objects.kwargs


import pytest
from contextlib import nullcontext


@pytest.fixture(autouse=True)
def placement_factory_dependencies(monkeypatch):
    """Stub only storage IO for the initialization unit tests."""
    from django.db import transaction
    monkeypatch.setattr(transaction, "atomic", lambda: nullcontext())
    storage_module = types.ModuleType("pokemon.models.storage")
    storage_module.UserStorage = types.SimpleNamespace(objects=types.SimpleNamespace(
        get_or_create=lambda **kwargs: (types.SimpleNamespace(pk=1), True)))
    monkeypatch.setitem(sys.modules, "pokemon.models.storage", storage_module)
    placement_module = types.ModuleType("pokemon.services.placement")
    placement_module.PlacementService = lambda storage: types.SimpleNamespace(
        locked=lambda: nullcontext(storage), place_new=lambda mon: None)
    monkeypatch.setitem(sys.modules, "pokemon.services.placement", placement_module)
