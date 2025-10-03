import os
import sys
import types
import uuid

import django
import pytest


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from pokemon.battle.battleinstance import BattleSession
from pokemon.models.core import OwnedPokemon


class InMemoryManager:
    """Minimal stand-in for the Django manager used in tests."""

    def __init__(self, model):
        self.model = model
        self.store: dict[str, OwnedPokemon] = {}
        self.last_lookup = None

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        uid = kwargs.get("unique_id") or str(uuid.uuid4())
        obj.unique_id = uid
        obj._deleted = False
        self.store[uid] = obj

        manager = self

        def _delete(instance):
            instance._deleted = True
            manager.store.pop(instance.unique_id, None)

        obj.delete = types.MethodType(_delete, obj)  # type: ignore[attr-defined]
        return obj

    def get(self, *args, **kwargs):
        if args:
            key = args[0]
        else:
            key = kwargs.get("unique_id")
        if key is None:
            raise KeyError("unique_id is required")
        self.last_lookup = key
        return self.store[key]

    def filter(self, **kwargs):
        matches = []
        for obj in self.store.values():
            include = True
            for key, value in kwargs.items():
                attr = key.split("__", 1)[0]
                if getattr(obj, attr, None) != value:
                    include = False
                    break
            if include:
                matches.append(obj)

        manager = self

        class _QuerySet(list):
            def delete(self_inner):
                for item in list(self_inner):
                    manager.store.pop(item.unique_id, None)

            def filter(self_inner, **kw):
                return manager.filter(**kw)

        return _QuerySet(matches)


class DummyRoom:
    def __init__(self):
        self.id = 1
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()


class DummyPlayer:
    def __init__(self, room):
        self.key = "Player"
        self.id = 99
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.location = room

    def msg(self, *args, **kwargs):
        return None

    def move_to(self, destination, quiet=False):
        self.location = destination


class DummyClearRelation:
    def __init__(self):
        self.cleared = False

    def clear(self):
        self.cleared = True


class DummyDeleteRelation:
    def __init__(self):
        self.deleted = False

    def all(self):
        return self

    def delete(self):
        self.deleted = True


class DummyActiveMoveset:
    def __init__(self):
        self.deleted = False

    def delete(self):
        self.deleted = True


@pytest.mark.parametrize("flag", ["is_wild", "is_battle_instance"])
def test_wild_encounter_cleans_up_owned_pokemon(monkeypatch, flag):
    handler = types.SimpleNamespace(register=lambda *a, **k: None, unregister=lambda *a, **k: None)
    monkeypatch.setattr("pokemon.battle.battleinstance.battle_handler", handler, raising=False)

    stub_models = types.ModuleType("pokemon.models")
    stub_models.OwnedPokemon = OwnedPokemon
    monkeypatch.setitem(sys.modules, "pokemon.models", stub_models)

    orig_delete_if_wild = OwnedPokemon.delete_if_wild
    call_info: dict[str, object] = {}

    def _tracking_delete(self):
        call_info["called"] = True
        result = orig_delete_if_wild(self)
        call_info["result"] = result
        return result

    monkeypatch.setattr(OwnedPokemon, "delete_if_wild", _tracking_delete, raising=False)

    manager = InMemoryManager(OwnedPokemon)
    monkeypatch.setattr(OwnedPokemon, "objects", manager, raising=False)
    monkeypatch.setattr(OwnedPokemon, "save", lambda self, *a, **k: None, raising=False)

    wild = manager.create(species="Pidgey", level=3)
    setattr(wild, flag, True)
    wild.trainer = None
    wild.ai_trainer = None

    learned = DummyClearRelation()
    slots = DummyDeleteRelation()
    movesets = DummyDeleteRelation()
    boosts = DummyDeleteRelation()
    active_moveset = DummyActiveMoveset()

    monkeypatch.setattr(OwnedPokemon, "learned_moves", learned, raising=False)
    monkeypatch.setattr(OwnedPokemon, "activemoveslot_set", slots, raising=False)
    monkeypatch.setattr(OwnedPokemon, "movesets", movesets, raising=False)
    monkeypatch.setattr(OwnedPokemon, "pp_boosts", boosts, raising=False)
    monkeypatch.setattr(OwnedPokemon, "active_moveset", active_moveset, raising=False)

    room = DummyRoom()
    player = DummyPlayer(room)

    session = BattleSession(player)
    session.logic = types.SimpleNamespace(
        state=None,
        battle=types.SimpleNamespace(participants=[]),
        data=None,
    )
    session.temp_pokemon_ids = [wild.unique_id]

    session.end()

    assert manager.last_lookup == wild.unique_id
    assert call_info.get("called") is True
    assert call_info.get("result") is True
    assert wild._deleted is True
    assert wild.unique_id not in manager.store
    assert learned.cleared
    assert slots.deleted
    assert movesets.deleted
    assert boosts.deleted
    assert active_moveset.deleted
    assert session.temp_pokemon_ids == []
