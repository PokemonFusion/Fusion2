"""Fresh native Damp reproductions through actual damage/prevention events."""

from types import SimpleNamespace

import pytest

from pokemon.battle.effect_context import EffectContext
from pokemon.dex.functions.abilities_funcs import Damp

from .test_diagnosed_item_effects import attack, native_battle


def test_native_damp_allows_sandstorm_without_callback_failures():
    """Ground immunity protects Wooper; unrelated opponents still take weather chip."""
    battle, wooper, foe = native_battle("Wooper", foe="Mew", ability="Damp")
    battle.setWeather("Sandstorm", source=foe)
    before = (wooper.hp, foe.hp)
    battle.residual()
    assert (wooper.hp, foe.hp) == (before[0], before[1] - foe.max_hp // 16)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("identity", ["Aftermath", "Explosion", "Mind Blown", "Misty Explosion", "Self-Destruct"])
@pytest.mark.parametrize("representation", ["string", "id", "name"])
def test_damp_blocks_only_the_named_prevented_sources(identity, representation):
    """Dex entities and ordinary string effects have the same prevention identity."""
    effect = identity if representation == "string" else SimpleNamespace(**{representation: identity})
    assert Damp().onAnyDamage(12, effect=effect) == 0
    if EffectContext.key(effect) != "aftermath":
        assert Damp().onAnyTryMove(move=effect) is False


@pytest.mark.parametrize("effect", [None, "brn", "psn", "recoil", SimpleNamespace(name="Sandstorm"), object()])
def test_damp_preserves_unrelated_damage(effect):
    """Unknown effects remain diagnosable by their own consumers and do not explode."""
    assert Damp().onAnyDamage(12, effect=effect) == 12
    assert Damp().onAnyTryMove(move=effect) is None


@pytest.mark.parametrize("move", ["Explosion", "Self-Destruct", "Mind Blown", "Misty Explosion"])
def test_native_damp_prevents_explosive_moves_without_fainting_the_user(move):
    """Actual move prevention leaves both combatants alive and undamaged."""
    battle, wooper, foe = native_battle("Wooper", foe="Mew", ability="Damp")
    before = (wooper.hp, foe.hp)
    attack(battle, foe, wooper, move)
    assert (wooper.hp, foe.hp) == before
    assert not getattr(battle, "_callback_failures", [])


def test_native_damp_allows_contact_damage_status_and_recoil():
    """Damp is not an immunity to ordinary attacks or their indirect costs."""
    battle, foe, wooper = native_battle("Mew", foe="Wooper")
    wooper.ability = "Damp"
    assert attack(battle, foe, wooper, "Tackle")[0] > 0
    before = foe.hp
    attack(battle, foe, wooper, "Double-Edge")
    assert foe.hp < before
    battle.apply_status_condition(foe, "brn", source=wooper, effect="move:willowisp")
    before = foe.hp
    battle.residual()
    assert foe.hp < before
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("ability,prevented", [("Damp", True), ("Water Absorb", False)])
def test_native_aftermath_ko_uses_damage_prevention(ability, prevented):
    """The same contact KO pays Aftermath only without an active Damp holder."""
    battle, quagsire, drifloon = native_battle("Quagsire", foe="Drifloon", ability=ability)
    drifloon.ability = "Aftermath"
    drifloon.hp = 1  # Explicit depleted-HP precondition, not a forced attack result.
    before = quagsire.hp
    attack(battle, quagsire, drifloon, "Waterfall")
    assert drifloon.hp == 0
    assert quagsire.hp == before - (0 if prevented else quagsire.max_hp // 4)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("suppressed", [True, False])
def test_explosion_without_effective_damp_still_sacrifices_and_damages(suppressed):
    """The pre-execution repair does not remove ordinary Explosion's sacrifice cost."""
    battle, wooper, foe = native_battle("Wooper", foe="Mew", ability="Damp" if suppressed else "Water Absorb")
    wooper.ability_suppressed = suppressed
    before = wooper.hp
    attack(battle, foe, wooper, "Explosion")
    assert wooper.hp < before
    assert foe.hp == 0
    assert not getattr(battle, "_callback_failures", [])
