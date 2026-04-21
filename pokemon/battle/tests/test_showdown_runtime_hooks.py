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

	assert battle.eat_item(attacker, force=True) is True
	assert attacker.item is None
	assert getattr(attacker.consumed_berry, "name", None) == "Aguav Berry"
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


def test_move_on_hit_field_dispatch_runs_haze():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()

	attacker.boosts["attack"] = 2
	defender.boosts["defense"] = -1
	move = BattleMove(
		name="Haze",
		raw={"category": "Status", "onHitField": "Haze.onHitField"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert all(value == 0 for value in attacker.boosts.values())
	assert all(value == 0 for value in defender.boosts.values())


def test_move_on_hit_side_dispatch_runs_quick_guard():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()

	move = BattleMove(
		name="Quick Guard",
		raw={"category": "Status", "onHitSide": "Quickguard.onHitSide"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.side, "volatiles", {}).get("quickguard") is True
	assert getattr(defender.side, "volatiles", {}).get("quickguard") is None


def test_move_on_after_hit_knock_off_removes_item():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	leftovers = Item.from_dict("Leftovers", {"name": "Leftovers"})
	battle.set_item(defender, leftovers)
	move = BattleMove(
		name="Knock Off",
		raw={"category": "Physical", "basePower": 65, "onAfterHit": "Knockoff.onAfterHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert defender.item is None
	assert defender.last_removed_item == "Leftovers"
	assert defender.knocked_off is True


def test_move_on_after_hit_thief_steals_item():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	leftovers = Item.from_dict("Leftovers", {"name": "Leftovers"})
	battle.set_item(defender, leftovers)
	move = BattleMove(
		name="Thief",
		raw={"category": "Physical", "basePower": 60, "onAfterHit": "Thief.onAfterHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "name", None) == "Leftovers"
	assert defender.item is None


def test_fling_removes_item_only_after_successful_hit():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	iron_ball = Item.from_dict("Iron Ball", {"name": "Iron Ball"})
	iron_ball.fling_power = 130
	battle.set_item(attacker, iron_ball)
	move = BattleMove(
		name="Fling",
		raw={
			"category": "Physical",
			"basePower": 0,
			"onPrepareHit": "Fling.onPrepareHit",
			"onAfterHit": "Fling.onAfterHit",
		},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.item is None
	assert getattr(attacker.last_used_item, "name", None) == "Iron Ball"


def test_fling_keeps_item_when_move_is_blocked():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	defender.volatiles["protect"] = True
	iron_ball = Item.from_dict("Iron Ball", {"name": "Iron Ball"})
	iron_ball.fling_power = 130
	battle.set_item(attacker, iron_ball)
	move = BattleMove(
		name="Fling",
		raw={
			"category": "Physical",
			"basePower": 0,
			"onPrepareHit": "Fling.onPrepareHit",
			"onAfterHit": "Fling.onAfterHit",
		},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "name", None) == "Iron Ball"
	assert attacker.last_used_item is None


def test_move_on_hit_trick_swaps_items():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	choice_band = Item.from_dict("Choice Band", {"name": "Choice Band"})
	leftovers = Item.from_dict("Leftovers", {"name": "Leftovers"})
	battle.set_item(attacker, choice_band)
	battle.set_item(defender, leftovers)
	move = BattleMove(
		name="Trick",
		raw={"category": "Status", "onHit": "Trick.onHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "name", None) == "Leftovers"
	assert getattr(defender.item, "name", None) == "Choice Band"


def test_choice_item_locks_user_into_first_move():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	choice_band = Item.from_dict("Choice Band", {"name": "Choice Band"})
	battle.set_item(attacker, choice_band)
	first_move = BattleMove(name="Tackle", raw={"category": "Physical", "basePower": 40})
	second_move = BattleMove(name="Scratch", raw={"category": "Physical", "basePower": 40})

	first_action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=first_move,
		pokemon=attacker,
	)
	battle.use_move(first_action)

	assert attacker.choice_locked_move == "tackle"
	hp_after_first = defender.hp

	second_action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=second_move,
		pokemon=attacker,
	)
	battle.use_move(second_action)

	assert defender.hp == hp_after_first
	assert attacker.choice_locked_move == "tackle"


def test_choice_lock_clears_when_item_is_removed():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	choice_specs = Item.from_dict("Choice Specs", {"name": "Choice Specs"})
	battle.set_item(attacker, choice_specs)
	move = BattleMove(name="Swift", raw={"category": "Special", "basePower": 60})

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.choice_locked_move == "swift"

	battle.remove_item(attacker, source=defender, effect="move:knockoff")

	assert attacker.choice_locked_move is None
	assert attacker.item is None


def test_choice_lock_clears_on_switch_out():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	choice_scarf = Item.from_dict("Choice Scarf", {"name": "Choice Scarf"})
	battle.set_item(attacker, choice_scarf)
	move = BattleMove(name="Quick Attack", raw={"category": "Physical", "basePower": 40})

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.choice_locked_move == "quickattack"

	battle.on_switch_out(attacker)

	assert attacker.choice_locked_move is None
	assert "choicelock" not in attacker.volatiles


def test_harvest_restores_consumed_berry_with_battle_helper():
	load_modules()
	from pokemon.dex.entities import Ability, Item

	battle, attacker, _ = build_battle()
	ability = Ability.from_dict("Harvest", {"name": "Harvest", "onResidual": "Harvest.onResidual"})
	berry = Item.from_dict(
		"Sitrus Berry",
		{"name": "Sitrus Berry", "onEat": "Sitrusberry.onEat", "onTryEatItem": "Sitrusberry.onTryEatItem"},
	)
	attacker.ability = ability
	attacker.effective_weather = lambda: "sunnyday"
	battle.set_item(attacker, berry)

	assert battle.eat_item(attacker, force=True) is True
	assert attacker.item is None

	ability.call("onResidual", pokemon=attacker)

	assert getattr(attacker.item, "name", None) == "Sitrus Berry"
	assert attacker.consumed_berry is None


def test_pickup_recovers_last_used_side_item():
	load_modules()
	from pokemon.dex.entities import Ability, Item

	battle, attacker, _ = build_battle()
	pickup_user = attacker
	pickup_user.ability = Ability.from_dict("Pickup", {"name": "Pickup", "onResidual": "Pickup.onResidual"})
	berry = Item.from_dict(
		"Aguav Berry",
		{"name": "Aguav Berry", "onEat": "Aguavberry.onEat", "onTryEatItem": "Aguavberry.onTryEatItem"},
	)
	battle.set_item(pickup_user, berry)

	assert battle.eat_item(pickup_user, force=True) is True
	assert pickup_user.item is None

	pickup_user.ability.call("onResidual", pokemon=pickup_user)

	assert getattr(pickup_user.item, "name", None) == "Aguav Berry"
	assert getattr(pickup_user.side, "used_items", []) == []


def test_pickup_does_not_overwrite_existing_held_item_state():
	load_modules()
	from pokemon.dex.entities import Ability, Item

	battle, attacker, _ = build_battle()
	pickup_user = attacker
	pickup_user.ability = Ability.from_dict("Pickup", {"name": "Pickup", "onResidual": "Pickup.onResidual"})
	pickup_user.held_item = "Placeholder"
	pickup_user.side.used_items = [Item.from_dict("Aguav Berry", {"name": "Aguav Berry"})]

	pickup_user.ability.call("onResidual", pokemon=pickup_user)

	assert pickup_user.item is None
	assert pickup_user.held_item == "Placeholder"
	assert len(getattr(pickup_user.side, "used_items", [])) == 1


def test_corrosive_gas_uses_remove_item_helper():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	leftovers = Item.from_dict("Leftovers", {"name": "Leftovers"})
	battle.set_item(defender, leftovers)
	move = BattleMove(
		name="Corrosive Gas",
		raw={"category": "Status", "onHit": "Corrosivegas.onHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert defender.item is None
	assert defender.last_removed_item == "Leftovers"


def test_stuff_cheeks_eats_berry_through_battle_helper():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	berry = Item.from_dict(
		"Aguav Berry",
		{"name": "Aguav Berry", "onEat": "Aguavberry.onEat", "onTryEatItem": "Aguavberry.onTryEatItem"},
	)
	attacker.hp = 40
	attacker.boosts["defense"] = 0
	battle.set_item(attacker, berry)
	move = BattleMove(
		name="Stuff Cheeks",
		raw={"category": "Status", "onHit": "Stuffcheeks.onHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.item is None
	assert attacker.hp > 40
	assert attacker.boosts.get("defense", attacker.boosts.get("def", 0)) >= 2
	assert getattr(attacker.consumed_berry, "name", None) == "Aguav Berry"


def test_tea_time_forces_active_pokemon_to_eat_berries():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	attacker_berry = Item.from_dict(
		"Aguav Berry",
		{"name": "Aguav Berry", "onEat": "Aguavberry.onEat", "onTryEatItem": "Aguavberry.onTryEatItem"},
	)
	defender_berry = Item.from_dict(
		"Sitrus Berry",
		{"name": "Sitrus Berry", "onEat": "Sitrusberry.onEat", "onTryEatItem": "Sitrusberry.onTryEatItem"},
	)
	attacker.hp = 40
	defender.hp = 40
	battle.set_item(attacker, attacker_berry)
	battle.set_item(defender, defender_berry)
	move = BattleMove(
		name="Teatime",
		raw={"category": "Status", "onHit": "Teatime.onHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.item is None
	assert defender.item is None
	assert attacker.hp > 40
	assert defender.hp > 40


def test_incinerate_removes_berries_from_all_opposing_active_pokemon():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	Pokemon = modules["Pokemon"]
	battle, attacker, defender = build_battle()
	from pokemon.dex.entities import Item

	extra = Pokemon("Defender2", level=50, hp=200, max_hp=200)
	extra.base_stats = attacker.base_stats
	extra.types = ["Normal"]
	extra.boosts = {
		"attack": 0,
		"defense": 0,
		"special_attack": 0,
		"special_defense": 0,
		"speed": 0,
		"accuracy": 0,
		"evasion": 0,
	}
	extra.side = battle.participants[1].side
	extra.battle = battle
	battle.participants[1].pokemons.append(extra)
	battle.participants[1].active.append(extra)

	berry_one = Item.from_dict("Aguav Berry", {"name": "Aguav Berry"})
	berry_two = Item.from_dict("Sitrus Berry", {"name": "Sitrus Berry"})
	battle.set_item(defender, berry_one)
	battle.set_item(extra, berry_two)
	move = BattleMove(
		name="Incinerate",
		raw={"category": "Special", "basePower": 60, "onHit": "Incinerate.onHit"},
	)

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert defender.item is None
	assert extra.item is None
	assert defender.last_removed_item == "Aguav Berry"
	assert extra.last_removed_item == "Sitrus Berry"


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
