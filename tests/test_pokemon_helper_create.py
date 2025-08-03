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
            self.moves_learned = False
        def set_level(self, level):
            self.level = level
        def heal(self):
            self.healed = True
        def learn_level_up_moves(self):
            self.moves_learned = True
    fake_models = types.ModuleType("pokemon.models")
    fake_models.OwnedPokemon = OwnedPokemon
    monkeypatch.setitem(sys.modules, "pokemon.models", fake_models)
    pkg = sys.modules.get("pokemon")
    if pkg and getattr(pkg, "__path__", None) is None:
        monkeypatch.delitem(sys.modules, "pokemon")
        pkg = importlib.import_module("pokemon")
    else:
        pkg = importlib.import_module("pokemon")
    monkeypatch.setattr(pkg, "models", fake_models, raising=False)
    from pokemon.utils.pokemon_helpers import create_owned_pokemon
    mon = create_owned_pokemon("Pikachu", trainer="Ash", level=5, gender="M")
    assert OwnedPokemon.objects.kwargs["trainer"] == "Ash"
    assert mon.level == 5
    assert mon.healed and mon.moves_learned
