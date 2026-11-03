"""Manual medicine checks the recipient's Embargo without held suppression."""

from types import SimpleNamespace

import pytest

from pokemon.services.battle_items import BattleMedicineUse


@pytest.mark.parametrize("item", ("Potion", "Antidote", "Ether", "Max Ether", "Elixir", "Max Elixir",
                                 "Fresh Water", "Oran Berry", "Lum Berry", "Leppa Berry", "Max Honey"))
def test_active_embargo_refuses_before_any_medicine_debit(item):
    """Every medicine family shares the same target policy at execution."""
    pokemon = SimpleNamespace(volatiles={"embargo": {"duration": 5}}, hp=10, max_hp=100)
    battle = SimpleNamespace(participants=[SimpleNamespace(active=[pokemon])])
    debits = []
    assert not BattleMedicineUse(pokemon, battle=battle).use(item, lambda: debits.append(item))
    assert debits == [] and pokemon.hp == 10


@pytest.mark.parametrize("mode", ("reserve", "otheractor", "magicroom", "klutz", "field"))
def test_medicine_target_policy_preserves_other_routes(mode):
    """Only the actual active recipient's Embargo restricts this bag route."""
    target = SimpleNamespace(volatiles={}, ability="Klutz" if mode == "klutz" else "Synchronize")
    actor = SimpleNamespace(volatiles={"embargo": {"duration": 5}})
    active = [actor] if mode == "reserve" else [actor, target]
    battle = SimpleNamespace(participants=[SimpleNamespace(active=active)],
                             field=SimpleNamespace(pseudo_weather={"magicroom": {"duration": 5}}))
    if mode in {"reserve", "field"}:
        target.volatiles["embargo"] = {"duration": 5}
    assert not BattleMedicineUse.target_blocked(target, None if mode == "field" else battle)
