"""Real item damage/healing and legacy Gene activation use battle guards."""

import random
from types import SimpleNamespace

import pytest

from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats

from .test_diagnosed_item_effects import attack, native_battle
from .test_reactive_item_consumption import name


def reaction(item, ability="Cute Charm"):
    """A native Clefable attacks a durable native Mew with actual level-50 stats."""
    battle, holder, source = native_battle("Mew", item, "Clefable", ability="Synchronize")
    data = SimpleNamespace(species="Clefable", level=50, ivs=[0] * 6, evs=[0] * 6, nature="Hardy")
    source.level = 50
    source.base_stats = type(holder.base_stats)(**get_stats(data))
    source.hp = source.max_hp = get_max_hp(data)
    source.ability = ability
    return battle, holder, source


@pytest.mark.parametrize("item,divisor", (("Black Sludge", 8), ("Sticky Barb", 8),
                                        ("Rocky Helmet", 6), ("Jaboca Berry", 8), ("Rowap Berry", 8)))
@pytest.mark.parametrize("mode", ("ordinary", "magicguard", "suppressed"))
def test_native_magic_guard_prevents_all_five_indirect_item_effects(item, divisor, mode):
    """Suppression restores damage; direct hits remain effective in all cases."""
    ability = "Cute Charm" if mode == "ordinary" else "Magic Guard"
    if item in {"Black Sludge", "Sticky Barb"}:
        battle, recipient, foe = native_battle("Clefable", item, "Mew", ability=ability)
        if mode == "suppressed":
            attack(battle, foe, recipient, "Gastro Acid")
        before = recipient.hp
        battle.residualEvent()
    else:
        battle, holder, recipient = reaction(item, ability)
        if mode == "suppressed":
            attack(battle, holder, recipient, "Gastro Acid")
        before, old_target = recipient.hp, holder.hp
        attack(battle, recipient, holder, "Water Gun" if item == "Rowap Berry" else "Tackle")
        assert holder.hp < old_target
        if "Berry" in item:
            assert name(holder.item) == (item if mode == "magicguard" else "")
            assert name(holder.last_used_item) == ("" if mode == "magicguard" else item)
            assert len(holder.side.used_items) == (0 if mode == "magicguard" else 1)
    assert before - recipient.hp == (0 if mode == "magicguard" else recipient.max_hp // divisor)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,species,ability", (("Leftovers", "Mew", "Synchronize"),
                                                 ("Black Sludge", "Muk", "Sticky Hold")))
@pytest.mark.parametrize("move", ("Heal Block", "Psychic Noise"))
def test_residual_heal_respects_real_block_and_recovers_after_expiry(item, species, ability, move):
    """A real blocking move stops reusable healing until its volatile expires."""
    battle, holder, foe = native_battle(species, item, "Mew", ability=ability)
    foe.level = 5
    holder.hp = holder.max_hp // 2
    battle.residualEvent()
    assert holder.hp == holder.max_hp // 2 + holder.max_hp // 16
    attack(battle, foe, holder, move)
    assert holder.hp > 0 and "healblock" in holder.volatiles
    before = holder.hp
    duration = 2 if move == "Psychic Noise" else 5
    assert holder.volatiles["healblock"]["duration"] == duration
    for _ in range(duration):
        battle.residualEvent()
        assert holder.hp == before
    assert "healblock" not in holder.volatiles
    battle.residualEvent()
    assert holder.hp == min(holder.max_hp, before + holder.max_hp // 16)
    assert name(holder.item) == item and not holder.last_used_item


@pytest.mark.parametrize("item,species", (("Leftovers", "Mew"), ("Black Sludge", "Muk")))
def test_residual_healing_never_revives_and_caps_at_actual_max_hp(item, species):
    """Reusable items preserve HP caps, physical holding and fainted state."""
    battle, holder, _ = native_battle(species, item)
    holder.hp -= 1
    battle.residualEvent()
    assert holder.hp == holder.max_hp
    holder.hp = 0
    battle.residualEvent()
    assert holder.hp == 0 and name(holder.item) == item


@pytest.mark.parametrize("species,ability,delta,confused", (("Mew", "Synchronize", 2, True),
                                                          ("Spinda", "Own Tempo", 2, False),
                                                          ("Shuckle", "Contrary", -2, True),
                                                          ("Bibarel", "Simple", 4, True)))
@pytest.mark.parametrize("prior", (-6, 0, 6))
def test_berserk_gene_attack_only_with_guarded_confusion_and_one_use(species, ability, delta, confused, prior):
    """PF2 combines the legacy item's Attack effect with current native abilities."""
    from pokemon.battle.battledata import Pokemon

    battle, holder, foe = native_battle(species, "Berserk Gene", ability=ability)
    holder.boosts.update(attack=prior, speed=2)
    battle.rng = random.Random(0)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.boosts["attack"] == max(-6, min(6, prior + delta))
    assert holder.boosts["speed"] == 2
    assert ("confusion" in holder.volatiles) is confused
    assert not holder.item and name(holder.last_used_item) == "Berserk Gene"
    before = dict(holder.boosts)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert holder.boosts == before and len(holder.side.used_items) == 1
    restored = Pokemon.from_dict(holder.to_dict())
    assert restored.boosts == before and name(restored.last_used_item) == "Berserk Gene"


@pytest.mark.parametrize("suppression", ("Magic Room", "Embargo"))
def test_berserk_gene_suppression_preserves_physical_copy(suppression):
    """No update grants effects or loses a suppressed copy."""
    battle, holder, foe = native_battle("Spinda", "Berserk Gene", "Mew", ability="Own Tempo")
    attack(battle, foe, holder if suppression == "Embargo" else foe, suppression)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert name(holder.item) == "Berserk Gene"
    assert not any(holder.boosts.values()) and "confusion" not in holder.volatiles


def test_own_tempo_suppression_permits_berserk_gene_confusion():
    """A genuine Gastro Acid removes the native confusion guard."""
    battle, holder, foe = native_battle("Spinda", "Berserk Gene", "Mew", ability="Own Tempo")
    attack(battle, foe, holder, "Gastro Acid")
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert "confusion" in holder.volatiles and holder.boosts["attack"] == 2
