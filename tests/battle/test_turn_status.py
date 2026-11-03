from pokemon.battle.actions import Action, ActionType
from pokemon.battle.battledata import Move, Pokemon
from pokemon.battle.engine import Battle, BattleMove, BattleParticipant, BattleType
from pokemon.dex.entities import Stats


class FixedRng:
	def __init__(self, value):
		self.value = value

	def random(self):
		return self.value

	def randint(self, start, end):
		return start


def setup_battle(status=None, rng_value=0.5):
	p1 = Pokemon("P1", level=1, hp=100, max_hp=100, moves=[Move("Tackle")])
	p2 = Pokemon("P2", level=1, hp=100, max_hp=100, moves=[Move("Tackle")])
	base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	for poke, num in ((p1, 1), (p2, 2)):
		poke.base_stats = base
		poke.num = num
		poke.types = ["Normal"]
	if status:
		p1.status = status
	part1 = BattleParticipant("P1", [p1], is_ai=False)
	part2 = BattleParticipant("P2", [p2], is_ai=False)
	part1.active = [p1]
	part2.active = [p2]
	move = BattleMove(
		"Tackle",
		power=40,
		accuracy=100,
		type="Normal",
		raw={
			"name": "Tackle",
			"basePower": 40,
			"type": "Normal",
			"category": "Physical",
			"accuracy": 100,
		},
	)
	part1.pending_action = Action(
		actor=part1,
		action_type=ActionType.MOVE,
		target=part2,
		move=move,
		priority=move.priority,
		pokemon=p1,
	)
	return Battle(BattleType.WILD, [part1, part2], rng=FixedRng(rng_value)), p1, p2


def test_paralysis_can_prevent_move():
	"""Paralysis should occasionally stop a Pokemon from acting."""
	battle, p1, p2 = setup_battle("par", rng_value=0.1)
	battle.run_turn()
	assert p2.hp == 100


def test_frozen_blocks_move():
	"""Frozen status should prevent action unless the Pokemon thaws."""
	battle, p1, p2 = setup_battle("frz", rng_value=0.5)
	battle.run_turn()
	assert p2.hp == 100
	assert p1.status == "frz"


def test_frozen_can_thaw_and_move():
	"""Frozen Pokemon may thaw out and attack."""
	battle, p1, p2 = setup_battle("frz", rng_value=0.1)
	battle.run_turn()
	assert p2.hp < 100
	assert p1.status == 0
