import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.models.stats import award_experience_to_party


class DummyManager:
	def __init__(self, mons):
		self._mons = mons

	def all(self):
		return list(self._mons)


class DummyStorage:
	def __init__(self, mons):
		self.active_pokemon = DummyManager(mons)


class DummyUser:
	def __init__(self, share, mons):
		self.db = types.SimpleNamespace(exp_share=share)
		self.storage = DummyStorage(mons)


class DummyMon:
	def __init__(self):
		self.experience = 0
		self.level = 1
		self.growth_rate = "medium_fast"
		self.evs = {}

	def save(self):
		pass


def test_award_experience_without_share():
	mons = [DummyMon(), DummyMon()]
	user = DummyUser(False, mons)
	award_experience_to_party(user, 100, {"atk": 2})
	assert mons[0].experience == 100
	assert mons[0].evs.get("attack") == 2
	assert mons[1].experience == 0


def test_award_experience_with_share():
	mons = [DummyMon(), DummyMon(), DummyMon()]
	user = DummyUser(True, mons)
	award_experience_to_party(user, 90, {"atk": 1})
	assert all(m.experience == 30 for m in mons)
	assert all(m.evs.get("attack") == 1 for m in mons)
