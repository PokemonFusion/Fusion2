import importlib.util
import os
import sys
import types
from dataclasses import dataclass
from enum import Enum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "player", "cmd_battle_item.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_battle_item", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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
    sys.modules["evennia.utils"] = utils_mod
    sys.modules["evennia.utils.evmenu"] = evmenu_mod
    sys.modules["evennia"] = fake_evennia

    orig_battle = sys.modules.get("pokemon.battle")
    battle_mod = types.ModuleType("pokemon.battle")
    class ActionType(Enum):
        ITEM = 3
    @dataclass
    class Action:
        actor: object
        action_type: ActionType
        target: object = None
        item: str | None = None
        priority: int = 0
    battle_mod.Action = Action
    battle_mod.ActionType = ActionType
    battle_mod.BattleMove = type("BattleMove", (), {})
    sys.modules["pokemon.battle"] = battle_mod

    orig_battleinstance = sys.modules.get("pokemon.battle.battleinstance")
    bi_mod = types.ModuleType("pokemon.battle.battleinstance")
    class BattleSession:
        @staticmethod
        def ensure_for_player(caller):
            return getattr(caller.ndb, "battle_instance", None)
    bi_mod.BattleSession = BattleSession
    sys.modules["pokemon.battle.battleinstance"] = bi_mod

    return orig_evennia, orig_battle, orig_battleinstance


def restore_modules(e, b, bi):
    if e is not None:
        sys.modules["evennia"] = e
    else:
        sys.modules.pop("evennia", None)
    sys.modules.pop("evennia.utils.evmenu", None)
    sys.modules.pop("evennia.utils", None)
    if b is not None:
        sys.modules["pokemon.battle"] = b
    else:
        sys.modules.pop("pokemon.battle", None)
    if bi is not None:
        sys.modules["pokemon.battle.battleinstance"] = bi
    else:
        sys.modules.pop("pokemon.battle.battleinstance", None)


class FakeParticipant:
    def __init__(self, name, poke):
        self.name = name
        self.pokemons = [poke]
        self.active = [poke]
        self.pending_action = None

class FakeBattle:
    def __init__(self, participants):
        self.participants = participants
    def opponent_of(self, part):
        for p in self.participants:
            if p is not part:
                return p
        return None

class FakeInstance:
    def __init__(self, battle):
        self.battle = battle
        self.queued = []

    def queue_item(self, item_name, target="B1", caller=None):
        self.queued.append((item_name, target))

class DummyCaller:
    def __init__(self):
        self.msgs = []
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace(battle_control=True)
        self.has_item = lambda name: True
        self.trainer = types.SimpleNamespace(remove_item=lambda name: None)
    def msg(self, text):
        self.msgs.append(text)


def test_battleitem_persists_declare_via_queue_item():
    e, b, bi = setup_modules()
    cmd_mod = load_cmd_module()

    poke = types.SimpleNamespace()
    player = FakeParticipant("Player", poke)
    enemy = FakeParticipant("Enemy", poke)
    battle = FakeBattle([player, enemy])
    inst = FakeInstance(battle)
    caller = DummyCaller()
    caller.ndb.battle_instance = inst

    cmd = cmd_mod.CmdBattleItem()
    cmd.caller = caller
    cmd.args = "potion"
    cmd.func()

    restore_modules(e, b, bi)
    assert isinstance(player.pending_action, cmd_mod.Action)
    assert inst.queued == [("potion", "B1")]

