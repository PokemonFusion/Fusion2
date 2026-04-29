import random

from pokemon.battle.actions import Action, ActionType
from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Battle, BattleMove, BattleParticipant, BattleType
from pokemon.dex.entities import Stats


def test_double_turn_order_and_spread_damage():
	base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)

	a1 = Pokemon("A1", hp=100, max_hp=100)
	a2 = Pokemon("A2", hp=100, max_hp=100)
	for idx, poke in enumerate((a1, a2), start=1):
		poke.base_stats = base
		poke.num = idx
		poke.types = ["Normal"]

	b1 = Pokemon("B1", hp=100, max_hp=100)
	b2 = Pokemon("B2", hp=100, max_hp=100)
	for idx, poke in enumerate((b1, b2), start=3):
		poke.base_stats = base
		poke.num = idx
		poke.types = ["Normal"]

	spread_move = BattleMove(
		"Surf",
		power=40,
		accuracy=100,
		type="Water",
		raw={
			"name": "Surf",
			"basePower": 40,
			"type": "Water",
			"category": "Special",
			"accuracy": 100,
			"target": "allAdjacentFoes",
		},
	)

	p1 = BattleParticipant("P1", [a1, a2], is_ai=False, max_active=2)
	p2 = BattleParticipant("P2", [b1, b2], is_ai=False, max_active=2)
	p1.active = [a1, a2]
	p2.active = [b1, b2]

	p1.pending_action = [
		Action(
			actor=p1,
			action_type=ActionType.MOVE,
			target=p2,
			move=spread_move,
			priority=spread_move.priority,
			pokemon=a1,
		)
	]

	battle = Battle(BattleType.WILD, [p1, p2])
	random.seed(0)
	battle.run_turn()

	damage_first = 100 - b1.hp
	damage_second = 100 - b2.hp
	assert damage_second == int(damage_first * 0.75)
