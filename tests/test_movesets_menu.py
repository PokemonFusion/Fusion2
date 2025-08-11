import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def test_movesets_invalid_location():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_evmod = sys.modules.get("helpers.enhanced_evmenu")
    fake_evmod = types.ModuleType("helpers.enhanced_evmenu")
    class FakeMenu:
        called = False
        def __init__(self, *a, **k):
            FakeMenu.called = True
    fake_evmod.EnhancedEvMenu = FakeMenu
    sys.modules["helpers.enhanced_evmenu"] = fake_evmod

    orig_mgr = sys.modules.get("menus.moveset_manager")
    fake_mgr = types.ModuleType("menus.moveset_manager")
    sys.modules["menus.moveset_manager"] = fake_mgr

    path = os.path.join(ROOT, "commands", "player", "cmd_movesets.py")
    spec = importlib.util.spec_from_file_location("commands.player.cmd_movesets", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_evmod is not None:
        sys.modules["helpers.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("helpers.enhanced_evmenu", None)
    if orig_mgr is not None:
        sys.modules["menus.moveset_manager"] = orig_mgr
    else:
        sys.modules.pop("menus.moveset_manager", None)

    class DummyLoc:
        def __init__(self):
            self.db = types.SimpleNamespace(is_pokemon_center=False)

    class DummyCaller:
        def __init__(self):
            self.msgs = []
            self.location = DummyLoc()
        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller()
    cmd = mod.CmdMovesets()
    cmd.caller = caller
    cmd.func()

    assert not FakeMenu.called
    assert caller.msgs and "Pokémon Center" in caller.msgs[-1]


def test_number_select_opens_edit():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia

    orig_evmod = sys.modules.get("helpers.enhanced_evmenu")
    fake_evmod = types.ModuleType("helpers.enhanced_evmenu")
    fake_evmod.EnhancedEvMenu = object
    sys.modules["helpers.enhanced_evmenu"] = fake_evmod

    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)
    if orig_evmod is not None:
        sys.modules["helpers.enhanced_evmenu"] = orig_evmod
    else:
        sys.modules.pop("helpers.enhanced_evmenu", None)

    class Slots(list):
        def order_by(self, field):
            return self
        def create(self, move, slot):
            obj = types.SimpleNamespace(move=move, slot=slot)
            self.append(obj)
            return obj

    class Moveset:
        def __init__(self, index):
            self.index = index
            self.slots = Slots([types.SimpleNamespace(move=types.SimpleNamespace(name="tackle"), slot=1)])

    class Manager(list):
        def order_by(self, field):
            return sorted(self, key=lambda m: m.index)
        def all(self):
            return self
        def get_or_create(self, index):
            for m in self:
                if m.index == index:
                    return m, False
            ms = Moveset(index)
            self.append(ms)
            return ms, True

    class DummyPoke:
        def __init__(self):
            self.nickname = "Pika"
            self.name = "Pikachu"
            self.movesets = Manager([Moveset(0)])
            self.active_moveset = self.movesets[0]
            class LM:
                def __init__(self):
                    self.moves = [types.SimpleNamespace(name="ember"), types.SimpleNamespace(name="tackle")]
                def all(self):
                    return self
                def order_by(self, field):
                    return sorted(self.moves, key=lambda m: getattr(m, field))
            self.learned_moves = LM()

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(DummyPoke())
    text, _ = menu.node_manage(caller, raw_input="1")
    assert caller.ndb.ms_index == 0
    assert "Enter up to 4 moves" in text


def test_manage_lists_active_set_and_species():
    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    class DummyPoke:
        def __init__(self):
            self.nickname = ""
            self.species = "Charmander"
            class Slots(list):
                def order_by(self, field):
                    return self

            class Moveset:
                def __init__(self, index):
                    self.index = index
                    self.slots = Slots([types.SimpleNamespace(move=types.SimpleNamespace(name="scratch"), slot=1)]) if index == 0 else Slots()

            class Manager(list):
                def order_by(self, field):
                    return sorted(self, key=lambda m: m.index)
                def all(self):
                    return self

            self.movesets = Manager([Moveset(0), Moveset(1)])
            self.active_moveset = self.movesets[0]

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(DummyPoke())
    text, _ = menu.node_manage(caller)
    assert "*1." in text
    assert "Charmander" in text


def test_edit_lists_learned_moves():
    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    poke = type("DP", (), {})()
    poke.nickname = "Pika"
    poke.species = "Pikachu"
    class Slots(list):
        def order_by(self, field):
            return self
    class Moveset:
        def __init__(self):
            self.index = 0
            self.slots = Slots([types.SimpleNamespace(move=types.SimpleNamespace(name="tackle"), slot=1)])
    class Manager(list):
        def order_by(self, field):
            return self
        def all(self):
            return self
        def get_or_create(self, index):
            return self[0], False
    poke.movesets = Manager([Moveset()])
    poke.active_moveset = poke.movesets[0]
    class LM:
        def all(self):
            return self
        def order_by(self, field):
            return [types.SimpleNamespace(name="ember"), types.SimpleNamespace(name="tackle")]
    poke.learned_moves = LM()

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke, ms_index=0)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(poke)
    text, _ = menu.node_edit(caller)
    assert "Available moves" in text
    assert "ember, tackle" in text


def test_edit_rejects_invalid_move():
    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    poke = type("DP", (), {})()
    poke.nickname = "Pika"
    poke.species = "Pikachu"
    class Slots(list):
        def order_by(self, field):
            return self
        def create(self, move, slot):
            obj = types.SimpleNamespace(move=move, slot=slot)
            self.append(obj)
            return obj
    class Moveset:
        def __init__(self):
            self.index = 0
            self.slots = Slots()
    class Manager(list):
        def order_by(self, field):
            return self
        def all(self):
            return self
        def get_or_create(self, index):
            return self[0], False
    poke.movesets = Manager([Moveset()])
    poke.active_moveset = poke.movesets[0]
    class LM:
        def all(self):
            return self
        def order_by(self, field):
            return [types.SimpleNamespace(name="ember")]
    poke.learned_moves = LM()
    poke.save = lambda: None

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke, ms_index=0)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(poke)
    text, _ = menu.node_edit(caller, raw_input="tackle")
    assert any("Invalid move" in m for m in caller.msgs)
    assert len(poke.movesets[0].slots) == 0
    assert "Available moves" in text


def test_edit_rejects_duplicate_moves():
    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    poke = type("DP", (), {})()
    poke.nickname = "Pika"
    poke.species = "Pikachu"
    class Slots(list):
        def order_by(self, field):
            return self
        def create(self, move, slot):
            obj = types.SimpleNamespace(move=move, slot=slot)
            self.append(obj)
            return obj
    class Moveset:
        def __init__(self):
            self.index = 0
            self.slots = Slots()
    class Manager(list):
        def order_by(self, field):
            return self
        def all(self):
            return self
        def get_or_create(self, index):
            return self[0], False
    poke.movesets = Manager([Moveset()])
    poke.active_moveset = poke.movesets[0]

    class LM:
        def all(self):
            return self

        def order_by(self, field):
            return [types.SimpleNamespace(name="ember"), types.SimpleNamespace(name="tackle")]

    poke.learned_moves = LM()
    poke.save = lambda: None

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke, ms_index=0)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(poke)
    text, _ = menu.node_edit(caller, raw_input="tackle, tackle")
    assert any("Duplicate" in m for m in caller.msgs)
    assert len(poke.movesets[0].slots) == 0
    assert "Available moves" in text


def test_edit_back_returns_to_manage():
    import importlib
    menu = importlib.import_module("menus.moveset_manager")

    poke = type("DP", (), {})()
    poke.nickname = "Pika"
    poke.species = "Pikachu"
    class Slots(list):
        def order_by(self, field):
            return self
    class Moveset:
        def __init__(self, index):
            self.index = index
            initial = [types.SimpleNamespace(move=types.SimpleNamespace(name="tackle"), slot=1)] if index == 0 else []
            self.slots = Slots(initial)
    class Manager(list):
        def order_by(self, field):
            return sorted(self, key=lambda m: m.index)
        def all(self):
            return self
        def get_or_create(self, index):
            return self[index], False
    poke.movesets = Manager([Moveset(0), Moveset(1)])
    poke.active_moveset = poke.movesets[0]
    class LM:
        def all(self):
            return self
        def order_by(self, field):
            return [types.SimpleNamespace(name="tackle")]
    poke.learned_moves = LM()

    class DummyCaller:
        def __init__(self, poke):
            self.msgs = []
            self.ndb = types.SimpleNamespace(ms_pokemon=poke, ms_index=0)

        def msg(self, text):
            self.msgs.append(text)

    caller = DummyCaller(poke)
    text, _ = menu.node_edit(caller, raw_input="back")
    assert "Managing movesets" in text
