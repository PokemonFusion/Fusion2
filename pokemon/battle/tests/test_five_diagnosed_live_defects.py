"""Regressions for five defects reproduced by the full logged-in dex sweep."""

import copy
import random

import pytest

from .helpers import build_battle, load_modules


def native(species, ability=None, *, level=50):
    """Prepare a calculated native carrier without writing owned records."""
    from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

    battle, user, target = build_battle(attacker_ability=ability)
    user.name = user.species = user.base_species = species
    user.level = level
    user.ivs = [31, 25, 21, 19, 17, 15]
    user.evs = [100, 80, 60, 40, 20, 0]
    user.nature = "Adamant"
    user.max_hp = get_max_hp(user)
    user.hp = user.max_hp
    user.base_stats = load_modules()["Stats"](**get_stats(user))
    return battle, user, target


def use(battle, user, target, name, *, seed=1):
    """Execute an ordinary action against a deterministic hit window."""
    from pokemon.battle.actions import Action, ActionType

    battle.rng = random.Random(seed)
    move = load_modules()["BattleMove"](name)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE,
                           battle.participant_for(target), move, pokemon=user, target_pokemon=target))
    assert not getattr(battle, "_callback_failures", [])
    return move


@pytest.mark.parametrize("level", [50, 100])
@pytest.mark.parametrize("species,form", [
    ("Castform", "Castform-Sunny"), ("Cherrim", "Cherrim-Sunshine"),
    ("Aegislash", "Aegislash-Blade"), ("Darmanitan", "Darmanitan-Zen"),
    ("Darmanitan-Galar", "Darmanitan-Galar-Zen"), ("Morpeko", "Morpeko-Hangry"),
    ("Wishiwashi", "Wishiwashi-School"),
])
def test_native_form_calculates_stats_retains_training_and_roundtrips(level, species, form):
    from pokemon.helpers.pokemon_helpers import get_stats

    _, user, _ = native(species, level=level)
    user.hp -= 13
    training = (list(user.ivs), list(user.evs), user.nature, user.level)
    user.boosts["attack"] = 2
    maximum = user.max_hp
    for name in (form, species):
        assert user.formeChange(name, preserve_ability=True)
        assert vars(user.base_stats) == get_stats(user)
        assert user.max_hp == maximum and user.hp == maximum - 13
        assert user.boosts["attack"] == 2
        assert (user.ivs, user.evs, user.nature, user.level) == training
        restored = load_modules()["Pokemon"].from_dict(user.to_dict())
        assert restored.species == name and vars(restored.base_stats) == get_stats(restored)


@pytest.mark.parametrize("fainted", [False, True])
def test_power_construct_hp_change_preserves_damage_and_never_revives(fainted):
    from pokemon.helpers.pokemon_helpers import get_max_hp

    _, user, _ = native("Zygarde", "Power Construct")
    user.hp = 0 if fainted else user.max_hp // 4
    damage = user.max_hp - user.hp
    assert user.formeChange("Zygarde-Complete")
    assert user.max_hp == get_max_hp(user)
    assert user.hp == (0 if fainted else user.max_hp - damage)
    assert load_modules()["Pokemon"].from_dict(user.to_dict()).max_hp == user.max_hp


def test_unknown_form_is_rejected_without_mutating_runtime_identity():
    _, user, _ = native("Minior")
    before = user.to_dict()
    assert not user.formeChange("Minior-Core")
    assert user.to_dict() == before


@pytest.mark.parametrize("fraction,expected", [(1, "Minior-Meteor"), (.5, "Minior"), (.25, "Minior")])
def test_shields_down_valid_names_at_both_thresholds_and_after_healing(fraction, expected):
    from pokemon.dex.functions.abilities_funcs import Shieldsdown

    _, user, _ = native("Minior", "Shields Down")
    handler = Shieldsdown()
    user.hp = int(user.max_hp * fraction)
    handler.onStart(user)
    assert user.species == expected
    user.hp = user.max_hp // 4
    handler.onResidual(user)
    assert user.species == "Minior"
    user.hp = user.max_hp
    handler.onResidual(user)
    assert user.species == "Minior-Meteor"
    assert user.setStatus("psn") is False


@pytest.mark.parametrize("ability,species", [("Shields Down", "Minior"), ("Schooling", "Wishiwashi")])
@pytest.mark.parametrize("state", ["transformed", "fainted"])
def test_native_ability_form_guards(ability, species, state):
    from pokemon.dex.functions.abilities_funcs import Schooling, Shieldsdown

    _, user, _ = native(species, ability)
    user.transformed = state == "transformed"
    if state == "fainted":
        user.hp = 0
    (Schooling() if species == "Wishiwashi" else Shieldsdown()).onResidual(user)
    assert user.species == species


@pytest.mark.parametrize("level,fraction,expected", [
    (19, 1, "Wishiwashi"), (20, 1, "Wishiwashi-School"),
    (20, .25, "Wishiwashi"), (100, 1, "Wishiwashi-School"),
])
def test_schooling_level_and_hp_boundaries(level, fraction, expected):
    from pokemon.dex.functions.abilities_funcs import Schooling

    _, user, _ = native("Wishiwashi", "Schooling", level=level)
    user.hp = int(user.max_hp * fraction)
    Schooling().onStart(user)
    assert user.species == expected


def test_instruct_repeat_spends_pp_and_reports_the_called_attack(monkeypatch):
    battle, instructor, target = build_battle()
    messages = []
    monkeypatch.setattr(battle, "log_action", messages.append)
    modules = load_modules()
    learned = modules["Move"]("Tackle")
    learned.pp = 10
    target.moves = [learned]
    use(battle, target, instructor, "Tackle")
    before_hp = instructor.hp
    use(battle, instructor, target, "Instruct")
    assert instructor.hp < before_hp and learned.pp == 8
    assert any("Instruct and called Tackle" in row for row in messages)
    assert not any("Instruct" in row and "no effect" in row for row in messages)


@pytest.mark.parametrize("name,pp", [("Tackle", 0), ("Fly", 10), ("Hyper Beam", 10), ("Instruct", 10)])
def test_instruct_rejects_empty_pp_and_disallowed_repeats(name, pp):
    battle, instructor, target = build_battle()
    learned = load_modules()["Move"](name)
    learned.pp = pp
    target.moves = [learned]
    target.last_move = load_modules()["BattleMove"](name)
    use(battle, instructor, target, "Instruct")
    assert not getattr(battle, "called_moves", []) and learned.pp == pp


@pytest.mark.parametrize("blocked,full", [(False, False), (True, False), (False, True)])
def test_present_healing_obeys_hp_cap_and_heal_block_and_preserves_dex(monkeypatch, blocked, full):
    from pokemon.dex import MOVEDEX

    battle, user, target = build_battle(attacker_ability="No Guard")
    target.hp = target.max_hp if full else 70
    if blocked:
        battle.apply_volatile_status(target, "healblock", source=user)
    before = target.hp
    dex_before = copy.deepcopy(MOVEDEX["present"].raw)
    monkeypatch.setattr(random, "randint", lambda *args: 1)
    use(battle, user, target, "Present")
    expected = before if blocked or full else before + target.max_hp // 4
    assert target.hp == expected
    assert MOVEDEX["present"].raw == dex_before


def test_present_reused_move_clears_heal_branch_before_damaging_roll(monkeypatch):
    from pokemon.dex.functions.moves.damage_moves import Present

    move = load_modules()["BattleMove"]("Present")
    monkeypatch.setattr(random, "randint", lambda *args: 1)
    Present().onModifyMove(move)
    assert move.raw["heal"] == [1, 4]
    monkeypatch.setattr(random, "randint", lambda *args: 95)
    Present().onModifyMove(move)
    assert "heal" not in move.raw and "bypassSub" not in move.raw and move.heal is None and move.power == 120


@pytest.mark.parametrize("roll,heals", [(1, True), (95, False)])
def test_present_only_its_healing_branch_bypasses_substitute(monkeypatch, roll, heals):
    battle, user, target = build_battle(attacker_ability="No Guard")
    target.hp = 70
    target.volatiles["substitute"] = {"hp": 150}
    monkeypatch.setattr(random, "randint", lambda *args: roll)
    use(battle, user, target, "Present")
    assert target.hp == (120 if heals else 70)
    assert target.volatiles["substitute"]["hp"] == 150 if heals else target.volatiles["substitute"]["hp"] < 150


def test_present_healing_can_miss_and_does_not_heal_after_a_miss(monkeypatch):
    battle, user, target = build_battle()
    target.hp = 70
    monkeypatch.setattr(random, "randint", lambda *args: 1)
    use(battle, user, target, "Present", seed=2)
    assert target.hp == 70
