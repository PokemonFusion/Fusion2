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


class DummyBattleMon:
        def __init__(self, identifier, hp=10):
                self.model_id = identifier
                self.hp = hp


class DummyUser:
        def __init__(self, share, mons):
                self.db = types.SimpleNamespace(exp_share=share)
                self.storage = DummyStorage(mons)


class DummyMon:
        def __init__(self, identifier):
                self.experience = 0
                self.level = 1
                self.growth_rate = "medium_fast"
                self.evs = {}
                self.unique_id = identifier

        def save(self):
                pass


def test_award_experience_without_share():
        mons = [DummyMon("a"), DummyMon("b")]
        user = DummyUser(False, mons)
        award_experience_to_party(
                user,
                100,
                {"atk": 2},
                participants=[DummyBattleMon("a")],
        )
        assert mons[0].experience == 100
        assert mons[0].evs.get("attack") == 2
        assert mons[1].experience == 0
        assert mons[1].evs.get("attack") is None


def test_award_experience_with_share():
        mons = [DummyMon("a"), DummyMon("b"), DummyMon("c")]
        user = DummyUser(True, mons)
        award_experience_to_party(
                user,
                90,
                {"atk": 1},
                participants=[DummyBattleMon("a")],
        )
        assert mons[0].experience == 90
        assert mons[1].experience == 45
        assert mons[2].experience == 45
        assert all(m.evs.get("attack") == 1 for m in mons)
