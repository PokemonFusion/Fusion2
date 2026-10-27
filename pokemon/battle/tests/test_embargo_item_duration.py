"""Embargo's real move must resume held effects after five residual turns."""

import pytest

from .test_diagnosed_item_effects import attack
from .test_restored_item_update_handlers import live_logic, restore
from .test_plate_theft_identity import held


@pytest.mark.parametrize("reconnect", (False, True))
@pytest.mark.parametrize("item", ("Pecha Berry", "PSN Cure Berry", "Oran Berry"))
def test_embargo_expires_and_restores_useful_item(item, reconnect):
    """Count the application turn, preserve remaining time and consume once."""
    logic = live_logic(item)
    battle = logic.battle
    holder, source = [part.active[0] for part in battle.participants]
    attack(battle, source, holder, "Embargo")
    assert holder.volatiles["embargo"]["duration"] == 5
    if item == "Oran Berry":
        holder.hp = holder.max_hp // 2
    else:
        holder.setStatus("psn", source=source, battle=battle)
    for remaining in (4, 3, 2, 1, 0):
        battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
        assert held(holder)
        battle.residualEvent()
        if remaining:
            assert holder.volatiles["embargo"]["duration"] == remaining
        else:
            assert "embargo" not in holder.volatiles
        if reconnect and remaining:
            logic = restore(logic)
            battle = logic.battle
            holder, source = [part.active[0] for part in battle.participants]
            assert holder.volatiles["embargo"]["duration"] == remaining
    before = holder.hp
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert not held(holder)
    if item == "Oran Berry":
        assert holder.hp == before + 10
    else:
        assert not holder.status
    battle.dispatcher.dispatch("update", pokemon=holder, battle=battle)
    assert not held(holder)
    assert not getattr(battle, "_callback_failures", [])


def test_reapplying_embargo_does_not_reset_remaining_duration():
    """An already active volatile keeps its original expiry boundary."""
    logic = live_logic("Pecha Berry")
    battle = logic.battle
    holder, source = [part.active[0] for part in battle.participants]
    attack(battle, source, holder, "Embargo")
    battle.residualEvent()
    assert holder.volatiles["embargo"]["duration"] == 4
    attack(battle, source, holder, "Embargo")
    assert holder.volatiles["embargo"]["duration"] == 4


@pytest.mark.parametrize("reconnect", (False, True))
def test_direct_condition_api_never_suppresses_the_source(reconnect):
    """Canonical target/source/effect calls and legacy move calls target alike."""
    logic = live_logic("Pecha Berry")
    battle = logic.battle
    holder, source = [part.active[0] for part in battle.participants]
    assert battle.apply_volatile_status(holder, "embargo", source=source)
    assert "embargo" not in source.volatiles
    assert holder.volatiles["embargo"]["duration"] == 5
    if reconnect:
        logic = restore(logic)
        battle = logic.battle
        holder, source = [part.active[0] for part in battle.participants]
    for _ in range(5):
        battle.residualEvent()
    assert "embargo" not in holder.volatiles
    assert "embargo" not in source.volatiles
