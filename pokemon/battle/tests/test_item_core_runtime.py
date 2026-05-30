"""Battle-level coverage for the core held-item runtime."""

from __future__ import annotations

import random

import pytest

from pokemon.battle.actions import Action, ActionType

from .helpers import battle_move, build_battle, load_modules


def _move_action(battle, pokemon, move, *, target=None):
	"""Return a move action targeting the opposing participant by default."""

	participant = battle.participant_for(pokemon)
	assert participant is not None
	if target is None:
		target = battle.opponent_of(participant)
	return Action(
		actor=participant,
		action_type=ActionType.MOVE,
		target=target,
		move=move,
		pokemon=pokemon,
	)


def test_leftovers_heals_on_residual():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, _ = build_battle()
	attacker.hp = 100
	attacker.max_hp = 160
	battle.set_item(attacker, Item.from_dict("Leftovers", {"name": "Leftovers", "onResidual": "Leftovers.onResidual"}))

	battle.residual()

	assert attacker.hp == 110


def test_black_sludge_heals_any_poison_type_and_hurts_non_poison():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle(attacker_types=["Water", "Poison"], defender_types=["Normal"])
	attacker.hp = 100
	attacker.max_hp = 160
	defender.hp = 160
	defender.max_hp = 160
	item = Item.from_dict("Black Sludge", {"name": "Black Sludge", "onResidual": "Blacksludge.onResidual"})
	battle.set_item(attacker, item)
	battle.set_item(defender, item)

	battle.residual()

	assert attacker.hp == 110
	assert defender.hp == 140


def test_choice_scarf_changes_turn_order_and_choice_lock_blocks_other_moves():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	attacker.base_stats.speed = 50
	defender.base_stats.speed = 60
	attacker.moves = [battle_move("Tackle"), battle_move("Quick Attack", priority=1)]
	battle.set_item(
		attacker,
		Item.from_dict(
			"Choice Scarf",
			{
				"name": "Choice Scarf",
				"onModifySpe": "Choicescarf.onModifySpe",
				"onModifyMove": "Choicescarf.onModifyMove",
			},
		),
	)

	first = _move_action(battle, attacker, attacker.moves[0])
	second = _move_action(battle, defender, battle_move("Scratch"))
	ordered = battle.order_actions([first, second])
	assert ordered[0].pokemon is attacker

	battle.use_move(first)

	assert attacker.choice_locked_move == "tackle"
	pre_hp = defender.hp
	locked_out = _move_action(battle, attacker, attacker.moves[1])
	battle.use_move(locked_out)
	assert defender.hp == pre_hp


def test_choice_band_and_choice_specs_apply_offense_boosts():
	load_modules()
	from pokemon.dex.entities import Item

	plain_battle, plain_attacker, plain_defender = build_battle()
	plain_battle.rng = random.Random(0)
	physical_plain = plain_battle._deal_damage(plain_attacker, plain_defender, battle_move("Tackle", power=80))

	band_battle, band_attacker, band_defender = build_battle()
	band_battle.rng = random.Random(0)
	band_battle.set_item(
		band_attacker,
		Item.from_dict(
			"Choice Band",
			{
				"name": "Choice Band",
				"onModifyAtk": "Choiceband.onModifyAtk",
				"onModifyMove": "Choiceband.onModifyMove",
			},
		),
	)
	physical_band = band_battle._deal_damage(band_attacker, band_defender, battle_move("Tackle", power=80))

	special_plain_battle, special_plain_attacker, special_plain_defender = build_battle()
	special_plain_battle.rng = random.Random(0)
	special_plain = special_plain_battle._deal_damage(
		special_plain_attacker,
		special_plain_defender,
		battle_move("Water Gun", power=80, move_type="Water", category="Special"),
	)

	specs_battle, specs_attacker, specs_defender = build_battle()
	specs_battle.rng = random.Random(0)
	specs_battle.set_item(
		specs_attacker,
		Item.from_dict(
			"Choice Specs",
			{
				"name": "Choice Specs",
				"onModifySpA": "Choicespecs.onModifySpA",
				"onModifyMove": "Choicespecs.onModifyMove",
			},
		),
	)
	special_specs = specs_battle._deal_damage(
		specs_attacker,
		specs_defender,
		battle_move("Water Gun", power=80, move_type="Water", category="Special"),
	)

	assert physical_band > physical_plain
	assert special_specs > special_plain


def test_eviolite_reduces_damage_for_not_fully_evolved_target():
	load_modules()
	from pokemon.dex.entities import Item

	item_battle, item_attacker, item_defender = build_battle()
	item_defender.fully_evolved = False
	item_battle.set_item(
		item_defender,
		Item.from_dict(
			"Eviolite",
			{
				"name": "Eviolite",
				"onModifyDef": "Eviolite.onModifyDef",
				"onModifySpD": "Eviolite.onModifySpD",
			},
		),
	)

	modified_def = item_battle.runEvent(
		"ModifyDef",
		item_defender,
		item_attacker,
		battle_move("Tackle", power=80),
		120,
	)
	modified_spd = item_battle.runEvent(
		"ModifySpD",
		item_defender,
		item_attacker,
		battle_move("Water Gun", power=80, move_type="Water", category="Special"),
		120,
	)

	assert modified_def == 180
	assert modified_spd == 180


def test_air_balloon_pops_after_damaging_hit():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			"Air Balloon",
			{
				"name": "Air Balloon",
				"onStart": "Airballoon.onStart",
				"onDamagingHit": "Airballoon.onDamagingHit",
			},
		),
	)
	assert defender.volatiles.get("airballoon") is True

	battle._deal_damage(attacker, defender, battle_move("Tackle", power=40))

	assert defender.item is None
	assert defender.volatiles.get("airballoon") is None
	assert getattr(defender, "held_item", "") == ""


def test_rocky_helmet_damages_contact_attacker():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	attacker.max_hp = 180
	attacker.hp = 180
	battle.set_item(
		defender,
		Item.from_dict(
			"Rocky Helmet",
			{"name": "Rocky Helmet", "onDamagingHit": "Rockyhelmet.onDamagingHit"},
		),
	)

	battle._deal_damage(
		attacker,
		defender,
		battle_move("Tackle", power=40, flags={"contact": 1}),
	)

	assert attacker.hp == 150


def test_absorb_bulb_consumes_and_boosts_special_attack():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			"Absorb Bulb",
			{"name": "Absorb Bulb", "onDamagingHit": "Absorbbulb.onDamagingHit"},
		),
	)

	battle._deal_damage(attacker, defender, battle_move("Water Gun", power=40, move_type="Water", category="Special"))

	assert defender.boosts["spa"] == 1
	assert defender.item is None
	assert getattr(defender, "held_item", "") == ""


def test_cell_battery_luminous_moss_and_snowball_consume_on_matching_hit():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			"Cell Battery",
			{"name": "Cell Battery", "onDamagingHit": "Cellbattery.onDamagingHit"},
		),
	)
	battle._deal_damage(
		attacker,
		defender,
		battle_move("Thunder Shock", power=40, move_type="Electric", category="Special"),
	)
	assert defender.boosts["atk"] == 1
	assert defender.item is None

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			"Luminous Moss",
			{"name": "Luminous Moss", "onDamagingHit": "Luminousmoss.onDamagingHit"},
		),
	)
	battle._deal_damage(
		attacker,
		defender,
		battle_move("Water Gun", power=40, move_type="Water", category="Special"),
	)
	assert defender.boosts["spd"] == 1
	assert defender.item is None

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			"Snowball",
			{"name": "Snowball", "onDamagingHit": "Snowball.onDamagingHit"},
		),
	)
	battle._deal_damage(
		attacker,
		defender,
		battle_move("Powder Snow", power=40, move_type="Ice", category="Special"),
	)
	assert defender.boosts["atk"] == 1
	assert defender.item is None


def test_sitrus_berry_auto_consumes_after_damage():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	defender.hp = 90
	defender.max_hp = 200
	battle.set_item(
		defender,
		Item.from_dict(
			"Sitrus Berry",
			{
				"name": "Sitrus Berry",
				"onEat": "Sitrusberry.onEat",
				"onTryEatItem": "Sitrusberry.onTryEatItem",
				"onUpdate": "Sitrusberry.onUpdate",
			},
		),
	)

	battle._deal_damage(attacker, defender, battle_move("Tackle", power=40))

	assert defender.item is None
	assert getattr(defender.last_consumed_item_obj, "name", None) == "Sitrus Berry"
	assert defender.hp > 50


def test_aguav_and_berry_juice_auto_consume_for_recovery():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	defender.hp = 40
	defender.max_hp = 180
	battle.set_item(
		defender,
		Item.from_dict(
			"Aguav Berry",
			{
				"name": "Aguav Berry",
				"onEat": "Aguavberry.onEat",
				"onTryEatItem": "Aguavberry.onTryEatItem",
				"onUpdate": "Aguavberry.onUpdate",
			},
		),
	)
	battle._deal_damage(attacker, defender, battle_move("Tackle", power=20))
	assert defender.item is None
	assert defender.hp >= 80

	battle, attacker, defender = build_battle()
	defender.hp = 90
	defender.max_hp = 200
	battle.set_item(
		defender,
		Item.from_dict("Berry Juice", {"name": "Berry Juice", "onUpdate": "Berryjuice.onUpdate"}),
	)
	battle._deal_damage(attacker, defender, battle_move("Tackle", power=30))
	assert defender.item is None
	assert defender.hp > 60


def test_passho_berry_only_reduces_super_effective_hit_once():
	load_modules()
	from pokemon.dex.entities import Item

	plain_battle, plain_attacker, plain_defender = build_battle(defender_types=["Rock", "Ground"])
	plain_battle.rng = random.Random(0)
	plain_damage = plain_battle._deal_damage(
		plain_attacker,
		plain_defender,
		battle_move("Water Gun", power=60, move_type="Water", category="Special"),
	)

	item_battle, item_attacker, item_defender = build_battle(defender_types=["Rock", "Ground"])
	item_battle.rng = random.Random(0)
	item_battle.set_item(
		item_defender,
		Item.from_dict(
			"Passho Berry",
			{
				"name": "Passho Berry",
				"onSourceModifyDamage": "Passhoberry.onSourceModifyDamage",
			},
		),
	)
	first_hit = item_battle._deal_damage(
		item_attacker,
		item_defender,
		battle_move("Water Gun", power=60, move_type="Water", category="Special"),
	)

	post_battle, post_attacker, post_defender = build_battle(defender_types=["Rock", "Ground"])
	post_battle.rng = random.Random(0)
	second_hit = post_battle._deal_damage(
		post_attacker,
		post_defender,
		battle_move("Water Gun", power=60, move_type="Water", category="Special"),
	)

	assert first_hit < plain_damage
	assert second_hit == plain_damage
	assert item_defender.item is None


@pytest.mark.parametrize(
	("berry_name", "callback_name", "move_name", "move_type", "defender_types"),
	[
		("Babiri Berry", "Babiriberry.onSourceModifyDamage", "Flash Cannon", "Steel", ["Rock", "Ice"]),
		("Charti Berry", "Chartiberry.onSourceModifyDamage", "Rock Slide", "Rock", ["Bug", "Flying"]),
		("Chople Berry", "Chopleberry.onSourceModifyDamage", "Aura Sphere", "Fighting", ["Normal"]),
		("Coba Berry", "Cobaberry.onSourceModifyDamage", "Air Slash", "Flying", ["Grass", "Fighting"]),
		("Colbur Berry", "Colburberry.onSourceModifyDamage", "Dark Pulse", "Dark", ["Ghost"]),
		("Haban Berry", "Habanberry.onSourceModifyDamage", "Dragon Pulse", "Dragon", ["Dragon"]),
		("Kasib Berry", "Kasibberry.onSourceModifyDamage", "Shadow Ball", "Ghost", ["Ghost"]),
		("Kebia Berry", "Kebiaberry.onSourceModifyDamage", "Sludge Bomb", "Poison", ["Grass"]),
		("Occa Berry", "Occaberry.onSourceModifyDamage", "Flamethrower", "Fire", ["Grass", "Steel"]),
		("Payapa Berry", "Payapaberry.onSourceModifyDamage", "Psychic", "Psychic", ["Poison"]),
		("Rindo Berry", "Rindoberry.onSourceModifyDamage", "Energy Ball", "Grass", ["Rock", "Ground"]),
		("Roseli Berry", "Roseliberry.onSourceModifyDamage", "Moonblast", "Fairy", ["Dragon"]),
		("Shuca Berry", "Shucaberry.onSourceModifyDamage", "Earth Power", "Ground", ["Fire"]),
		("Tanga Berry", "Tangaberry.onSourceModifyDamage", "Bug Buzz", "Bug", ["Grass", "Psychic"]),
		("Wacan Berry", "Wacanberry.onSourceModifyDamage", "Thunderbolt", "Electric", ["Water", "Flying"]),
		("Yache Berry", "Yacheberry.onSourceModifyDamage", "Ice Beam", "Ice", ["Flying", "Ground"]),
	],
)
def test_type_resist_berries_reduce_super_effective_hit_once(
	berry_name,
	callback_name,
	move_name,
	move_type,
	defender_types,
):
	load_modules()
	from pokemon.dex.entities import Item

	plain_battle, plain_attacker, plain_defender = build_battle(defender_types=defender_types)
	plain_battle.rng = random.Random(0)
	plain_damage = plain_battle._deal_damage(
		plain_attacker,
		plain_defender,
		battle_move(move_name, power=60, move_type=move_type, category="Special"),
	)

	item_battle, item_attacker, item_defender = build_battle(defender_types=defender_types)
	item_battle.set_item(
		item_defender,
		Item.from_dict(
			berry_name,
			{
				"name": berry_name,
				"onSourceModifyDamage": callback_name,
			},
		),
	)
	item_battle.rng = random.Random(0)
	first_hit = item_battle._deal_damage(
		item_attacker,
		item_defender,
		battle_move(move_name, power=60, move_type=move_type, category="Special"),
	)

	post_battle, post_attacker, post_defender = build_battle(defender_types=defender_types)
	post_battle.rng = random.Random(0)
	second_hit = post_battle._deal_damage(
		post_attacker,
		post_defender,
		battle_move(move_name, power=60, move_type=move_type, category="Special"),
	)

	assert first_hit < plain_damage
	assert second_hit == plain_damage
	assert item_defender.item is None


@pytest.mark.parametrize(
	("seed_name", "callback_name", "terrain_name", "boost_key"),
	[
		("Electric Seed", "Electricseed", "electricterrain", "def"),
		("Grassy Seed", "Grassyseed", "grassyterrain", "def"),
		("Misty Seed", "Mistyseed", "mistyterrain", "spd"),
		("Psychic Seed", "Psychicseed", "psychicterrain", "spd"),
	],
)
def test_terrain_seeds_activate_when_set_into_active_terrain(
	seed_name,
	callback_name,
	terrain_name,
	boost_key,
):
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	assert battle.setTerrain(terrain_name, source=attacker) is True
	battle.set_item(
		defender,
		Item.from_dict(
			seed_name,
			{
				"name": seed_name,
				"onStart": f"{callback_name}.onStart",
				"onTerrainChange": f"{callback_name}.onTerrainChange",
			},
		),
	)

	assert defender.boosts[boost_key] == 1
	assert defender.item is None
	assert getattr(defender, "held_item", "") == ""


@pytest.mark.parametrize(
	("seed_name", "callback_name", "terrain_name", "boost_key"),
	[
		("Electric Seed", "Electricseed", "electricterrain", "def"),
		("Grassy Seed", "Grassyseed", "grassyterrain", "def"),
		("Misty Seed", "Mistyseed", "mistyterrain", "spd"),
		("Psychic Seed", "Psychicseed", "psychicterrain", "spd"),
	],
)
def test_terrain_seeds_activate_on_terrain_change(
	seed_name,
	callback_name,
	terrain_name,
	boost_key,
):
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict(
			seed_name,
			{
				"name": seed_name,
				"onStart": f"{callback_name}.onStart",
				"onTerrainChange": f"{callback_name}.onTerrainChange",
			},
		),
	)

	assert defender.boosts.get(boost_key, 0) == 0
	assert battle.setTerrain(terrain_name, source=attacker) is True

	assert defender.boosts[boost_key] == 1
	assert defender.item is None
	assert getattr(defender, "held_item", "") == ""


def test_focus_sash_prevents_ohko_and_life_orb_adds_recoil():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, defender = build_battle()
	battle.set_item(
		defender,
		Item.from_dict("Focus Sash", {"name": "Focus Sash", "onDamage": "Focussash.onDamage"}),
	)
	battle._deal_damage(attacker, defender, battle_move("Tackle", power=1000))
	assert defender.hp == 1
	assert defender.item is None

	battle, attacker, defender = build_battle()
	attacker.max_hp = 200
	attacker.hp = 200
	battle.set_item(
		attacker,
		Item.from_dict(
			"Life Orb",
			{
				"name": "Life Orb",
				"onModifyDamage": "Lifeorb.onModifyDamage",
				"onAfterMoveSecondarySelf": "Lifeorb.onAfterMoveSecondarySelf",
			},
		),
	)
	before = defender.hp
	battle.use_move(_move_action(battle, attacker, battle_move("Tackle", power=80)))
	assert defender.hp < before
	assert attacker.hp == 180


def test_assault_vest_boosts_special_defense_and_blocks_status_moves():
	load_modules()
	from pokemon.dex.entities import Item

	plain_battle, plain_attacker, plain_defender = build_battle()
	plain_battle.rng = random.Random(0)
	plain_special = plain_battle._deal_damage(
		plain_attacker,
		plain_defender,
		battle_move("Water Gun", power=80, move_type="Water", category="Special"),
	)

	item_battle, item_attacker, item_defender = build_battle()
	item_battle.rng = random.Random(0)
	item_battle.set_item(
		item_defender,
		Item.from_dict(
			"Assault Vest",
			{
				"name": "Assault Vest",
				"onModifySpD": "Assaultvest.onModifySpD",
				"onDisableMove": "Assaultvest.onDisableMove",
			},
		),
	)
	item_special = item_battle._deal_damage(
		item_attacker,
		item_defender,
		battle_move("Water Gun", power=80, move_type="Water", category="Special"),
	)
	assert item_special < plain_special

	status_move = battle_move("Recover", power=0, category="Status")
	item_defender.moves = [status_move]
	action = _move_action(item_battle, item_defender, status_move, target=item_battle.opponent_of(item_battle.participant_for(item_defender)))
	pre_hp = item_attacker.hp
	item_battle.use_move(action)
	assert item_attacker.hp == pre_hp


def test_room_service_consumes_when_trick_room_starts():
	load_modules()
	from pokemon.dex.entities import Item

	battle, attacker, _ = build_battle()
	battle.set_item(
		attacker,
		Item.from_dict(
			"Room Service",
			{
				"name": "Room Service",
				"onAnyPseudoWeatherChange": "Roomservice.onAnyPseudoWeatherChange",
				"onStart": "Roomservice.onStart",
			},
		),
	)

	battle.add_pseudo_weather("trickroom", source=attacker)

	assert attacker.boosts["spe"] == -1
	assert attacker.item is None
