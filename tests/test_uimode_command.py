import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_uimode.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_uimode", path)
	mod = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = mod
	spec.loader.exec_module(mod)
	return mod


def setup_module():
	global orig_evennia
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")
	fake_evennia.Command = type("Command", (), {})
	sys.modules["evennia"] = fake_evennia


def teardown_module():
	if orig_evennia is not None:
		sys.modules["evennia"] = orig_evennia
	else:
		sys.modules.pop("evennia", None)


def _caller(**attrs):
	db = types.SimpleNamespace(**attrs)
	caller = types.SimpleNamespace(db=db, msgs=[])
	caller.msg = lambda text: caller.msgs.append(text)
	return caller


def test_uimode_ascii_sets_simple_layout_and_ascii_battle_symbols():
	cmd_mod = load_cmd_module()
	caller = _caller(ui_mode="fancy", battle_ascii_symbols=False)
	cmd = cmd_mod.CmdUiMode()
	cmd.caller = caller
	cmd.args = "ascii"

	cmd.func()

	assert caller.db.ui_mode == "simple"
	assert caller.db.battle_ascii_symbols is True
	assert "ascii-safe" in caller.msgs[-1]


def test_uimode_unicode_sets_fancy_layout_and_unicode_battle_symbols():
	cmd_mod = load_cmd_module()
	caller = _caller(ui_mode="simple", battle_ascii_symbols=True)
	cmd = cmd_mod.CmdUiMode()
	cmd.caller = caller
	cmd.args = "unicode"

	cmd.func()

	assert caller.db.ui_mode == "fancy"
	assert caller.db.battle_ascii_symbols is False
	assert "unicode" in caller.msgs[-1]


def test_uimode_status_includes_ascii_symbol_preference():
	cmd_mod = load_cmd_module()
	caller = _caller(ui_mode="boxed", battle_ascii_symbols=True)
	cmd = cmd_mod.CmdUiMode()
	cmd.caller = caller
	cmd.args = ""

	cmd.func()

	assert caller.msgs[-1] == "Current UI mode: boxed. ASCII symbols: on."
