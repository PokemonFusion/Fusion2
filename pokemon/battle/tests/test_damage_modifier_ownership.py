"""Offensive and defensive damage hooks belong to opposite event roles."""

import random

from .helpers import build_battle, load_modules


class DamageHooks:
    """Independent arithmetic probes for event direction and invocation count."""

    name = "Damage ownership probe"

    def __init__(self, *, offensive=None, defensive=None):
        self.offensive, self.defensive = offensive, defensive
        self.calls = []

    def call(self, hook, value=None, *args, **kwargs):
        if hook == "onModifyDamage" and self.offensive:
            self.calls.append(hook)
            return self.offensive(value)
        if hook == "onSourceModifyDamage" and self.defensive:
            self.calls.append(hook)
            return self.defensive(value)
        return None


def strike(*, attacker_ability=None, defender_ability=None, defender_types=None, name="Tackle"):
    """Run the real move path with equal formula inputs and deterministic RNG."""
    from pokemon.battle.actions import Action, ActionType

    battle, user, target = build_battle(attacker_ability=attacker_ability, defender_ability=defender_ability,
                                      defender_types=defender_types)
    battle.rng = random.Random(0)
    from pokemon import dex
    from pokemon.names import normalize_name

    raw = dict(dex.MOVEDEX[normalize_name(name)].raw)
    move = load_modules()["BattleMove"](name, power=raw.get("basePower", 0),
                                       type=raw["type"], raw=raw)
    battle.use_move(Action(battle.participant_for(user), ActionType.MOVE, battle.participant_for(target),
                           move, pokemon=user))
    return target.max_hp - target.hp


def test_offensive_modify_damage_runs_once_on_the_attacker():
    ability = DamageHooks(offensive=lambda damage: damage * 2)
    control = strike()
    assert strike(attacker_ability=ability) == control * 2
    assert ability.calls == ["onModifyDamage"]


def test_defensive_source_modifier_does_not_reduce_its_holders_outgoing_damage():
    ability = DamageHooks(defensive=lambda damage: damage // 2)
    assert strike(attacker_ability=ability) == strike()
    assert ability.calls == []


def test_defensive_source_modifier_runs_once_for_the_defender():
    ability = DamageHooks(defensive=lambda damage: damage // 2)
    control = strike()
    assert strike(defender_ability=ability) == control // 2
    assert ability.calls == ["onSourceModifyDamage"]


def test_real_punk_rock_boosts_its_own_sound_move():
    assert strike(attacker_ability="Punk Rock", name="Round") > strike(name="Round")


def test_real_punk_rock_halves_an_incoming_sound_move_once():
    control = strike(name="Round")
    assert strike(defender_ability="Punk Rock", name="Round") == control // 2


def test_defender_type_conversion_does_not_rewrite_the_opponents_move():
    assert strike(defender_types=["Ghost"]) == 0
    assert strike(defender_ability="Aerilate", defender_types=["Ghost"]) == 0


def test_reckless_reads_real_recoil_metadata_without_boosting_ordinary_attacks():
    assert strike(attacker_ability="Reckless", name="Take Down") > strike(name="Take Down")
    assert strike(attacker_ability="Reckless") == strike()
