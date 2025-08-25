"""Tests for depositing a Pokémon that is fused with the player."""

import importlib
import sys
import types


def test_deposit_rejects_fusion(monkeypatch):
    """The player's own fusion result should not be depositable."""

    fusion_mod = types.ModuleType("pokemon.models.fusion")
    fusion_mod.PokemonFusion = type("PF", (), {})
    monkeypatch.setitem(sys.modules, "pokemon.models.fusion", fusion_mod)

    objresolve_mod = types.ModuleType("pokemon.utils.objresolve")
    objresolve_mod.resolve_to_obj = lambda val: None
    monkeypatch.setitem(sys.modules, "pokemon.utils.objresolve", objresolve_mod)

    evennia_mod = types.ModuleType("evennia")
    evennia_mod.DefaultCharacter = type("DefaultCharacter", (), {})
    monkeypatch.setitem(sys.modules, "evennia", evennia_mod)

    user_mod = importlib.import_module("pokemon.user")
    User = user_mod.User

    class DummyM2M:
        def __init__(self):
            self.items = set()

        def add(self, item):
            self.items.add(item)

        def remove(self, item):
            self.items.discard(item)

        def all(self):
            return list(self.items)

    class DummyBox:
        def __init__(self, name="Box 1"):
            self.name = name
            self.pokemon = DummyM2M()

    class DummyBoxes:
        def __init__(self, boxes):
            self._boxes = boxes

        def all(self):
            class _QS(list):
                def order_by(self_inner, field):
                    assert field == "id"
                    return self_inner

            return _QS(self._boxes)

    class DummyStorage:
        def __init__(self, boxes):
            self.boxes = DummyBoxes(boxes)
            self.active_pokemon = DummyM2M()
            self.stored_pokemon = DummyM2M()

        def remove_active_pokemon(self, pokemon):
            self.active_pokemon.remove(pokemon)

    class DummyPokemon:
        def __init__(self, uid, species="Pikachu"):
            self.unique_id = uid
            self.species = species
            self.nickname = ""

    user = type("DU", (), {})()
    user.trainer = object()
    box = DummyBox()
    user.storage = DummyStorage([box])
    mon = DummyPokemon("pid")
    user.storage.active_pokemon.add(mon)

    def fake_get_pokemon_by_id(pid):
        return mon if pid == "pid" else None

    def fake_get_box(index):
        return user.storage.boxes.all().order_by("id")[index - 1]

    user.get_pokemon_by_id = fake_get_pokemon_by_id
    user.get_box = fake_get_box

    monkeypatch.setattr(
        user_mod, "get_fusion_parents", lambda result: (user.trainer, object())
    )

    msg = User.deposit_pokemon(user, "pid")
    assert msg == "Pikachu is fused with you and cannot be deposited."
    assert mon in user.storage.active_pokemon.all()
    assert mon not in user.storage.stored_pokemon.all()
    assert mon not in box.pokemon.all()

