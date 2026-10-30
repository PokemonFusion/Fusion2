"""Tests for +effects/adminreveal."""

from __future__ import annotations

import importlib
import sys
import types

import pytest

from pokemon.battle.battledata import BattleData, Pokemon, Team


@pytest.fixture
def cmd_effects_env():
	orig_evennia = sys.modules.get("evennia")
	fake_evennia = types.ModuleType("evennia")

	class BaseCommand:
		def __init__(self):
			self.caller = None
			self.args = ""

	fake_evennia.Command = BaseCommand
	sys.modules["evennia"] = fake_evennia

	mod = importlib.import_module("commands.player.cmd_effects")
	mod = importlib.reload(mod)
	orig_registry = mod.REGISTRY

	class FakeRegistry:
		def __init__(self):
			self.sessions = []

		def all(self):
			return list(self.sessions)

		def sessions_for(self, caller):
			return [session for session in self.sessions if caller in getattr(session, "teamA", []) + getattr(session, "teamB", [])]

		def get_by_id(self, _ident):
			return None

	registry = FakeRegistry()
	mod.REGISTRY = registry

	try:
		yield types.SimpleNamespace(module=mod, registry=registry)
	finally:
		mod.REGISTRY = orig_registry
		sys.modules.pop("commands.player.cmd_effects", None)
		if orig_evennia is not None:
			sys.modules["evennia"] = orig_evennia
		else:
			sys.modules.pop("evennia", None)


class FakeStorage:
	def __init__(self):
		self.saved = []

	def set(self, part, value):
		if part == "data":
			self.saved.append(value)


class FakeSession:
	def __init__(self, room, data):
		self.room = room
		self.logic = types.SimpleNamespace(data=data, battle=types.SimpleNamespace(admin_ability_reveal=True))
		self.storage = FakeStorage()
		self.teamA = []
		self.teamB = []

	def get_admin_ability_reveal(self):
		return self.logic.data.admin_ability_reveal

	def set_admin_ability_reveal(self, enabled):
		self.logic.data.admin_ability_reveal = bool(enabled)
		self.logic.battle.admin_ability_reveal = bool(enabled)
		self.storage.set("data", self.logic.data.to_dict())


def _data():
	return BattleData(
		Team("A", [Pokemon("Bulbasaur", ability="Overgrow", model_id=1)]),
		Team("B", [Pokemon("Pidgey", ability="Keen Eye", model_id=2)]),
	)


def _caller(room, battle=None):
	caller = types.SimpleNamespace(
		location=room,
		ndb=types.SimpleNamespace(),
		messages=[],
	)
	if battle is not None:
		caller.ndb.battle_instance = battle
	caller.msg = caller.messages.append
	return caller


def test_adminreveal_command_uses_wizard_lock(cmd_effects_env):
	assert cmd_effects_env.module.CmdEffectsAdminReveal.locks == "cmd:perm(Wizards)"


def test_adminreveal_reports_no_active_battle(cmd_effects_env):
	cmd = cmd_effects_env.module.CmdEffectsAdminReveal()
	cmd.caller = _caller(types.SimpleNamespace())
	cmd.args = "off"

	cmd.func()

	assert cmd.caller.messages == ["No active battle found in this room."]


def test_adminreveal_toggles_only_current_battle(cmd_effects_env):
	room = types.SimpleNamespace()
	first = FakeSession(room, _data())
	second = FakeSession(room, _data())
	cmd_effects_env.registry.sessions = [first, second]

	cmd = cmd_effects_env.module.CmdEffectsAdminReveal()
	cmd.caller = _caller(room, first)
	cmd.args = "off"

	cmd.func()

	assert first.logic.data.admin_ability_reveal is False
	assert first.logic.battle.admin_ability_reveal is False
	assert first.storage.saved[-1]["admin_ability_reveal"] is False
	assert second.logic.data.admin_ability_reveal is True
	assert cmd.caller.messages == ["Admin ability reveal for this battle is now OFF."]


def test_adminreveal_no_arg_toggles_current_state(cmd_effects_env):
	room = types.SimpleNamespace()
	session = FakeSession(room, _data())
	cmd_effects_env.registry.sessions = [session]

	cmd = cmd_effects_env.module.CmdEffectsAdminReveal()
	cmd.caller = _caller(room, session)
	cmd.args = ""

	cmd.func()

	assert session.logic.data.admin_ability_reveal is False
	assert cmd.caller.messages == ["Admin ability reveal for this battle is now OFF."]
