import math
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Battle, BattleParticipant, BattleType
from pokemon.dex.exp_ev_yields import GAIN_INFO
from pokemon.models.stats import trainer_battle_txp_gain


class DummyMon:
	def __init__(self, identifier="player-mon", *, nickname=None):
		self.experience = 1000
		self.level = 10
		self.growth_rate = "medium_fast"
		self.evs = {}
		self.unique_id = identifier
		self.nickname = nickname

	def save(self):
		pass


class DummyStorage:
	def __init__(self, mons):
		self._mons = mons

	def get_party(self):
		return list(self._mons)


class DummyPlayer:
	def __init__(self, mons):
		self.db = types.SimpleNamespace(exp_share=False)
		self.storage = DummyStorage(mons)
		self.messages: list[str] = []

	def msg(self, text):
		self.messages.append(text)


def _make_battle(player_mon, target, battle_type=BattleType.WILD):
	player = DummyPlayer([player_mon])
	user = Pokemon("Bulbasaur", level=5, hp=50, max_hp=50)
	user.model_id = player_mon.unique_id

	p1 = BattleParticipant("Player", [user], player=player)
	p2 = BattleParticipant("Opponent", [target], is_ai=True)
	p1.active = [user]
	p2.active = [target]

	return Battle(battle_type, [p1, p2]), player


def test_award_experience_on_faint():
	player_mon = DummyMon()
	target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)
	battle, _player = _make_battle(player_mon, target)

	battle.run_faint()

	gain = GAIN_INFO["Pikachu"]
	expected = math.floor(gain["exp"] * target.level / 7)
	assert player_mon.experience == 1000 + expected
	assert player_mon.evs.get("speed") == gain["evs"]["spe"]


def test_award_trainer_xp_on_faint():
	player_mon = DummyMon()
	target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)
	battle, player = _make_battle(player_mon, target)
	logs: list[str] = []
	battle.log_action = logs.append  # type: ignore[assignment]

	battle.run_faint()

	gain = GAIN_INFO["Pikachu"]
	expected = trainer_battle_txp_gain(gain["exp"], target.level)
	assert player.db.trainer_xp == expected
	assert player.db.txp == expected
	assert f"Trainer gained {expected} TXP!" in logs


def test_trainer_xp_flag_can_disable_payout():
	player_mon = DummyMon()
	target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)
	battle, player = _make_battle(player_mon, target)
	battle.award_txp = False

	battle.run_faint()

	assert not hasattr(player.db, "trainer_xp")
	assert not hasattr(player.db, "txp")


def test_experience_flag_can_disable_payout():
	player_mon = DummyMon()
	target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)
	battle, player = _make_battle(player_mon, target)
	battle.award_xp = False

	battle.run_faint()

	assert player_mon.experience == 1000
	assert player_mon.evs == {}
	assert player.db.trainer_xp > 0


def test_reward_message_logged_after_faint_once():
	player_mon = DummyMon(nickname="Charmander")
	target = Pokemon("Oddish", level=5, hp=0, max_hp=40)
	battle, player = _make_battle(player_mon, target)

	logs: list[str] = []
	battle.log_action = logs.append  # type: ignore[assignment]

	battle.run_faint()

	faint_message = "Oddish fainted!"
	assert faint_message in logs
	reward_msgs = [msg for msg in logs if "EXP" in msg]
	assert len(reward_msgs) == 1
	assert logs.index(reward_msgs[0]) > logs.index(faint_message)
	assert any("TXP" in msg for msg in logs)
	assert player.messages == []


def test_trainer_experience_multiplier():
	player_mon = DummyMon()
	target = Pokemon("Pikachu", level=5, hp=0, max_hp=50)
	battle, player = _make_battle(player_mon, target, BattleType.TRAINER)

	battle.run_faint()

	gain = GAIN_INFO["Pikachu"]
	expected = math.floor(1.5 * gain["exp"] * target.level / 7)
	assert player_mon.experience == 1000 + expected
	assert player.db.trainer_xp == trainer_battle_txp_gain(
		gain["exp"],
		target.level,
		trainer_battle=True,
	)
