import os
import sys
import types
import importlib.util
from dataclasses import dataclass
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "cmd_battle.py")
    spec = importlib.util.spec_from_file_location("commands.cmd_battle", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

class FakeQS(list):
    def all(self):
        return self
    def order_by(self, field):
        return self

def setup_modules():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_battle = sys.modules.get("pokemon.battle")
    battle_mod = types.ModuleType("pokemon.battle")
    class ActionType(Enum):
        MOVE = 1
    @dataclass
    class Action:
        actor: object
        action_type: ActionType
        target: object = None
        move: object = None
        priority: int = 0
    class BattleMove:
        def __init__(self, name, priority=0):
            self.name = name
            self.priority = priority
    battle_mod.Action = Action
    battle_mod.ActionType = ActionType
    battle_mod.BattleMove = BattleMove
    sys.modules["pokemon.battle"] = battle_mod

    return orig_evennia, orig_battle


def restore_modules(orig_evennia, orig_battle):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_battle is not None:
        sys.modules["pokemon.battle"] = orig_battle
    else:
        sys.modules.pop("pokemon.battle", None)


class FakeSlot:
    def __init__(self, name, slot):
        self.move = types.SimpleNamespace(name=name)
        self.slot = slot

class FakeParticipant:
    def __init__(self, name, pokemon):
        self.name = name
        self.pokemons = [pokemon]
        self.active = [pokemon]
        self.pending_action = None

class FakeBattle:
    def __init__(self, participants):
        self.participants = participants
    def opponent_of(self, part):
        for p in self.participants:
            if p is not part:
                return p
        return None

class DummyCaller:
    def __init__(self):
        self.msgs = []
        self.ndb = types.SimpleNamespace()
    def msg(self, text):
        self.msgs.append(text)


def test_battleattack_lists_moves_and_targets():
    orig_evennia, orig_battle = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1), FakeSlot('growl',2)]))
    opp = FakeParticipant('Enemy', poke)
    player = FakeParticipant('Player', poke)
    battle = FakeBattle([player, opp])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = ''
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle)
    joined = '\n'.join(caller.msgs)
    assert 'Available moves' in joined
    assert 'tackle' in joined.lower()
    assert 'enemy' in joined.lower()


def test_battleattack_auto_target_single():
    orig_evennia, orig_battle = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    enemy = FakeParticipant('Enemy', poke)
    battle = FakeBattle([player, enemy])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = 'tackle'
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert player.pending_action.target is enemy


def test_battleattack_requires_target_when_multiple():
    orig_evennia, orig_battle = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    e1 = FakeParticipant('Foe1', poke)
    e2 = FakeParticipant('Foe2', poke)
    battle = FakeBattle([player, e1, e2])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = 'tackle'
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle)
    assert player.pending_action is None
    assert 'Valid targets' in caller.msgs[-1]
