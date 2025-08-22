"""Cmdset and toggle for exposing +effects during testing."""

from __future__ import annotations

from evennia import CmdSet, Command

from ..player.cmd_effects import CmdEffects


class TestEffectsCmdSet(CmdSet):
	key = "TestEffectsCmdSet"
	priority = 100

	def at_cmdset_creation(self):
		self.add(CmdEffects())


class CmdToggleTestEffects(Command):
	"""+toggletesteffects
	Attach or detach the test effects cmdset (adds +effects for testing)."""

	key = "+toggletesteffects"
	locks = "cmd:perm(Builder) or perm(Admin)"

	def func(self):
		cs = TestEffectsCmdSet()
		if self.caller.cmdset.has_cmdset(cs, must_be_default=False):
			self.caller.cmdset.remove(cs)
			self.caller.msg("TestEffectsCmdSet removed.")
		else:
			self.caller.cmdset.add(cs)
			self.caller.msg("TestEffectsCmdSet added. Use +effects to view effects.")
