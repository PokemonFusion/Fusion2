import random

from pokemon.battle.actions import Action, ActionType
from pokemon.battle.battledata import Pokemon
from pokemon.battle.engine import Battle, BattleMove, BattleParticipant, BattleType
from pokemon.dex.entities import Stats


def setup_battle(target_volatiles=None, target_types=None):
	user = Pokemon("User", hp=100, max_hp=100)
	target = Pokemon("Target", hp=100, max_hp=100)
	base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
	for poke, num in ((user, 1), (target, 2)):
		poke.base_stats = base
		poke.num = num
		poke.types = ["Normal"]
	if target_types:
		target.types = target_types
	if target_volatiles:
		target.volatiles = dict(target_volatiles)
	move = BattleMove(
		"Tackle",
		power=40,
		accuracy=100,
		type="Normal",
		pp=5,
		raw={
			"name": "Tackle",
			"basePower": 40,
			"type": "Normal",
			"category": "Physical",
			"accuracy": 100,
		},
	)
	p1 = BattleParticipant("P1", [user], is_ai=False)
	p2 = BattleParticipant("P2", [target], is_ai=False)
	p1.active = [user]
	p2.active = [target]
	action = Action(
		actor=p1,
		action_type=ActionType.MOVE,
		target=p2,
		move=move,
		priority=move.priority,
		pokemon=user,
	)
	p1.pending_action = action
	battle = Battle(BattleType.WILD, [p1, p2])
	random.seed(0)
	return battle, user, target, move


def test_protect_blocks_damage_and_consumes_pp():
	battle, user, target, move = setup_battle(target_volatiles={"protect": True})
	battle.start_turn()
	battle.run_switch()
	battle.run_after_switch()
	battle.run_move()
	assert target.hp == 100
	assert move.pp == 4
	assert user.tempvals.get("moved") is True


def test_substitute_blocks_damage():
	battle, user, target, move = setup_battle(target_volatiles={"substitute": True})
	battle.start_turn()
	battle.run_switch()
	battle.run_after_switch()
	battle.run_move()
	assert target.hp == 100
	assert move.pp == 4


def test_substitute_takes_damage():
	battle, user, target, move = setup_battle(target_volatiles={"substitute": {"hp": 25}})
	battle.start_turn()
	battle.run_switch()
	battle.run_after_switch()
	battle.run_move()
	assert target.hp == 100
	assert target.volatiles["substitute"]["hp"] == 21


def test_immunity_blocks_damage():
	battle, user, target, move = setup_battle(target_types=["Ghost"])
	battle.start_turn()
	battle.run_switch()
	battle.run_after_switch()
	battle.run_move()
	assert target.hp == 100
	assert move.pp == 4
