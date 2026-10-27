"""Real consumers required before releasing the remaining canonical Mega pairs."""

import copy
import random
from unittest.mock import patch

import pytest

from .helpers import build_battle
from .test_pending_action_effects import action, doubles


@pytest.mark.parametrize(
    "weather,ability",
    [("sunnyday", "Drought"), ("snow", "Snow Warning"), ("sandstorm", "Sand Stream")],
)
@pytest.mark.parametrize("suppressed", [False, True])
def test_explicit_owned_start_context_and_suppression(weather, ability, suppressed):
    """Only the new explicit boundary starts one effective weather ability."""
    battle, user, _ = build_battle()
    user.ability_suppressed = suppressed
    user.setAbility(ability, battle=battle, is_from_forme_change=True, run_start=False)
    assert not battle.field.weather
    battle.start_owned_ability(user)
    assert (battle.field.weather or "") == ("" if suppressed else weather)


def test_trace_copies_executable_ability_state_and_uses_private_rng():
    """Rich ability objects, handler startup and notrace flags govern the copy."""
    from pokemon.battle.effect_context import EffectContext
    from pokemon.battle.engine import _resolve_ability

    battle, user, ally, foe, other = doubles()
    user.setAbility("Trace", battle=battle, is_from_forme_change=True, run_start=False)
    foe.ability = _resolve_ability("Drought")
    other.ability = _resolve_ability("Multitype")
    before = random.getstate()
    battle.start_owned_ability(user)
    assert EffectContext.key(user.ability) == "drought"
    assert user.ability_state["target"] is user
    assert battle.field.weather == "sunnyday"
    assert random.getstate() == before


@pytest.mark.parametrize("seed,cured", [(1, True), (2, False)])
def test_healer_uses_private_rng_and_only_living_active_ally(seed, cured):
    """An independent global RNG never controls a rollback-sensitive cure."""
    from pokemon.battle.engine import _resolve_ability

    battle, user, ally, foe, _ = doubles()
    user.ability = _resolve_ability("Healer")
    ally.status, user.status, foe.status = "par", "brn", "psn"
    battle.rng = random.Random(seed)
    before = random.getstate()
    user.ability.call("onResidual", pokemon=user, battle=battle, effect_state=user.ability_state)
    assert (not ally.status) is cured
    assert (user.status, foe.status) == ("brn", "psn")
    assert random.getstate() == before


def test_prankster_is_full_priority_and_dark_foe_immune_only_for_boosted_status():
    """Priority and the opposing Dark immunity belong to the used status copy."""
    battle, user, foe = build_battle(attacker_ability="Prankster", defender_types=["Dark"])
    move = action(battle, user, foe, "Growl")
    assert battle.apply_priority_modifiers(user, move.move, 0, foe) == 1
    battle.use_move(move)
    assert foe.boosts["attack"] == 0
    user.ability_suppressed = True
    battle.use_move(action(battle, user, foe, "Growl"))
    assert foe.boosts["attack"] == -1


@pytest.mark.parametrize(
    "control,trapped",
    [
        ("active", True),
        ("suppressed", False),
        ("ghost", False),
        ("shedshell", False),
        ("shadowtag", False),
    ],
)
def test_shadow_tag_controls_actual_switch_legality(control, trapped):
    """A normal active opponent is trapped; escape/suppression controls remain legal."""
    from pokemon.battle.legal_actions import LegalActions

    battle, holder, foe = build_battle(attacker_ability="Shadow Tag")
    holder.ability_suppressed = control == "suppressed"
    if control == "ghost":
        foe.types = ["Ghost"]
    if control == "shedshell":
        foe.item = "Shed Shell"
    if control == "shadowtag":
        foe.ability = "Shadow Tag"
    reserve = type(foe)("Reserve", level=50, hp=100, max_hp=100)
    reserve.name, reserve.battle = "Reserve", battle
    participant = battle.participant_for(foe)
    participant.pokemons.append(reserve)
    legal = LegalActions(battle, participant, foe).switches()
    assert (not legal) is trapped


@pytest.mark.parametrize(
    "move,expected",
    [
        ("Tackle", True),
        ("Growl", False),
        ("Double Hit", False),
        ("Earthquake", False),
        ("Struggle", False),
        ("Seismic Toss", True),
    ],
)
def test_parental_bond_qualifies_only_one_target_ordinary_damage(move, expected):
    """Excluded sources do not gain an extra hit; eligible hit two uses .25 damage."""
    battle, user, foe = build_battle(attacker_ability="Parental Bond")
    chosen = action(battle, user, foe, move)
    battle.use_move(chosen)
    assert (getattr(chosen.move, "multihit_type", "") == "parentalbond") is expected


@pytest.mark.parametrize("substitute", [False, True])
def test_parental_bond_contact_and_substitute_are_resolved_per_hit(substitute):
    """A broken substitute exposes HP only to hit two, and contact happens only on HP."""
    battle, user, foe = build_battle(
        attacker_ability="Parental Bond", defender_ability="Iron Barbs"
    )
    if substitute:
        foe.volatiles["substitute"] = {"hp": 1}
    old_user, old_foe = user.hp, foe.hp
    chosen = action(battle, user, foe, "Tackle")
    battle.use_move(chosen)
    assert chosen.move.total_damage > 1
    assert foe.hp < old_foe
    assert user.hp == old_user - (1 if substitute else 2) * (user.max_hp // 8)
    assert "substitute" not in foe.volatiles


def test_parental_bond_secondary_self_boost_and_protection_are_not_collapsed():
    """Power-Up Punch boosts per hit; protection stops both hits and contacts."""
    battle, user, foe = build_battle(attacker_ability="Parental Bond")
    battle.use_move(action(battle, user, foe, "Power-Up Punch"))
    assert user.boosts["attack"] == 2
    before = (user.hp, foe.hp, copy.deepcopy(user.boosts))
    foe.volatiles["protect"] = True
    battle.use_move(action(battle, user, foe, "Power-Up Punch"))
    assert (user.hp, foe.hp, user.boosts) == before


def test_parental_bond_fixed_damage_has_two_unscaled_hits():
    """Seismic Toss is eligible and retains its fixed damage on each hit."""
    battle, user, foe = build_battle(attacker_ability="Parental Bond")
    before = foe.hp
    battle.use_move(action(battle, user, foe, "Seismic Toss"))
    assert before - foe.hp == 2 * user.level


def test_parental_bond_contact_faint_stops_second_hit():
    """A first-hit contact faint cannot produce a second hit from the fainted user."""
    battle, user, foe = build_battle(
        attacker_ability="Parental Bond", defender_ability="Iron Barbs"
    )
    user.hp = user.max_hp // 8
    chosen = action(battle, user, foe, "Tackle")
    battle.use_move(chosen)
    assert user.hp == 0
    assert chosen.move.parental_bond_hit == 1


@pytest.mark.parametrize(
    "ability,yes,no",
    [
        ("Tough Claws", "Aerial Ace", "Water Gun"),
        ("Technician", "Tackle", "Body Slam"),
        ("Strong Jaw", "Bite", "Tackle"),
        ("Mega Launcher", "Water Pulse", "Water Gun"),
        ("Sheer Force", "Rock Slide", "Tackle"),
    ],
)
def test_conditional_offensive_traits_have_actual_qualifying_and_no_effect_hits(ability, yes, no):
    """Suppression controls isolate the ability rather than comparing native stats."""

    def damage(name, suppressed):
        """Execute a fresh ordinary move with identical stats and private RNG."""
        battle, user, foe = build_battle(attacker_ability=ability)
        user.ability_suppressed = suppressed
        battle.rng = random.Random(123)
        battle.use_move(action(battle, user, foe, name))
        return foe.max_hp - foe.hp

    assert damage(yes, False) > damage(yes, True) > 0
    assert damage(no, False) == damage(no, True)


@pytest.mark.parametrize(
    "ability,converted", [("Aerilate", "Flying"), ("Pixilate", "Fairy"), ("Refrigerate", "Ice")]
)
def test_conversion_applies_one_point_two_once_and_preserves_excluded_source(ability, converted):
    """Shared dex moves remain unchanged and non-Normal sources never convert."""
    from pokemon.dex import MOVEDEX

    raw_before = copy.deepcopy(MOVEDEX["tackle"].raw)
    battle, user, foe = build_battle(attacker_ability=ability, attacker_types=["Normal"])
    chosen = action(battle, user, foe, "Tackle")
    battle.use_move(chosen)
    assert chosen.move.type == converted
    assert chosen.move.power == 48
    assert MOVEDEX["tackle"].raw == raw_before
    other = action(battle, user, foe, "Water Gun")
    battle.use_move(other)
    assert other.move.type == "Water"
    assert other.move.power == 40


@pytest.mark.parametrize("side", ["user", "target"])
@pytest.mark.parametrize("protected", [False, True])
def test_no_guard_hits_in_both_directions_but_preserves_protection(side, protected):
    """Real numeric miss controls do not infer success from a callback assignment."""
    battle, user, foe = build_battle(
        attacker_ability="No Guard" if side == "user" else None,
        defender_ability="No Guard" if side == "target" else None,
    )
    if protected:
        foe.volatiles["protect"] = True
    chosen = action(battle, user, foe, "Tackle")
    chosen.move.accuracy = 0
    chosen.move.raw["accuracy"] = 0
    battle.use_move(chosen)
    assert (foe.hp < foe.max_hp) is not protected


@pytest.mark.parametrize("ability", ["No Guard", "Levitate"])
def test_suppressed_accuracy_and_ground_immunity_have_real_miss_hit_controls(ability):
    """Metadata-only and callback consumers read effective owned abilities."""
    battle, user, foe = build_battle(
        attacker_ability="No Guard" if ability == "No Guard" else None,
        defender_ability="Levitate" if ability == "Levitate" else None,
    )
    owner = user if ability == "No Guard" else foe
    owner.ability_suppressed = True
    chosen = action(battle, user, foe, "Tackle" if ability == "No Guard" else "Mud-Slap")
    if ability == "No Guard":
        chosen.move.accuracy = 0
        chosen.move.raw["accuracy"] = 0
    battle.use_move(chosen)
    assert (foe.hp < foe.max_hp) is (ability == "Levitate")


@pytest.mark.parametrize("power,boosted", [(0, False), (60, True), (61, False)])
def test_technician_current_power_boundary(power, boosted):
    """The callback receives the actual power, independent of absent move aliases."""
    from pokemon.dex.functions.abilities_funcs import Technician
    from types import SimpleNamespace

    result = Technician().onBasePower(power, move=SimpleNamespace(power=power))
    assert result == (int(power * 1.5) if boosted else power)


@pytest.mark.parametrize(
    "ability,weather,move,boost",
    [
        ("Sand Force", "sandstorm", "Metal Claw", True),
        ("Sand Force", None, "Metal Claw", False),
        ("Sand Force", "sandstorm", "Water Gun", False),
        ("Solar Power", "sunnyday", "Water Gun", True),
        ("Solar Power", None, "Water Gun", False),
    ],
)
def test_environment_power_qualifies_only_current_weather_and_move(ability, weather, move, boost):
    """Weather power is observed on real hits with the same form and source."""

    def damage(suppressed):
        """Use identical private rolls and read the actual target HP delta."""
        battle, user, foe = build_battle(attacker_ability=ability)
        user.ability_suppressed = suppressed
        if weather:
            battle.setWeather(weather, user)
        battle.rng = random.Random(123)
        battle.use_move(action(battle, user, foe, move))
        return foe.max_hp - foe.hp

    assert (damage(False) > damage(True)) is boost


def test_trace_no_candidate_waits_and_reentry_resets_temporary_copy_once():
    """Trace can seek later, while Mega reentry restores the native Mega trait."""
    from pokemon.battle.effect_context import EffectContext
    from pokemon.battle.engine import _resolve_ability

    battle, user, foe = build_battle(attacker_ability="Trace", defender_ability="Multitype")
    battle.start_owned_ability(user)
    assert EffectContext.key(user.ability) == "trace"
    foe.ability = _resolve_ability("Huge Power")
    _resolve_ability(user.ability).call("onUpdate", pokemon=user, battle=battle)
    assert EffectContext.key(user.ability) == "hugepower"
    user.species = "Alakazam-Mega"
    user.mega_profile = {"stone": "alakazite"}
    foe.ability = _resolve_ability("Drought")
    battle.on_enter_battle(user)
    assert EffectContext.key(user.ability) == "drought"
    assert battle.field.weather == "sunnyday"


def test_owned_start_internal_type_error_is_not_retried_as_missing_context():
    """An unexpected failure must escape to whole-turn rollback, exactly once."""
    from pokemon.dex.functions.abilities_funcs import Drought

    battle, user, _ = build_battle()
    user.setAbility("Drought", battle=battle, is_from_forme_change=True, run_start=False)
    calls = []

    def fail(handler, source=None, battle=None):
        """Raise after observing correct context, without an arity fallback."""
        calls.append((source, battle))
        raise TypeError("internal owned Start fixture")

    with patch.object(Drought, "onStart", fail):
        with pytest.raises(TypeError, match="internal owned Start fixture"):
            battle.start_owned_ability(user)
    assert calls == [(user, battle)]
