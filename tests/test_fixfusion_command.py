import importlib.util
import os
import sys
import types
from types import SimpleNamespace


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_cmd_fixfusion(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)

    fake_core = types.ModuleType("pokemon.models.core")
    fake_core.OwnedPokemon = types.SimpleNamespace(
        objects=types.SimpleNamespace(filter=lambda *args, **kwargs: [])
    )
    monkeypatch.setitem(sys.modules, "pokemon.models.core", fake_core)

    fake_storage = types.ModuleType("pokemon.models.storage")
    fake_storage.ActivePokemonSlot = types.SimpleNamespace(
        objects=types.SimpleNamespace(filter=lambda *args, **kwargs: [])
    )
    monkeypatch.setitem(sys.modules, "pokemon.models.storage", fake_storage)

    path = os.path.join(ROOT, "commands", "admin", "cmd_fixfusion.py")
    spec = importlib.util.spec_from_file_location("commands.admin.cmd_fixfusion", path)
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


class FakePokemon:
    def __init__(self, unique_id="mon-1", species="Pikachu"):
        self.unique_id = unique_id
        self.species = species
        self.name = species
        self.in_party = True
        self.party_slot = 2


class FakeStorage:
    def __init__(self, party):
        self.party = list(party)

    def get_party(self):
        return list(self.party)


class FakeCaller:
    def __init__(self, target):
        self.target = target
        self.messages = []

    def msg(self, text):
        self.messages.append(text)

    def search(self, query, global_search=False):
        return self.target


def test_fixfusion_can_be_rerun_without_duplicate_permanent_forms(monkeypatch):
    cmd_fixfusion = load_cmd_fixfusion(monkeypatch)
    pokemon = FakePokemon()
    target = SimpleNamespace(
        key="Ash",
        db=SimpleNamespace(fusion_species="Pikachu"),
        trainer=SimpleNamespace(),
        storage=FakeStorage([pokemon]),
    )
    caller = FakeCaller(target)
    calls = []
    monkeypatch.setattr(cmd_fixfusion, "record_fusion", lambda *args, **kwargs: calls.append((args, kwargs)))

    for _ in range(2):
        command = cmd_fixfusion.CmdFixFusion()
        command.caller = caller
        command.args = "Ash"
        command.func()

    assert target.db.fusion_id == "mon-1"
    assert target.db.fusion_kind == cmd_fixfusion.PERMANENT
    assert target.db.fusion_forms == ["mon-1"]
    assert len(calls) == 2
