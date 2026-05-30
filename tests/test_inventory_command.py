import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia

	path = os.path.join(ROOT, "commands", "player", "cmd_inventory.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_inventory", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)

	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)
	return mod


class DummyTrainer:
	def list_inventory(self):
		return [types.SimpleNamespace(item_name="Potion", quantity=2)]


class DummyCaller:
	def __init__(self):
		self.trainer = DummyTrainer()
		self.msgs = []

	def msg(self, text):
		self.msgs.append(text)


def test_inventory_uses_item_text_description_fallback():
	mod = load_cmd_module()
	caller = DummyCaller()
	cmd = mod.CmdInventory()
	cmd.caller = caller

	cmd.func()

	assert caller.msgs
	assert "Potion x2 - Restores 20 HP to one Pokemon." in caller.msgs[-1]
	assert "No description available" not in caller.msgs[-1]
