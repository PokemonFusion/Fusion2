"""Tests for Showdown-style callback and item runtime wiring."""

from __future__ import annotations

from types import SimpleNamespace

from .helpers import build_battle, load_modules, physical_move


def _battle_action(actor, action_type, **kwargs):
	modules = load_modules()
	Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
	return Action(actor=actor, action_type=action_type, **kwargs)


def test_item_call_resolves_string_callback():
	load_modules()
	from pokemon.dex.entities import Item

	item = Item.from_dict(
		"Assault Vest",
		{"name": "Assault Vest", "onModifySpD": "Assaultvest.onModifySpD"},
	)

	assert item.call("onModifySpD", 100, pokemon=object()) == 150


def test_ability_call_resolves_string_callback():
	load_modules()
	from pokemon.dex.entities import Ability

	ability = Ability.from_dict(
		"Prankster",
		{"name": "Prankster", "onModifyPriority": "Prankster.onModifyPriority"},
	)
	move = SimpleNamespace(category="Status")

	assert ability.call("onModifyPriority", 0, pokemon=object(), move=move) == 0.1


def test_eat_item_consumes_berry_and_sets_flags():
	battle, attacker, _ = build_battle()
	load_modules()
	from pokemon.dex.entities import Item

	berry = Item.from_dict(
		"Aguav Berry",
		{
			"name": "Aguav Berry",
			"onEat": "Aguavberry.onEat",
			"onTryEatItem": "Aguavberry.onTryEatItem",
		},
	)
	attacker.hp = 40
	battle.set_item(attacker, berry)

	assert battle.eat_item(attacker) is True
	assert attacker.item is None
	assert attacker.consumed_berry is True
	assert attacker.last_consumed_item == "Aguav Berry"
	assert attacker.hp > 40


def test_take_item_respects_on_take_item_blockers():
	battle, attacker, _ = build_battle()
	load_modules()
	from pokemon.dex.entities import Item

	stone = Item.from_dict(
		"Abomasite",
		{
			"name": "Abomasite",
			"megaEvolves": "Abomasnow",
			"onTakeItem": "Abomasite.onTakeItem",
		},
	)
	attacker.name = "Abomasnow"
	battle.set_item(attacker, stone)

	assert battle.take_item(attacker, source=object()) is None
	assert getattr(attacker.item, "name", None) == "Abomasite"


def test_move_on_modify_move_runs_before_execution():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	ally = modules["Pokemon"]("Ally", hp=100, max_hp=100)
	ally.base_stats = attacker.base_stats
	ally.party = []
	attacker.party = [attacker, ally]
	move = BattleMove(name="Beat Up", raw={"category": "Physical"})

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert move.raw.get("multihit") == 2


def test_move_on_move_fail_triggers_crash_damage():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	defender.volatiles["protect"] = True
	move = BattleMove(name="Axe Kick", raw={"category": "Physical"})
	start_hp = attacker.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.hp == start_hp - (attacker.max_hp // 2)


def test_after_move_secondary_self_hook_runs():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	attacker.boosts = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "accuracy": 0, "evasion": 0}
	defender.hp = 1
	move = BattleMove(name="Fell Stinger", raw={"category": "Physical", "basePower": 50})

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.boosts.get("attack", attacker.boosts.get("atk", 0)) >= 3


def test_trainer_item_action_supports_potion():
	modules = load_modules()
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	actor = battle.participants[0]
	attacker.hp = 50
	actor.inventory = {"Potion": 1}

	action = _battle_action(
		actor,
		ActionType.ITEM,
		target=actor,
		item="Potion",
		pokemon=attacker,
	)
	battle.execute_item(action)

	assert attacker.hp == 70
	assert actor.inventory.get("Potion", 0) == 0
