import importlib.util
import os
import sys
import types

import pytest

from utils import fusion as fusion_utils


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeConfigManager:
    def __init__(self):
        self.data = {}

    def conf(self, key=None, value=None, delete=False, default=None):
        if delete:
            self.data.pop(key, None)
            return None
        if value is not None:
            self.data[key] = value
            return None
        return self.data.get(key, default() if callable(default) else default)


class FakeServerConfig:
    objects = FakeConfigManager()


class DummyCaller:
    def __init__(self):
        self.msgs = []

    def msg(self, text):
        self.msgs.append(text)


@pytest.fixture(autouse=True)
def fake_server_config(monkeypatch):
    FakeServerConfig.objects = FakeConfigManager()
    monkeypatch.setattr(fusion_utils, "_server_config", lambda: FakeServerConfig)


def load_cmd_module():
    path = os.path.join(ROOT, "commands", "admin", "cmd_fusionboost.py")
    spec = importlib.util.spec_from_file_location("commands.admin.cmd_fusionboost", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def with_fake_evennia():
    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    sys.modules["evennia"] = fake_evennia
    return orig_evennia


def restore_evennia(orig_evennia):
    if orig_evennia is not None:
        sys.modules["evennia"] = orig_evennia
    else:
        sys.modules.pop("evennia", None)


def test_fusion_boost_setting_defaults_enabled_and_can_toggle():
    assert fusion_utils.is_fusion_boost_enabled() is True

    assert fusion_utils.set_fusion_boost_enabled(False) is False
    assert fusion_utils.is_fusion_boost_enabled() is False

    assert fusion_utils.set_fusion_boost_enabled(None) is True
    assert fusion_utils.is_fusion_boost_enabled() is True


def test_active_fusion_boost_respects_admin_setting():
    from utils.pokemon_utils import build_battle_pokemon_from_model

    class DummyModel:
        name = "Pikachu"
        species = "Pikachu"
        level = 20
        current_hp = 35
        max_hp = 35
        moves = ["Tackle"]
        gender = "N"
        _pf2_active_fusion = True
        _pf2_fusion_kind = fusion_utils.PERMANENT

    fusion_utils.set_fusion_boost_enabled(False)
    disabled = build_battle_pokemon_from_model(DummyModel())

    fusion_utils.set_fusion_boost_enabled(True)
    enabled = build_battle_pokemon_from_model(DummyModel())

    disabled_attack = disabled.getStat("atk", True, True)
    assert disabled_attack > 0
    assert getattr(disabled, "_pf2_active_fusion") is True
    assert enabled.getStat("atk", True, True) == disabled_attack * 11 // 10
    assert enabled.getStat("hp", True, True) == disabled.getStat("hp", True, True)


def test_fusionboost_command_sets_and_clears_setting():
    orig_evennia = with_fake_evennia()
    orig_cmd_module = sys.modules.get("commands.admin.cmd_fusionboost")
    cmd_mod = load_cmd_module()

    try:
        cmd = cmd_mod.CmdFusionBoost()
        cmd.caller = DummyCaller()
        cmd.args = "off"
        cmd.parse()
        cmd.func()

        assert fusion_utils.is_fusion_boost_enabled() is False
        assert "disabled" in cmd.caller.msgs[-1].lower()

        cmd.args = "clear"
        cmd.parse()
        cmd.func()

        assert fusion_utils.is_fusion_boost_enabled() is True
        assert "cleared" in cmd.caller.msgs[-1].lower()
    finally:
        restore_evennia(orig_evennia)
        if orig_cmd_module is not None:
            sys.modules["commands.admin.cmd_fusionboost"] = orig_cmd_module
        else:
            sys.modules.pop("commands.admin.cmd_fusionboost", None)
