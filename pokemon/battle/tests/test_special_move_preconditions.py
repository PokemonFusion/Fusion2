"""Reproduced conditional move failures must retain their intended negatives."""

import logging
import random

import pytest

from .helpers import build_battle, load_modules


@pytest.fixture(autouse=True)
def quiet_offline_battle_log():
    """Keep this offline diagnostic process from writing the live battle log."""
    logger = logging.getLogger("battle")
    disabled = logger.disabled
    logger.disabled = True
    yield
    logger.disabled = disabled


def use(battle, user, target, name):
    """Run a named move through the real hydrated engine path."""
    from pokemon.battle.actions import Action, ActionType

    move = load_modules()["BattleMove"](name)
    battle.rng = random.Random(0)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user))
    assert not getattr(battle, "_callback_failures", [])
    return move


def test_endeavor_lowers_the_targets_hp_to_the_lower_users_hp():
    battle, user, target = build_battle()
    user.hp = 80
    use(battle, user, target, "Endeavor")
    assert target.hp == 80


@pytest.mark.parametrize("target_hp,types", [(40, ["Normal"]), (200, ["Ghost"])])
def test_endeavor_preserves_the_hp_and_type_immunity_negatives(target_hp, types):
    battle, user, target = build_battle(defender_types=types)
    user.hp, target.hp = 80, target_hp
    use(battle, user, target, "Endeavor")
    assert target.hp == target_hp


def test_conversion_reads_the_real_first_moves_dex_type():
    battle, user, target = build_battle(attacker_types=["Psychic"])
    Move = load_modules()["Move"]
    user.moves = [Move("Tackle"), Move("Conversion")]
    use(battle, user, target, "Conversion")
    assert user.types == ["Normal"]


def test_conversion_two_resists_the_targets_previous_move_instead_of_copying_its_type():
    battle, user, target = build_battle(attacker_types=["Psychic"], defender_types=["Water"])
    target.last_move = load_modules()["BattleMove"]("Tackle")
    use(battle, user, target, "Conversion 2")
    assert len(user.types) == 1 and user.types[0] in {"Rock", "Steel", "Ghost"}


def test_conversion_two_without_a_previous_move_preserves_the_users_type():
    battle, user, target = build_battle(attacker_types=["Psychic"])
    use(battle, user, target, "Conversion 2")
    assert user.types == ["Psychic"]


def test_last_resort_works_after_all_other_real_moves_were_attempted():
    battle, user, target = build_battle()
    Move = load_modules()["Move"]
    user.moves = [Move("Last Resort"), Move("Splash")]
    use(battle, user, user, "Splash")
    use(battle, user, target, "Last Resort")
    assert target.hp < target.max_hp


@pytest.mark.parametrize("other", [True, False])
def test_last_resort_fails_with_an_unused_other_move_or_no_other_move(other):
    battle, user, target = build_battle()
    Move = load_modules()["Move"]
    user.moves = [Move("Last Resort")] + ([Move("Splash")] if other else [])
    use(battle, user, target, "Last Resort")
    assert target.hp == target.max_hp


def test_last_resort_usage_resets_when_the_holder_leaves():
    battle, user, target = build_battle()
    Move = load_modules()["Move"]
    user.moves = [Move("Last Resort"), Move("Splash")]
    use(battle, user, user, "Splash")
    battle.on_switch_out(user)
    battle.on_enter_battle(user)
    use(battle, user, target, "Last Resort")
    assert target.hp == target.max_hp


def test_geomancy_charges_without_boosting_then_boosts_once_and_spends_one_pp():
    battle, user, target = build_battle()
    learned = load_modules()["Move"]("Geomancy")
    learned.pp = 10
    user.moves = [learned]
    use(battle, user, user, "Geomancy")
    assert all(value == 0 for value in user.boosts.values())
    assert user.moves[0].pp == 9
    use(battle, user, user, "Geomancy")
    from pokemon.utils.boosts import STAT_KEY_MAP

    assert all(user.boosts[STAT_KEY_MAP[stat]] == 2 for stat in ("spa", "spd", "spe"))
    assert user.moves[0].pp == 9


def test_stuff_cheeks_consumes_a_berry_above_its_normal_hp_threshold():
    battle, user, target = build_battle()
    battle.set_item(user, "Oran Berry")
    use(battle, user, user, "Stuff Cheeks")
    assert user.boosts.get("defense") == 2
    assert not user.item


def test_stuff_cheeks_without_a_berry_cannot_grant_a_defense_boost():
    battle, user, target = build_battle()
    battle.set_item(user, "Leftovers")
    use(battle, user, user, "Stuff Cheeks")
    assert user.boosts.get("defense") == 0
    assert user.item


def test_stuff_cheeks_at_the_stage_cap_does_not_consume_the_berry():
    battle, user, target = build_battle()
    battle.set_item(user, "Oran Berry")
    user.boosts["defense"] = 6
    use(battle, user, user, "Stuff Cheeks")
    assert user.item and user.boosts["defense"] == 6


def test_teatime_forces_both_healthy_active_pokemon_to_eat_their_berries():
    battle, user, target = build_battle()
    for pokemon in (user, target):
        battle.set_item(pokemon, "Oran Berry")
    use(battle, user, target, "Teatime")
    assert not user.item and not target.item


def test_forced_berry_consumption_still_respects_the_generic_item_use_gate(monkeypatch):
    battle, user, target = build_battle()
    battle.set_item(user, "Oran Berry")
    monkeypatch.setattr(battle, "use_item", lambda *args, **kwargs: False)
    assert battle.eat_item(user, force=True) is False
    assert user.item


@pytest.mark.parametrize("name", ["Conversion", "Conversion 2"])
def test_conversion_moves_cannot_replace_terastallized_typing(name):
    battle, user, target = build_battle(attacker_types=["Water"])
    user.terastallized = "Water"
    user.moves = [load_modules()["Move"]("Tackle")]
    target.last_move = load_modules()["BattleMove"]("Tackle")
    use(battle, user, target, name)
    assert user.types == ["Water"]
