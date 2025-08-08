import os
import sys
import types
import importlib

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
    monkeypatch.setitem(sys.modules, "pokemon.models", types.ModuleType("pokemon.models"))

    # patch move management service to confirm it is invoked
    called = []
    service_mod = types.ModuleType("pokemon.services.move_management")

    def fake_learn(poke, *a, **k):
        called.append(poke)

    service_mod.learn_level_up_moves = fake_learn
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

    monkeypatch.delitem(sys.modules, "pokemon.utils.pokemon_helpers", raising=False)
    from pokemon.utils.pokemon_helpers import create_owned_pokemon

    mon = create_owned_pokemon("Pikachu", trainer="Ash", level=5, gender="M")
    assert OwnedPokemon.objects.kwargs["trainer"] == "Ash"
    assert mon.level == 5
    assert mon.healed
    assert called and called[0] is mon
