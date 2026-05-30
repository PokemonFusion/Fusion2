import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def load_cmd_module():
	path = os.path.join(ROOT, "commands", "player", "cmd_battleuistyle.py")
	spec = importlib.util.spec_from_file_location("commands.player.cmd_battleuistyle", path)
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


def _caller(style=None):
	db = types.SimpleNamespace()
	if style is not None:
		db.battle_ui_style = style
	caller = types.SimpleNamespace(db=db, msgs=[])
	caller.msg = lambda text: caller.msgs.append(text)
	return caller


def test_battleuistyle_shows_default():
	cmd_mod = load_cmd_module()
	caller = _caller()
	cmd = cmd_mod.CmdBattleUiStyle()
	cmd.caller = caller
	cmd.args = ""
	cmd.func()
	assert "classic_modern" in caller.msgs[-1]
	assert "legacy" in caller.msgs[-1]
	assert "pf1" in caller.msgs[-1]


def test_battleuistyle_sets_classic_modern():
	cmd_mod = load_cmd_module()
	caller = _caller("legacy")
	cmd = cmd_mod.CmdBattleUiStyle()
	cmd.caller = caller
	cmd.args = "classic"
	cmd.func()
	assert not hasattr(caller.db, "battle_ui_style")
	assert caller.msgs[-1] == "Battle UI style set to classic_modern."


def test_battleuistyle_invalid():
	cmd_mod = load_cmd_module()
	caller = _caller()
	cmd = cmd_mod.CmdBattleUiStyle()
	cmd.caller = caller
	cmd.args = "widebox"
	cmd.func()
	assert "Usage" in caller.msgs[-1]
	assert "pf1" in caller.msgs[-1]


def test_battleuistyle_legacy_sets_preference():
	cmd_mod = load_cmd_module()
	caller = _caller()
	cmd = cmd_mod.CmdBattleUiStyle()
	cmd.caller = caller
	cmd.args = "legacy"
	cmd.func()
	assert caller.db.battle_ui_style == "legacy"
	assert caller.msgs[-1] == "Battle UI style set to legacy."


def test_battleuistyle_pf1_sets_preference():
	cmd_mod = load_cmd_module()
	caller = _caller()
	cmd = cmd_mod.CmdBattleUiStyle()
	cmd.caller = caller
	cmd.args = "classic-pf1"
	cmd.func()
	assert caller.db.battle_ui_style == "pf1"
	assert caller.msgs[-1] == "Battle UI style set to pf1."
