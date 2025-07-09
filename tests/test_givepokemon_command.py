# Author: codex-bot
import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Temporarily replace evennia modules while importing the command
menu_calls = []
orig_evennia = sys.modules.get("evennia")
orig_evmenu = sys.modules.get("evennia.utils.evmenu")

fake_evennia = types.ModuleType("evennia")
fake_evennia.Command = type("Command", (), {})
sys.modules["evennia"] = fake_evennia

fake_evmenu = types.ModuleType("evennia.utils.evmenu")

def FakeEvMenu(*args, **kwargs):
    menu_calls.append((args, kwargs))

fake_evmenu.EvMenu = FakeEvMenu
sys.modules["evennia.utils.evmenu"] = fake_evmenu

# Provide empty menu module
sys.modules.setdefault("menus.give_pokemon", types.ModuleType("menus.give_pokemon"))

# Load command module with stubs in place
path = os.path.join(ROOT, "commands", "cmd_givepokemon.py")
spec = importlib.util.spec_from_file_location("commands.cmd_givepokemon", path)
cmd_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cmd_mod
spec.loader.exec_module(cmd_mod)

# Restore real evennia modules
if orig_evennia is not None:
    sys.modules["evennia"] = orig_evennia
else:
    sys.modules.pop("evennia", None)
if orig_evmenu is not None:
    sys.modules["evennia.utils.evmenu"] = orig_evmenu
else:
    sys.modules.pop("evennia.utils.evmenu", None)

class DummyStorage:
    def __init__(self, count=0):
        self.active_pokemon = types.SimpleNamespace(count=lambda: count)

class DummyChar:
    def __init__(self, key, is_char=True, count=0):
        self.key = key
        self.storage = DummyStorage(count)
        self.msgs = []
        self.is_char = is_char
        self.checked_paths = []

    def is_typeclass(self, path, exact=False):
        self.checked_paths.append(path)
        return self.is_char

    def msg(self, text):
        self.msgs.append(text)

class DummyCaller(DummyChar):
    def __init__(self):
        super().__init__("Caller")
        self.search_called = None
        self.search_result = None

    def search(self, name, global_search=False):
        self.search_called = (name, global_search)
        return self.search_result


def test_rejects_non_character_target():
    menu_calls.clear()
    cmd = cmd_mod.CmdGivePokemon()
    caller = DummyCaller()
    target = DummyChar("Obj", is_char=False)
    caller.search_result = target
    cmd.caller = caller
    cmd.args = "Obj"
    cmd.func()
    assert caller.search_called == ("Obj", True)
    assert target.checked_paths and target.checked_paths[-1] == "evennia.objects.objects.DefaultCharacter"
    assert caller.msgs and "You can only give" in caller.msgs[-1]
    assert not menu_calls


def test_launches_menu_for_character():
    menu_calls.clear()
    cmd = cmd_mod.CmdGivePokemon()
    caller = DummyCaller()
    target = DummyChar("Trg")
    caller.search_result = target
    cmd.caller = caller
    cmd.args = "Trg"
    cmd.func()
    assert target.checked_paths and target.checked_paths[-1] == "evennia.objects.objects.DefaultCharacter"
    assert menu_calls
    args, kwargs = menu_calls[-1]
    assert args[0] is caller
    assert kwargs.get("target") is target


def test_party_full_blocks_menu():
    menu_calls.clear()
    cmd = cmd_mod.CmdGivePokemon()
    caller = DummyCaller()
    target = DummyChar("Full", count=6)
    caller.search_result = target
    cmd.caller = caller
    cmd.args = "Full"
    cmd.func()
    assert target.checked_paths and target.checked_paths[-1] == "evennia.objects.objects.DefaultCharacter"
    assert caller.msgs and "party is already full" in caller.msgs[-1]
    assert not menu_calls
