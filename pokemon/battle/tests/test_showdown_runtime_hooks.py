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


def test_move_on_modify_type_uses_plate_item_identity():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle(defender_types=["Grass"])
	from pokemon.dex.entities import Item

	flame_plate = Item.from_dict("Flame Plate", {"name": "Flame Plate", "onPlate": "Fire"})
	battle.set_item(attacker, flame_plate)
	move = BattleMove(
		name="Judgment",
		raw={
			"category": "Special",
			"basePower": 100,
			"accuracy": 100,
			"type": "Normal",
			"onModifyType": "Judgment.onModifyType",
		},
	)
	start_hp = defender.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "onPlate", None) == "Fire"
	assert move.type == "Fire"
	assert defender.hp < start_hp


def test_multi_attack_uses_memory_item_identity():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle(defender_types=["Dragon"])
	from pokemon.dex.entities import Item

	fairy_memory = Item.from_dict("Fairy Memory", {"name": "Fairy Memory", "onMemory": "Fairy"})
	battle.set_item(attacker, fairy_memory)
	move = BattleMove(
		name="Multi-Attack",
		raw={
			"category": "Physical",
			"basePower": 120,
			"accuracy": 100,
			"type": "Normal",
			"onModifyType": "Multiattack.onModifyType",
		},
	)
	start_hp = defender.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "memory_type", None) == "Fairy"
	assert move.type == "Fairy"
	assert defender.hp < start_hp


def test_techno_blast_uses_drive_item_identity():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle(defender_types=["Water"])
	from pokemon.dex.entities import Item

	shock_drive = Item.from_dict("Shock Drive", {"name": "Shock Drive", "onDrive": "Electric"})
	battle.set_item(attacker, shock_drive)
	move = BattleMove(
		name="Techno Blast",
		raw={
			"category": "Special",
			"basePower": 120,
			"accuracy": 100,
			"type": "Normal",
			"onModifyType": "Technoblast.onModifyType",
		},
	)
	start_hp = defender.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "drive_type", None) == "Electric"
	assert move.type == "Electric"
	assert defender.hp < start_hp


def test_natural_gift_uses_item_natural_gift_identity():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle(defender_types=["Ghost"])
	from pokemon.dex.entities import Item

	belue = Item.from_dict(
		"Belue Berry",
		{"name": "Belue Berry", "naturalGift": {"basePower": 100, "type": "Electric"}},
	)
	battle.set_item(attacker, belue)
	move = BattleMove(
		name="Natural Gift",
		raw={
			"category": "Physical",
			"basePower": 1,
			"accuracy": 100,
			"type": "Normal",
			"onModifyType": "Naturalgift.onModifyType",
			"onPrepareHit": "Naturalgift.onPrepareHit",
		},
	)
	start_hp = defender.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert getattr(attacker.item, "natural_type", None) == "Electric"
	assert getattr(attacker.item, "natural_power", None) == 100
	assert move.type == "Electric"
	assert move.power == 100
	assert defender.hp < start_hp


def test_red_orb_primal_forme_activates_on_switch_in():
	load_modules()
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	attacker.name = "Groudon"
	red_orb = Item.from_dict(
		"Red Orb",
		{"name": "Red Orb", "onPrimal": "Redorb.onPrimal"},
	)
	battle.set_item(attacker, red_orb)

	battle.on_enter_battle(attacker)

	assert attacker.name == "Groudon-Primal"
	assert getattr(attacker, "species", None) == "Groudon-Primal"
	assert attacker.types == ["Ground", "Fire"]
	assert getattr(getattr(attacker, "ability", None), "name", attacker.ability) == "Desolate Land"


def test_blue_orb_primal_forme_activates_on_switch_in():
	load_modules()
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	attacker.name = "Kyogre"
	blue_orb = Item.from_dict(
		"Blue Orb",
		{"name": "Blue Orb", "onPrimal": "Blueorb.onPrimal"},
	)
	battle.set_item(attacker, blue_orb)

	battle.on_enter_battle(attacker)

	assert attacker.name == "Kyogre-Primal"
	assert getattr(attacker, "species", None) == "Kyogre-Primal"
	assert attacker.types == ["Water"]
	assert getattr(getattr(attacker, "ability", None), "name", attacker.ability) == "Primordial Sea"


def test_forced_forme_item_applies_on_switch_in():
	load_modules()
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	attacker.name = "Genesect"
	burn_drive = Item.from_dict(
		"Burn Drive",
		{"name": "Burn Drive", "forcedForme": "Genesect-Burn", "onDrive": "Fire"},
	)
	battle.set_item(attacker, burn_drive)

	battle.on_enter_battle(attacker)

	assert attacker.name == "Genesect-Burn"
	assert getattr(attacker, "species", None) == "Genesect-Burn"
	assert attacker.types == ["Bug", "Steel"]
	assert getattr(getattr(attacker, "ability", None), "name", attacker.ability) == "Download"


def test_set_item_applies_forced_forme_immediately():
	load_modules()
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	attacker.name = "Genesect"
	attacker.species = "Genesect"
	burn_drive = Item.from_dict(
		"Burn Drive",
		{"name": "Burn Drive", "forcedForme": "Genesect-Burn", "onDrive": "Fire"},
	)

	assert battle.set_item(attacker, burn_drive) is True
	assert attacker.name == "Genesect-Burn"
	assert getattr(attacker, "species", None) == "Genesect-Burn"


def test_take_item_reverts_forced_forme_to_base_species():
	load_modules()
	battle, attacker, _ = build_battle()
	from pokemon.dex.entities import Item

	attacker.name = "Genesect"
	attacker.species = "Genesect"
	burn_drive = Item.from_dict(
		"Burn Drive",
		{"name": "Burn Drive", "forcedForme": "Genesect-Burn", "onDrive": "Fire"},
	)
	battle.set_item(attacker, burn_drive)

	removed = battle.take_item(attacker)

	assert getattr(removed, "name", None) == "Burn Drive"
	assert attacker.name == "Genesect"
	assert getattr(attacker, "species", None) == "Genesect"
	assert attacker.types == ["Bug", "Steel"]
	assert getattr(getattr(attacker, "ability", None), "name", attacker.ability) == "Download"


def test_healing_wish_slot_condition_heals_replacement_on_switch():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	battle, attacker, _ = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=60, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.status = "brn"
	reserve.battle = battle

	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	assert battle.add_slot_condition(attacker, "healingwish", {"onSwap": "Healingwish.onSwap"}) is True

	battle.switch_pokemon(participant, reserve, 0)

	assert reserve.hp == reserve.max_hp
	assert reserve.status == 0
	assert participant.side.get_slot_condition(0, "healingwish") is None


def test_lunar_dance_slot_condition_restores_replacement_pp():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	battle, attacker, _ = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=40, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.status = "par"
	reserve.moves = [
		SimpleNamespace(pp=1, max_pp=8),
		SimpleNamespace(pp=0, maxpp=5),
	]
	reserve.battle = battle

	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	assert battle.add_slot_condition(attacker, "lunardance", {"onSwap": "Lunardance.onSwap"}) is True

	battle.switch_pokemon(participant, reserve, 0)

	assert reserve.hp == reserve.max_hp
	assert reserve.status == 0
	assert reserve.moves[0].pp == 8
	assert reserve.moves[1].pp == 5
	assert participant.side.get_slot_condition(0, "lunardance") is None


def test_wish_slot_condition_heals_current_occupant_after_duration():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	battle, attacker, _ = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=50, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle

	participant = battle.participants[0]
	participant.pokemons.append(reserve)
	attacker.hp = 80

	assert battle.add_slot_condition(
		attacker,
		"Wish",
		{"duration": 2, "onStart": "Wish.onStart", "onEnd": "Wish.onEnd"},
		source=attacker,
	) is True

	battle.residual()
	assert attacker.hp == 80
	assert participant.side.get_slot_condition(0, "Wish") is not None

	battle.switch_pokemon(participant, reserve, 0)
	battle.residual()

	assert reserve.hp == 150
	assert participant.side.get_slot_condition(0, "Wish") is None


def test_revival_blessing_revives_first_fainted_ally():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	fainted = Pokemon("Fainted Ally", level=50, hp=0, max_hp=200)
	fainted.base_stats = attacker.base_stats
	fainted.types = ["Normal"]
	fainted.boosts = dict(attacker.boosts)
	fainted.is_fainted = True
	fainted.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(fainted)

	move = BattleMove(
		name="Revival Blessing",
		raw={
			"category": "Status",
			"accuracy": True,
			"target": "self",
			"slotCondition": "revivalblessing",
			"condition": {"duration": 1},
			"onTryHit": "Revivalblessing.onTryHit",
		},
	)
	move.key = "revivalblessing"

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert fainted.hp == 100
	assert fainted.is_fainted is False
	assert participant.side.get_slot_condition(0, "revivalblessing") is None


def test_generic_self_switch_move_queues_switch_out():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, defender = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	move = BattleMove(
		name="Pivot Hit",
		raw={
			"category": "Physical",
			"basePower": 40,
			"accuracy": 100,
			"type": "Bug",
			"selfSwitch": True,
		},
	)
	move.key = "pivothit"
	start_hp = defender.hp

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[1],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert defender.hp < start_hp
	assert attacker.tempvals.get("switch_out") is True

	battle.run_switch()

	assert participant.active[0] is reserve


def test_self_switch_copyvolatile_passes_boosts_and_substitute():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	attacker.boosts["attack"] = 2
	attacker.volatiles["substitute"] = {"hp": 42}
	move = BattleMove(
		name="Pass Pivot",
		raw={
			"category": "Status",
			"accuracy": True,
			"target": "self",
			"type": "Normal",
			"selfSwitch": "copyvolatile",
		},
	)
	move.key = "passpivot"

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.tempvals.get("switch_out") is True
	assert attacker.tempvals.get("baton_pass") is True

	battle.run_switch()

	assert participant.active[0] is reserve
	assert reserve.boosts["attack"] == 2
	assert reserve.volatiles.get("substitute") == {"hp": 42}


def test_shed_tail_passes_fresh_substitute_to_replacement():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	move = BattleMove(
		name="Shed Tail",
		raw={
			"category": "Status",
			"accuracy": True,
			"target": "self",
			"type": "Normal",
			"selfSwitch": "shedtail",
			"onTryHit": "Shedtail.onTryHit",
			"onHit": "Shedtail.onHit",
		},
	)
	move.key = "shedtail"

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.hp == 100
	assert attacker.tempvals.get("switch_out") is True
	assert attacker.tempvals.get("shedtail_substitute") == {"hp": 50}

	battle.run_switch()

	assert participant.active[0] is reserve
	assert reserve.volatiles.get("substitute") == {"hp": 50}
	assert not attacker.volatiles.get("substitute")


def test_shed_tail_fails_when_user_already_has_substitute():
	modules = load_modules()
	BattleMove = modules["BattleMove"]
	ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
	battle, attacker, _ = build_battle()
	attacker.volatiles["substitute"] = {"hp": 40}
	start_hp = attacker.hp

	move = BattleMove(
		name="Shed Tail",
		raw={
			"category": "Status",
			"accuracy": True,
			"target": "self",
			"type": "Normal",
			"selfSwitch": "shedtail",
			"onTryHit": "Shedtail.onTryHit",
			"onHit": "Shedtail.onHit",
		},
	)
	move.key = "shedtail"

	action = _battle_action(
		battle.participants[0],
		ActionType.MOVE,
		target=battle.participants[0],
		move=move,
		pokemon=attacker,
	)
	battle.use_move(action)

	assert attacker.hp == start_hp
	assert attacker.tempvals.get("switch_out") is None


def test_emergency_exit_queues_switch_after_crossing_half_hp():
	modules = load_modules()
	damage_mod = __import__("pokemon.battle.damage", fromlist=["apply_damage"])
	battle, attacker, defender = build_battle(defender_ability=__import__("pokemon.dex.functions.abilities_funcs", fromlist=["Emergencyexit"]).Emergencyexit())
	defender.hp = 110
	move = modules["BattleMove"](
		name="Tackle",
		power=120,
		accuracy=100,
		type="Normal",
		raw={"category": "Physical", "basePower": 120, "accuracy": 100},
	)
	move.key = "tackle"

	damage_mod.apply_damage(attacker, defender, move, battle=battle)

	assert defender.hp <= defender.max_hp // 2
	assert defender.tempvals.get("switch_out") is True


def test_wimp_out_queues_switch_after_damaging_hit():
	modules = load_modules()
	damage_mod = __import__("pokemon.battle.damage", fromlist=["apply_damage"])
	battle, attacker, defender = build_battle(defender_ability=__import__("pokemon.dex.functions.abilities_funcs", fromlist=["Wimpout"]).Wimpout())
	move = modules["BattleMove"](
		name="Tackle",
		power=60,
		accuracy=100,
		type="Normal",
		raw={"category": "Physical", "basePower": 60, "accuracy": 100},
	)
	move.key = "tackle"

	damage_mod.apply_damage(attacker, defender, move, battle=battle)

	assert defender.tempvals.get("switch_out") is True


def test_natural_cure_clears_status_on_switch_out():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	battle, attacker, _ = build_battle(attacker_status="brn")
	attacker.ability = __import__("pokemon.dex.functions.abilities_funcs", fromlist=["Naturalcure"]).Naturalcure()
	reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	battle.switch_pokemon(participant, reserve, 0)

	assert attacker.status == 0


def test_regenerator_heals_on_switch_out():
	modules = load_modules()
	Pokemon = modules["Pokemon"]
	battle, attacker, _ = build_battle()
	attacker.ability = __import__("pokemon.dex.functions.abilities_funcs", fromlist=["Regenerator"]).Regenerator()
	attacker.hp = 90
	reserve = Pokemon("Reserve", level=50, hp=200, max_hp=200)
	reserve.base_stats = attacker.base_stats
	reserve.types = ["Normal"]
	reserve.boosts = dict(attacker.boosts)
	reserve.battle = battle
	participant = battle.participants[0]
	participant.pokemons.append(reserve)

	battle.switch_pokemon(participant, reserve, 0)

	assert attacker.hp == min(attacker.max_hp, 90 + attacker.max_hp // 3)


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
