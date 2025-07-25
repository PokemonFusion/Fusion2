import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_module():
    path = os.path.join(ROOT, "pokemon", "battle", "battleinstance.py")
    spec = importlib.util.spec_from_file_location("pokemon.battle.battleinstance", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_prepare_party_uses_active_moves():
    bi = load_module()
    bi._calc_stats_from_model = lambda poke: {"hp": 30}

    class FakeSlot:
        def __init__(self, name, slot):
            self.move = types.SimpleNamespace(name=name)
            self.slot = slot

    class FakeQS(list):
        def all(self):
            return self

        def order_by(self, field):
            return self

    class FakePoke:
        def __init__(self):
            self.name = "Pika"
            self.level = 5
            self.current_hp = 30
            self.activemoveslot_set = FakeQS([FakeSlot("tackle", 1), FakeSlot("growl", 2)])
            self.ability = None
            self.data = {}

    class FakeStorage:
        def get_party(self):
            return [FakePoke()]

    trainer = types.SimpleNamespace(key="Ash", storage=FakeStorage())
    session = object.__new__(bi.BattleSession)

    party = bi.BattleSession._prepare_player_party(session, trainer)
    assert [m.name for m in party[0].moves] == ["tackle", "growl"]
    assert hasattr(party[0], "activemoveslot_set")
