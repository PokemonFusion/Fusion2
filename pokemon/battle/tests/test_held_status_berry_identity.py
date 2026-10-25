"""Held poison and thawing berries through real status, update and eating paths."""

import pytest

from pokemon.battle.tests.test_diagnosed_item_effects import attack, native_battle
from pokemon.battle.tests.test_plate_theft_identity import held


@pytest.mark.parametrize("item", ("Pecha Berry", "PSN Cure Berry"))
@pytest.mark.parametrize("move", ("Toxic", "Poison Powder"))
def test_poison_berry_cures_actual_poison_moves(item, move):
    """Both poison states cure immediately, consume once and clear Toxic state."""
    battle, holder, source = native_battle(item=item)
    attack(battle, source, holder, move)
    assert not holder.status
    assert holder.toxic_counter == 0
    assert not held(holder)
    before = holder.hp
    battle.residualEvent()
    assert holder.hp == before
    attack(battle, source, holder, "Toxic")
    assert holder.status == "tox" and not held(holder)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item", ("Burnt Berry", "Aspear Berry"))
def test_thawing_berries_cannot_cure_burn_or_consume(item):
    """A useful burn remains a burn; thawing berries remain physically held."""
    battle, holder, source = native_battle(item=item)
    attack(battle, source, holder, "Will-O-Wisp")
    assert holder.status == "brn" and held(holder)
    before = holder.hp
    battle.residualEvent()
    assert holder.hp < before and held(holder)


@pytest.mark.parametrize("item", ("Pecha Berry", "PSN Cure Berry", "Burnt Berry"))
@pytest.mark.parametrize("status", ("", "brn", "par", "slp", "psn", "tox", "frz"))
def test_exact_useful_status_and_one_shot_consumption(item, status):
    """Named status prerequisites isolate the ordinary update/eating path."""
    battle, holder, source = native_battle(item=item)
    if status:
        holder.setStatus(status, battle=battle, source=source)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    useful = status == "frz" if item == "Burnt Berry" else status in {"psn", "tox"}
    assert bool(held(holder)) is not useful
    assert (holder.status or "") == ("" if useful else status)
    if useful:
        assert holder.toxic_counter == 0
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert bool(held(holder)) is not useful
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item,status", (("Pecha Berry", "tox"), ("PSN Cure Berry", "tox"), ("Burnt Berry", "frz")))
@pytest.mark.parametrize("prevention", ("magicroom", "embargo", "klutz", "unnerve"))
def test_suppression_and_unnerve_delay_useful_eating(item, status, prevention):
    """Physical ownership survives prevention, then useful eating happens once."""
    battle, holder, source = native_battle(item=item)
    if prevention == "magicroom":
        battle.add_pseudo_weather("magicroom", source=source)
    elif prevention == "embargo":
        battle.apply_volatile_status(holder, "embargo", source=source)
    elif prevention == "klutz":
        holder.ability = "Klutz"  # Offline effect adapter.
    else:
        source.ability = "Unnerve"  # Offline effect adapter.
    holder.setStatus(status, battle=battle, source=source)
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert held(holder) and holder.status == status
    if prevention == "magicroom":
        battle.remove_pseudo_weather("magicroom")
    elif prevention == "embargo":
        battle.remove_volatile(holder, "embargo")
    elif prevention == "klutz":
        holder.ability = "No Ability"
    else:
        source.ability = "No Ability"
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert not held(holder) and not holder.status and holder.toxic_counter == 0
    assert not getattr(battle, "_callback_failures", [])
