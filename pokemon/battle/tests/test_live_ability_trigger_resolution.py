"""Independent reproductions for five remaining matched ability failures."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_battle_log():
    """Separate offline diagnostic output from ordinary-login evidence."""
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def use(battle, user, target, name):
    """Run the named move through real prevention, damage and after-move events."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(0)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), load_modules()["BattleMove"](name), pokemon=user))
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("hp", [100, 200])
def test_liquid_ooze_inverts_actual_drain_even_when_the_recipient_was_full(hp):
    battle, user, target = build_battle(defender_ability="Liquid Ooze")
    user.hp = hp
    use(battle, user, target, "Absorb")
    assert user.hp < hp and target.hp < target.max_hp


def test_liquid_ooze_does_not_invert_an_unrelated_recovery_move():
    battle, user, target = build_battle(defender_ability="Liquid Ooze")
    user.hp = 100
    use(battle, user, user, "Recover")
    assert user.hp == user.max_hp


def test_liquid_ooze_does_not_hurt_its_own_draining_attacks():
    battle, user, target = build_battle(attacker_ability="Liquid Ooze")
    user.hp = 100
    use(battle, user, target, "Absorb")
    assert user.hp > 100


def test_liquid_ooze_damage_respects_the_drainers_magic_guard():
    battle, user, target = build_battle(attacker_ability="Magic Guard", defender_ability="Liquid Ooze")
    use(battle, user, target, "Absorb")
    assert user.hp == user.max_hp and target.hp < target.max_hp


def test_shield_dust_blocks_guaranteed_secondary_status_and_keeps_direct_damage():
    battle, user, target = build_battle(defender_ability="Shield Dust")
    use(battle, user, target, "Nuzzle")
    assert not target.status and target.hp < target.max_hp


def test_shield_dust_does_not_block_a_primary_status_move():
    battle, user, target = build_battle(defender_ability="Shield Dust")
    use(battle, user, target, "Thunder Wave")
    assert target.status == "par"


def test_shield_dust_belongs_to_the_recipient_of_the_secondary():
    battle, user, target = build_battle(attacker_ability="Shield Dust")
    use(battle, user, target, "Nuzzle")
    assert target.status == "par"


def test_secondary_status_does_not_leak_through_a_substitute():
    battle, user, target = build_battle()
    use(battle, target, target, "Substitute")
    previous = target.hp
    use(battle, user, target, "Nuzzle")
    assert target.hp == previous and not target.status


def crits(ability, status, seed, defender_ability=None):
    """Read per-hit critical decisions from the real damage calculator."""
    from pokemon.battle.damage import damage_calc
    from pokemon.dex.entities import Move

    battle, user, target = build_battle(attacker_ability=ability, defender_ability=defender_ability)
    target.status = status
    move = Move(name="Water Gun", num=0, type="Water", category="Special", power=40,
                accuracy=100, pp=25, raw={"basePower": 40, "category": "Special", "type": "Water"})
    return damage_calc(user, target, move, battle=battle, rng=random.Random(seed)).debug["critical"]


@pytest.mark.parametrize("status", ["psn", "tox"])
def test_merciless_guarantees_each_critical_against_poison(status):
    assert all(all(crits("Merciless", status, seed)) for seed in range(12))


@pytest.mark.parametrize("status", ["", "brn", "par", "slp"])
def test_merciless_does_not_raise_critical_chance_for_unqualified_status(status):
    assert [crits("Merciless", status, seed) for seed in range(30)] == [crits(None, status, seed) for seed in range(30)]


def test_merciless_preserves_battle_armor_critical_prevention():
    assert crits("Merciless", "psn", 0, "Battle Armor") == [False]


def spa(pokemon):
    """Read either supported stage-key representation."""
    return pokemon.boosts.get("special_attack", pokemon.boosts.get("spa", 0))


def test_berserk_uses_the_actual_before_hit_hp_for_a_half_hp_crossing():
    battle, user, target = build_battle(defender_ability="Berserk")
    target.hp = 110
    use(battle, user, target, "Tackle")
    assert target.hp < 100 and spa(target) == 1
    use(battle, user, target, "Tackle")
    assert spa(target) == 1


@pytest.mark.parametrize("hp", [80, 180])
def test_berserk_does_not_trigger_without_crossing_the_threshold(hp):
    battle, user, target = build_battle(defender_ability="Berserk")
    target.hp = hp
    use(battle, user, target, "Tackle")
    assert spa(target) == 0


def test_berserk_ignores_an_old_hit_during_a_later_harmless_move():
    battle, user, target = build_battle(defender_ability="Berserk")
    target.hp = 110
    use(battle, user, target, "Tackle")
    assert spa(target) == 1
    battle.turn_count += 1
    use(battle, user, target, "Growl")
    assert spa(target) == 1


def test_berserk_does_not_trigger_for_sheer_force_suppressed_effects():
    battle, user, target = build_battle(attacker_ability="Sheer Force", defender_ability="Berserk")
    target.hp = 110
    use(battle, user, target, "Water Pulse")
    assert target.hp < 100 and spa(target) == 0


def test_berserk_boosts_before_then_allows_the_delayed_healing_berry():
    battle, user, target = build_battle(defender_ability="Berserk")
    battle.set_item(target, "Oran Berry")
    target.hp = 110
    use(battle, user, target, "Tackle")
    assert spa(target) == 1
    assert not battle._holder_item(target)
    assert target.hp == 80


def test_soul_heart_receives_the_actual_opposing_faint_without_an_entry_bonus():
    battle, user, target = build_battle(attacker_ability="Soul-Heart")
    battle.award_xp = battle.award_txp = False
    battle.start_turn()
    assert spa(user) == 0
    target.hp = 1
    use(battle, user, target, "Tackle")
    battle.run_faint()
    assert target.hp == 0 and spa(user) == 1


def test_soul_heart_also_triggers_after_an_indirect_opposing_faint():
    battle, user, target = build_battle(attacker_ability="Soul-Heart")
    battle.award_xp = battle.award_txp = False
    target.hp = 1
    target.status = "psn"
    battle.residual()
    assert target.hp == 0 and spa(user) == 1


def test_soul_heart_does_not_boost_a_fainted_holder():
    battle, user, target = build_battle(attacker_ability="Soul-Heart")
    user.hp = 0
    target.hp = 0
    battle.on_faint(target)
    assert spa(user) == 0
