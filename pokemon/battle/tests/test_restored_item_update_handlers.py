"""Restored held updates must resume without replaying native entry effects."""

import pytest

from pokemon.battle.battledata import BattleData, Team, TurnData
from pokemon.battle.logic import BattleLogic
from pokemon.battle.state import BattleState

from .test_plate_theft_identity import held, pair


def live_logic(item, *, species="Mew", ability="No Ability", doubles=False):
    """Use native calculated holders and ordinary team/position checkpoints."""
    battle, holder, source = pair(item, holder=species, ability=ability)
    source.ability = "No Ability"
    holder.model_id, source.model_id = "unit:holder", "unit:source"
    if doubles:
        for index, part in enumerate(battle.participants):
            _, bench, _ = pair("", ability="No Ability")
            bench.model_id = "unit:partner" + str(index)
            bench.battle = battle
            part.pokemons.append(bench)
            part.active.append(bench)
            part.max_active = 2
    data = BattleData(Team("A", battle.participants[0].pokemons), Team("B", battle.participants[1].pokemons))
    data.turndata = TurnData(data.teams, teamslots=2 if doubles else 1)
    state = BattleState.from_battle_data(data, ai_type="PVP")
    logic = BattleLogic(battle, data, state)
    battle.start_turn()
    return logic


def restore(logic):
    """Freeze the real nonzero turn so first-entry registration cannot mask it."""
    logic.data.battle.turn = logic.battle.turn_count
    return BattleLogic.from_dict(logic.to_dict())


@pytest.mark.parametrize("item,status", (("Pecha Berry", "tox"), ("PSN Cure Berry", "tox"),
                                        ("Burnt Berry", "frz"), ("Lum Berry", "tox"),
                                        ("Miracle Berry", "tox")))
@pytest.mark.parametrize("doubles", (False, True))
def test_restored_status_update_eats_once(item, status, doubles):
    """A later normal update must reach the current active holder's actual item."""
    logic = restore(restore(live_logic(item, doubles=doubles)))
    battle = logic.battle
    holder, source = [part.active[0] for part in battle.participants]
    assert holder.battle is battle
    holder.setStatus(status, source=source, battle=battle)
    battle.start_turn()
    assert not held(holder) and not holder.status and holder.toxic_counter == 0
    consumed = holder.last_consumed_item
    battle.start_turn()
    assert holder.last_consumed_item == consumed and not held(holder)
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("doubles", (False, True))
def test_restored_oran_update_heals_once(doubles):
    """HP-triggered consumption also needs reattached update handlers."""
    logic = restore(restore(live_logic("Oran Berry", doubles=doubles)))
    holder = logic.battle.participants[0].active[0]
    holder.hp = 1
    logic.battle.start_turn()
    assert holder.hp == 11 and not held(holder)
    logic.battle.start_turn()
    assert holder.hp == 11


@pytest.mark.parametrize("species,item,ability", (("Zacian", "Rusted Sword", "Intrepid Sword"),
                                                ("Zamazenta", "Rusted Shield", "Dauntless Shield"),
                                                ("Kyogre", "Blue Orb", "Drizzle"),
                                                ("Groudon", "Red Orb", "Drought")))
def test_rebinding_never_replays_entry_boost_or_weather(species, item, ability):
    """Repeated restore/update preserves actual entry outcomes, not reactivation."""
    logic = live_logic(item, species=species, ability=ability)
    holder = logic.battle.participants[0].active[0]
    before = (str(holder.species), dict(holder.boosts), holder.hp, logic.battle.field.weather)
    for _ in range(3):
        logic = restore(logic)
        logic.battle.start_turn()
        holder = logic.battle.participants[0].active[0]
        assert (str(holder.species), dict(holder.boosts), holder.hp, logic.battle.field.weather) == before
    assert not getattr(logic.battle, "_callback_failures", [])
