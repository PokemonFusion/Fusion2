"""Outcome regressions for failures retained by the ordinary-login catalog run."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_offline_log():
    """Keep unit evidence separate from local game-session log correlation."""
    logger = logging.getLogger("battle")
    disabled = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = disabled


def use(battle, user, target, name, seed=1):
    """Execute the real move pipeline without replacing any callback."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(seed)
    move = load_modules()["BattleMove"](name, pp=35)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user))
    assert not getattr(battle, "_callback_failures", [])
    return move


def damage(ability=None, move="Tackle", item=None, *, target_ability=None, target_boost=0, user_boost=0):
    """Measure actual HP loss with independently selected effects and stages."""
    battle, user, target = build_battle(attacker_ability=ability, defender_ability=target_ability)
    user.boosts["attack"] = user_boost
    target.boosts["defense"] = target_boost
    if item:
        user.item = battle._coerce_item(item)
        assert user.item is not None
    use(battle, user, target, move)
    return target.max_hp - target.hp


def test_sniper_adds_its_bonus_only_to_an_actual_critical():
    assert damage("Sniper", "Frost Breath") > damage(None, "Frost Breath")
    assert damage("Sniper", "Tackle") == damage(None, "Tackle")
    assert damage("Sniper", "Frost Breath", target_ability="Battle Armor") == damage(None, "Frost Breath", target_ability="Battle Armor")


@pytest.mark.parametrize("name,expected", [("Frost Breath", 6), ("Water Gun", 0)])
def test_anger_point_requires_an_actual_critical_hit(name, expected):
    battle, user, target = build_battle(defender_ability="Anger Point")
    use(battle, user, target, name)
    assert target.boosts.get("attack", target.boosts.get("atk", 0)) == expected


def test_klutz_suppresses_the_item_effect_without_removing_the_item():
    assert damage("Klutz", item="choiceband") == damage(None)
    assert damage(None, item="choiceband") > damage(None)
    battle, user, target = build_battle(attacker_ability="Klutz")
    item = user.item = battle._coerce_item("choiceband")
    use(battle, user, target, "Tackle")
    assert user.item is item


def test_unaware_ignores_opposing_offense_but_keeps_its_own_stages():
    assert damage(target_ability="Unaware", user_boost=6) == damage(target_ability="Unaware")
    assert damage(target_ability="Unaware", target_boost=2) < damage(target_ability="Unaware")


def test_unaware_ignores_opposing_defense_but_keeps_its_own_offense():
    assert damage("Unaware", target_boost=6) == damage("Unaware")
    assert damage("Unaware", user_boost=2) > damage("Unaware")


@pytest.mark.parametrize("ability,move", [("Tablets of Ruin", "Tackle"), ("Vessel of Ruin", "Water Gun")])
def test_ruin_holder_reduces_the_other_attackers_stat(ability, move):
    assert damage(target_ability=ability, move=move) < damage(move=move)
    assert damage(ability=ability, move=move) == damage(move=move)


@pytest.mark.parametrize("ability,expected", [(None, 50), ("Ripen", 100)])
def test_ripen_doubles_the_real_sitrus_heal_and_consumes_once(ability, expected):
    battle, user, target = build_battle(attacker_ability=ability)
    user.item = battle._coerce_item("sitrusberry")
    user.hp = 40
    assert battle.eat_item(user, force=True)
    assert user.hp == 40 + expected
    assert not user.item
    assert not battle.eat_item(user, force=True)
    assert not getattr(user, "ripen_active", False)


def test_ripen_does_not_double_an_unrelated_later_recover():
    battle, user, target = build_battle(attacker_ability="Ripen")
    user.item, user.hp = battle._coerce_item("oranberry"), 40
    assert battle.eat_item(user, force=True)
    assert user.hp == 60
    use(battle, user, user, "Recover")
    assert user.hp == 160


@pytest.mark.parametrize("ability,hp,eaten", [("Gluttony", 90, True), ("Gluttony", 110, False), (None, 90, False)])
def test_gluttony_uses_a_real_half_hp_berry_without_shadowing_eat_item(ability, hp, eaten):
    battle, user, target = build_battle(attacker_ability=ability)
    user.item, user.hp = battle._coerce_item("figyberry"), hp
    battle.register_handlers(user)
    battle.dispatcher.dispatch("update", pokemon=user, battle=battle)
    user.item.call("onUpdate", pokemon=user, battle=battle) if user.item else None
    assert callable(user.eat_item)
    assert (not user.item) is eaten
    assert user.hp == hp + (user.max_hp // 3 if eaten else 0)


def test_innards_out_returns_actual_remaining_hp_and_respects_magic_guard():
    for ability, expected in [(None, 20), ("Magic Guard", 0)]:
        battle, user, target = build_battle(attacker_ability=ability, defender_ability="Innards Out")
        target.hp = 20
        use(battle, user, target, "Psychic")
        assert target.hp == 0
        assert user.max_hp - user.hp == expected


def test_innards_out_does_not_trigger_for_a_surviving_hit():
    battle, user, target = build_battle(defender_ability="Innards Out")
    use(battle, user, target, "Water Gun")
    assert target.hp > 0 and user.hp == user.max_hp


def test_truant_skips_second_action_without_pp_then_resumes():
    battle, user, target = build_battle(attacker_ability="Truant")
    first = use(battle, user, target, "Tackle")
    first_loss = target.max_hp - target.hp
    assert first_loss > 0
    second = use(battle, user, target, "Tackle")
    assert target.max_hp - target.hp == first_loss
    assert second.pp == 35
    use(battle, user, target, "Tackle")
    assert target.max_hp - target.hp == first_loss * 2


@pytest.mark.parametrize("ability,comparison", [("Heavy Metal", "greater"), ("Light Metal", "less")])
@pytest.mark.parametrize("name", ["Low Kick", "Grass Knot"])
def test_weight_moves_consume_effective_ability_weight(ability, comparison, name):
    losses = []
    for effect in (None, ability):
        battle, user, target = build_battle(defender_ability=effect)
        target.weightkg = 60 if ability == "Heavy Metal" else 95
        use(battle, user, target, name)
        losses.append(target.max_hp - target.hp)
    assert losses[1] > losses[0] if comparison == "greater" else losses[1] < losses[0]


def test_prepared_struggle_damages_ghost_and_has_fixed_max_hp_recoil():
    battle, user, target = build_battle(defender_types=["Ghost"])
    use(battle, user, target, "Struggle")
    assert target.hp < target.max_hp
    assert user.hp == user.max_hp - user.max_hp // 4


@pytest.mark.parametrize("level", [1, 50, 100])
def test_shedinja_fixed_hp_is_calculated_without_writing_any_model(level):
    from pokemon.helpers.pokemon_helpers import calculate_stats
    assert calculate_stats("Shedinja", level, {}, {}, "Hardy")["hp"] == 1


def test_skill_link_maximizes_a_variable_count_without_changing_a_fixed_count():
    ordinary = damage(move="Icicle Spear", target_ability="Battle Armor")
    assert damage("Skill Link", "Icicle Spear", target_ability="Battle Armor") > ordinary
    assert damage("Skill Link", "Double Kick", target_ability="Battle Armor") == damage(move="Double Kick", target_ability="Battle Armor")
    assert damage("Skill Link", "Tackle", target_ability="Battle Armor") == damage(move="Tackle", target_ability="Battle Armor")


def test_parental_bond_second_hit_is_quarter_strength_and_does_not_add_to_multihit():
    ordinary = damage(target_ability="Battle Armor")
    actual = damage("Parental Bond", target_ability="Battle Armor")
    assert ordinary < actual < ordinary * 1.5
    assert damage("Parental Bond", "Double Kick", target_ability="Battle Armor") == damage(move="Double Kick", target_ability="Battle Armor")
