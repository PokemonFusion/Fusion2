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
    utils_mod = types.ModuleType("evennia.utils")
    evmenu_mod = types.ModuleType("evennia.utils.evmenu")

    def fake_get_input(caller, prompt, callback, session=None, *a, **kw):
        caller.msg(prompt)
        caller.ndb.last_prompt_callback = callback

    evmenu_mod.get_input = fake_get_input
    utils_mod.evmenu = evmenu_mod

    fake_evennia.utils = utils_mod
    sys.modules["evennia"] = fake_evennia
    sys.modules["evennia.utils"] = utils_mod
    sys.modules["evennia.utils.evmenu"] = evmenu_mod

    orig_battle = sys.modules.get("pokemon.battle")
    orig_battleinstance = sys.modules.get("pokemon.battle.battleinstance")
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

    battleinstance_mod = types.ModuleType("pokemon.battle.battleinstance")
    class BattleSession:
        @staticmethod
        def ensure_for_player(caller):
            return getattr(caller.ndb, "battle_instance", None)
    battleinstance_mod.BattleSession = BattleSession
    sys.modules["pokemon.battle.battleinstance"] = battleinstance_mod

    return orig_evennia, orig_battle, orig_battleinstance


def restore_modules(orig_evennia, orig_battle, orig_battleinstance):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
        try:
            import importlib

            real_evennia = importlib.import_module("evennia")
            sys.modules["evennia"] = real_evennia
        except Exception:
            evennia = types.ModuleType("evennia")
            evennia.search_object = lambda *a, **k: []
            evennia.create_object = lambda *a, **k: None
            sys.modules["evennia"] = evennia
    sys.modules.pop("evennia.utils.evmenu", None)
    sys.modules.pop("evennia.utils", None)
    if orig_battle is not None:
        sys.modules["pokemon.battle"] = orig_battle
    else:
        sys.modules.pop("pokemon.battle", None)
    if orig_battleinstance is not None:
        sys.modules["pokemon.battle.battleinstance"] = orig_battleinstance
    else:
        sys.modules.pop("pokemon.battle.battleinstance", None)


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
        self.ran = False
    def opponent_of(self, part):
        for p in self.participants:
            if p is not part:
                return p
        return None
    def run_turn(self):
        self.ran = True

class FakeInstance:
    def __init__(self, battle):
        self.battle = battle
        self.ran = False
    def run_turn(self):
        self.ran = True
        self.battle.run_turn()

class DummyCaller:
    def __init__(self):
        self.msgs = []
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace(battle_control=True)
    def msg(self, text):
        self.msgs.append(text)


def test_battleattack_lists_moves_and_targets():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1), FakeSlot('growl',2)]))
    opp = FakeParticipant('Enemy', poke)
    player = FakeParticipant('Player', poke)
    battle = FakeBattle([player, opp])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = ''
    cmd.parse()
    cmd.func()
    joined = '\n'.join(caller.msgs)
    assert 'Pick an attack' in joined
    assert 'tackle' in joined.lower()

    cb = caller.ndb.last_prompt_callback
    assert cb is not None
    cb(caller, '', 'tackle')

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert player.pending_action.target is opp


def test_battleattack_auto_target_single():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    enemy = FakeParticipant('Enemy', poke)
    battle = FakeBattle([player, enemy])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = 'tackle'
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert player.pending_action.target is enemy


def test_battleattack_prompt_runs_turn_after_callback():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    enemy = FakeParticipant('Enemy', poke)
    battle = FakeBattle([player, enemy])
    inst = FakeInstance(battle)
    caller = DummyCaller()
    caller.ndb.battle_instance = inst
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = ''
    cmd.parse()
    cmd.func()
    assert inst.ran is False
    assert battle.ran is False

    cb = caller.ndb.last_prompt_callback
    assert cb is not None
    cb(caller, '', 'tackle')

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert inst.ran is True
    assert battle.ran is True


def test_battleattack_arg_runs_turn():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    enemy = FakeParticipant('Enemy', poke)
    battle = FakeBattle([player, enemy])
    inst = FakeInstance(battle)
    caller = DummyCaller()
    caller.ndb.battle_instance = inst
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = 'tackle'
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert inst.ran is True
    assert battle.ran is True


def test_battleattack_requires_target_when_multiple():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(activemoveslot_set=FakeQS([FakeSlot('tackle',1)]))
    player = FakeParticipant('Player', poke)
    e1 = FakeParticipant('Foe1', poke)
    e2 = FakeParticipant('Foe2', poke)
    battle = FakeBattle([player, e1, e2])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = 'tackle'
    cmd.parse()
    cmd.func()

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert player.pending_action is None
    assert 'Valid targets' in caller.msgs[-1]


def test_battleattack_falls_back_to_move_list():
    orig_evennia, orig_battle, orig_bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace(moves=[types.SimpleNamespace(name='tackle'), types.SimpleNamespace(name='growl')])
    player = FakeParticipant('Player', poke)
    enemy = FakeParticipant('Enemy', poke)
    battle = FakeBattle([player, enemy])
    caller = DummyCaller()
    caller.ndb.battle_instance = types.SimpleNamespace(battle=battle)
    caller.db.battle_control = True

    cmd = cmd_mod.CmdBattleAttack()
    cmd.caller = caller
    cmd.args = ''
    cmd.parse()
    cmd.func()
    msg = '\n'.join(caller.msgs)
    assert 'tackle' in msg.lower()
    assert '/----------------[A]' in msg

    cb = caller.ndb.last_prompt_callback
    assert cb is not None
    cb(caller, '', 'A')

    restore_modules(orig_evennia, orig_battle, orig_bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert player.pending_action.target is enemy
