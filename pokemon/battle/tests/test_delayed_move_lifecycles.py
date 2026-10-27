"""Delayed and turn-limited moves need actual later-turn outcomes and controls."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules
from .test_pending_action_effects import action


@pytest.fixture(autouse=True)
def quiet_log():
    logger = logging.getLogger("battle")
    old = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = old


def use(battle, user, target, name):
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, name))
    assert not getattr(battle, "_callback_failures", [])


def test_ingrain_heals_through_residual_and_prevents_switching():
    battle, user, target = build_battle()
    user.hp = 80
    use(battle, user, user, "Ingrain")
    battle.residual()
    assert user.hp == 92 and battle._is_trapped(user)
    battle.on_switch_out(user)
    assert "ingrain" not in user.volatiles


@pytest.mark.parametrize("ability,starting_status,expected", [(None, None, "slp"), ("Insomnia", None, None), (None, "brn", "brn")])
def test_yawn_finishes_after_two_residuals_without_overwriting_status(ability, starting_status, expected):
    battle, user, target = build_battle(defender_ability=ability)
    use(battle, user, target, "Yawn")
    battle.residual()
    assert not target.status
    if starting_status:
        target.status = starting_status
    battle.residual()
    assert (target.status or None) == expected
    assert "yawn" not in target.volatiles


def test_perish_song_counts_three_then_two_then_one_then_faints():
    battle, user, target = build_battle()
    use(battle, user, user, "Perish Song")
    for index in range(3):
        battle.residual()
        assert user.hp > 0 and target.hp > 0
    battle.residual()
    assert user.hp == target.hp == 0


def test_perish_song_preserves_soundproof_and_switch_removal():
    battle, user, target = build_battle(defender_ability="Soundproof")
    use(battle, user, user, "Perish Song")
    assert "perishsong" in user.volatiles and "perishsong" not in target.volatiles
    battle.on_switch_out(user)
    assert "perishsong" not in user.volatiles


def test_bide_accumulates_two_actual_hits_and_spends_one_pp_for_release():
    battle, user, target = build_battle()
    learned = load_modules()["Move"]("Bide")
    learned.pp = 10
    user.moves = [learned]
    for _ in range(2):
        use(battle, user, target, "Bide")
        assert target.hp == target.max_hp
        use(battle, target, user, "Tackle")
    accumulated = user.max_hp - user.hp
    use(battle, user, target, "Bide")
    assert target.max_hp - target.hp == accumulated * 2
    assert learned.pp == 9 and "bide" not in user.volatiles


def test_bide_without_qualifying_damage_has_no_release_damage():
    battle, user, target = build_battle()
    for _ in range(3):
        use(battle, user, target, "Bide")
    assert target.hp == target.max_hp and "bide" not in user.volatiles


@pytest.mark.parametrize("incoming,expected", [("Tackle", True), ("Water Gun", False), ("Splash", False)])
def test_shell_trap_is_armed_before_attacks_and_requires_physical_damage(incoming, expected):
    battle, user, target = build_battle()
    battle.rng = random.Random(1)
    battle.execute_turn([action(battle, user, target, "Shell Trap"), action(battle, target, user, incoming)])
    assert (target.hp < target.max_hp) is expected
    assert "shelltrap" not in user.volatiles


def test_ion_deluge_changes_a_qualifying_normal_attack_only_for_one_turn():
    battle, user, target = build_battle(attacker_types=["Ghost"])
    battle.rng = random.Random(1)
    battle.execute_turn([action(battle, user, target, "Ion Deluge"), action(battle, target, user, "Tackle")])
    assert user.hp < user.max_hp
    hp = user.hp
    use(battle, target, user, "Tackle")
    assert user.hp == hp


@pytest.mark.parametrize("incoming,blocked", [("Tackle", True), ("Growl", False)])
def test_mat_block_first_turn_protects_damage_but_allows_status(incoming, blocked):
    battle, user, target = build_battle()
    user.base_stats.speed = 400
    battle.rng = random.Random(1)
    battle.start_turn()
    battle.execute_turn([action(battle, user, user, "Mat Block"), action(battle, target, user, incoming)])
    assert user.hp == user.max_hp
    if not blocked:
        assert user.boosts.get("attack", user.boosts.get("atk", 0)) == -1
    battle.start_turn()
    battle.execute_turn([action(battle, user, user, "Mat Block"), action(battle, target, user, "Tackle")])
    assert user.hp < user.max_hp
