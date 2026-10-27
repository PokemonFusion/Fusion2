"""Qualified live misses and missing move effects through ordinary engine actions."""
import copy
import random

import pytest

from .helpers import build_battle, load_modules
from .test_live_ability_reactions import ally
from .test_live_checkpoint_effect_consumers import quiet_log, stage
from .test_pending_action_effects import action


@pytest.mark.parametrize("holder", ["attacker", "target"])
def test_no_guard_guarantees_a_qualifying_damaging_hit_from_either_holder(holder):
    battle, user, target = build_battle(attacker_ability="No Guard" if holder == "attacker" else "No Ability",
                                      defender_ability="No Guard" if holder == "target" else "No Ability")
    battle.rng = random.Random(0)
    battle.use_move(action(battle, user, target, "Zap Cannon"))
    assert target.hp < target.max_hp


def test_no_guard_on_an_uninvolved_ally_does_not_guarantee_the_users_hit():
    battle, user, target = build_battle()
    ally(battle, ability="No Guard")
    battle.rng = random.Random(0)
    battle.use_move(action(battle, user, target, "Zap Cannon"))
    assert target.hp == target.max_hp


@pytest.mark.parametrize("ability,weather", [("Sand Veil", "sandstorm"), ("Snow Cloak", "snow")])
@pytest.mark.parametrize("move", ["Swift", "Aerial Ace"])
def test_never_miss_moves_keep_their_guaranteed_hit_against_weather_evasion(ability, weather, move):
    battle, user, target = build_battle(defender_ability=ability)
    battle.setWeather(weather, target)
    battle.rng = random.Random(0)
    battle.use_move(action(battle, user, target, move))
    assert target.hp < target.max_hp


@pytest.mark.parametrize("own,partner", [(True, False), (False, True)])
def test_victory_star_receives_its_real_owner_and_modifies_ally_accuracy(own, partner):
    battle, user, target = build_battle(attacker_ability="Victory Star" if own else "No Ability")
    if partner:
        ally(battle, ability="Victory Star")
    battle.rng = random.Random(24)  # 0.712... is above 70 and below 77 percent.
    battle.use_move(action(battle, user, target, "Thunder"))
    assert target.hp < target.max_hp


def test_opposing_victory_star_does_not_raise_the_users_accuracy():
    battle, user, target = build_battle(defender_ability="Victory Star")
    battle.rng = random.Random(24)
    battle.use_move(action(battle, user, target, "Thunder"))
    assert target.hp == target.max_hp


def test_status_accuracy_consumer_honors_wonder_skin_but_self_boosts_still_work():
    values = []
    for ability in ("No Ability", "Wonder Skin"):
        battle, user, target = build_battle(defender_ability=ability)
        battle.rng = random.Random(0)
        battle.use_move(action(battle, user, target, "Growl"))
        values.append(stage(target, "atk", "attack"))
        battle.use_move(action(battle, target, target, "Swords Dance"))
        assert stage(target, "atk", "attack") == values[-1] + 2
    assert values == [-1, 0]


def test_status_moves_can_miss_normally_and_no_guard_preserves_status_immunities():
    for ability, types, burned in (("No Ability", ["Normal"], False),
                                   ("No Guard", ["Normal"], True),
                                   ("No Guard", ["Fire"], False)):
        battle, user, target = build_battle(attacker_ability=ability, defender_types=types)
        battle.rng = random.Random(2)  # The unmodified 85 percent attempt misses.
        battle.use_move(action(battle, user, target, "Will-O-Wisp"))
        assert (target.status == "brn") is burned


def test_grass_pelt_reads_actual_battle_terrain_and_no_terrain_is_a_negative():
    losses = []
    for ability, terrain in (("No Ability", "grassyterrain"), ("Grass Pelt", "grassyterrain"), ("Grass Pelt", "")):
        battle, user, target = build_battle(defender_ability=ability)
        if terrain:
            battle.setTerrain(terrain, target)
        battle.rng = random.Random(1)
        battle.use_move(action(battle, user, target, "Tackle"))
        losses.append(target.max_hp - target.hp)
    assert 0 < losses[1] < losses[0] == losses[2]


def test_stench_augmented_secondary_reaches_actual_hit_and_does_not_stack_existing_flinch():
    from pokemon import dex
    from pokemon.names import resolve_dex_entry
    observed = False
    for seed in range(24):
        battle, user, target = build_battle(attacker_ability="Stench")
        battle.rng = random.Random(seed)
        battle.use_move(action(battle, user, target, "Tackle"))
        observed |= "flinch" in target.volatiles
    assert observed
    original = copy.deepcopy(resolve_dex_entry(dex.MOVEDEX, "Bite").raw)
    battle, user, target = build_battle(attacker_ability="Stench")
    selected = action(battle, user, target, "Bite")
    battle.use_move(selected)
    raw = selected.move.raw
    secondaries = ([raw["secondary"]] if raw.get("secondary") else []) + list(raw.get("secondaries") or [])
    assert [(row["chance"], row["volatileStatus"]) for row in secondaries if row.get("volatileStatus") == "flinch"] == [(30, "flinch")]
    assert resolve_dex_entry(dex.MOVEDEX, "Bite").raw == original
