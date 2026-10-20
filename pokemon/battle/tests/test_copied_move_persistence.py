"""Temporary copies need independent PP and checkpoint-safe switch reversion."""

import logging
import random
from types import SimpleNamespace

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


def learned(name, pp):
    move = load_modules()["Move"](name)
    move.pp = pp
    return move


def use(battle, user, target, name):
    battle.rng = random.Random(1)
    battle.use_move(action(battle, user, target, name))
    assert not getattr(battle, "_callback_failures", [])


def test_mimic_uses_full_base_pp_with_an_independent_move_and_reverts():
    battle, user, target = build_battle()
    user.moves = [learned("Mimic", 10)]
    target.moves = [learned("Tackle", 2)]
    target.last_move = action(battle, target, user, "Tackle").move
    target.last_move.pp = 2
    use(battle, user, target, "Mimic")
    assert user.moves[0].name == "Tackle" and user.moves[0].pp == 35
    assert user.moves[0] is not target.moves[0] and user.moves[0] is not target.last_move
    use(battle, user, target, "Tackle")
    assert user.moves[0].pp == 34 and target.moves[0].pp == target.last_move.pp == 2
    battle.on_switch_out(user)
    assert user.moves[0].name == "Mimic" and user.moves[0].pp == 9


def test_mimic_cannot_copy_an_already_known_or_forbidden_move():
    battle, user, target = build_battle()
    user.moves = [learned("Mimic", 10), learned("Tackle", 35)]
    target.last_move = action(battle, target, user, "Tackle").move
    use(battle, user, target, "Mimic")
    assert user.moves[0].name == "Mimic"
    target.last_move = action(battle, target, user, "Struggle").move
    use(battle, user, target, "Mimic")
    assert user.moves[0].name == "Mimic"


def test_transform_copies_non_hp_stats_stages_types_ability_and_independent_five_pp():
    from pokemon.battle.utils import get_modified_stat
    battle, user, target = build_battle(attacker_ability="Own Tempo", defender_ability="Water Absorb", defender_types=["Water"])
    user.moves, target.moves = [learned("Transform", 10)], [learned("Splash", 39)]
    target.base_stats.attack = 250
    target.boosts["attack"] = 2
    hp, maximum, original_species = user.hp, user.max_hp, user.species
    use(battle, user, target, "Transform")
    assert user.hp == hp and user.max_hp == maximum
    assert user.species == target.species and user.types == ["Water"]
    assert user.moves[0].pp == 5 and user.moves[0] is not target.moves[0]
    assert get_modified_stat(user, "attack") == 500
    use(battle, user, user, "Splash")
    assert user.moves[0].pp == 4 and target.moves[0].pp == 39
    restored = load_modules()["Pokemon"].from_dict(user.to_dict())
    assert restored.moves[0].name == "Splash" and restored.moves[0].pp == 4
    assert get_modified_stat(restored, "attack") == 500
    battle.on_switch_out(user)
    assert user.species == original_species and user.moves[0].name == "Transform"
    assert user.moves[0].pp == 9 and get_modified_stat(user, "attack") == 120


def test_transform_respects_the_one_pp_move_exception():
    battle, user, target = build_battle()
    user.moves, target.moves = [learned("Transform", 10)], [learned("Revival Blessing", 1)]
    use(battle, user, target, "Transform")
    assert user.moves[0].pp == 1


def test_transform_cannot_copy_a_substitute_or_an_already_transformed_target():
    for condition in ("substitute", "transformed"):
        battle, user, target = build_battle()
        user.moves, target.moves = [learned("Transform", 10)], [learned("Splash", 39)]
        if condition == "substitute":
            target.volatiles["substitute"] = {"hp": 50}
        else:
            target.transformed = True
        use(battle, user, target, "Transform")
        assert user.moves[0].name == "Transform"


def test_temporary_transform_pp_never_spends_the_same_named_owned_slot():
    battle, user, target = build_battle()
    user.moves = [learned("Transform", 10), learned("Tackle", 20)]
    target.moves = [learned("Tackle", 35)]
    saved = []
    slots = [SimpleNamespace(move=SimpleNamespace(name=name), slot=index, current_pp=pp,
                             save=lambda **kwargs: saved.append(True))
             for index, name, pp in [(1, "Transform", 10), (2, "Tackle", 20)]]
    user.activemoveslot_set = SimpleNamespace(all=lambda: slots)
    use(battle, user, target, "Transform")
    use(battle, user, target, "Tackle")
    assert user.moves[0].pp == 4 and slots[0].current_pp == 9 and slots[1].current_pp == 20
    assert len(saved) == 1
