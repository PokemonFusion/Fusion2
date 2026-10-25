"""Synchronize must reflect only useful legitimate status once, including cures."""

from types import SimpleNamespace

import pytest

from .test_diagnosed_item_effects import attack
from .test_plate_theft_identity import held, pair


@pytest.mark.parametrize("status", ("psn", "tox", "brn", "par"))
def test_legitimate_status_reflects_once_to_healthy_source(status):
    """The ordinary setter/event pipeline retains the correct source roles."""
    battle, holder, source = pair("", ability="Synchronize")
    source.ability = "No Ability"  # Explicit offline ability isolation.
    assert holder.setStatus(status, source=source, battle=battle, effect="test:status")
    assert holder.status == source.status == status
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("status", ("slp", "frz"))
def test_freeze_and_sleep_never_reflect(status):
    """An otherwise healthy source must not inherit excluded major conditions."""
    battle, holder, source = pair("", ability="Synchronize")
    source.ability = "No Ability"
    assert holder.setStatus(status, source=source, battle=battle, effect="test:status")
    assert holder.status == status and not source.status
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("item", ("", "Lum Berry", "Miracle Berry", "Pecha Berry", "PSN Cure Berry"))
def test_two_synchronize_holders_cannot_reapply_poison_recursively(item, monkeypatch):
    """A diagnostic fuse bounds a regression without forcing a successful effect."""
    battle, holder, source = pair(item, ability="Synchronize")
    calls = []
    for mon in (holder, source):
        original = mon.setStatus

        def observe(status, *, _original=original, **kwargs):
            """Stop runaway recursion early so failed receipts remain reviewable."""
            calls.append(status)
            if len(calls) > 6:
                raise RuntimeError("Synchronize reflected repeatedly; bounded diagnostic fuse")
            return _original(status, **kwargs)

        monkeypatch.setattr(mon, "setStatus", observe)
    damage, _ = attack(battle, source, holder, "Toxic")
    assert damage == 0 and source.status == "tox"
    # Pecha/PSN Toxic eating is separately repaired in #858.
    if item in {"Lum Berry", "Miracle Berry"}:
        assert not holder.status and not held(holder)
    assert len([s for s in calls if s == "tox"]) == 2
    assert not getattr(battle, "_callback_failures", [])


@pytest.mark.parametrize("status", ("psn", "tox", "brn", "par", "slp", "frz"))
def test_already_statused_source_is_not_rewritten(status):
    """Use trySetStatus: same-status reflection cannot reset Toxic or sleep data."""
    battle, holder, source = pair("", ability="Synchronize")
    source.ability = "No Ability"
    source.setStatus(status, battle=battle)
    if status == "tox":
        source.toxic_counter = 4  # Labelled residual-state prerequisite.
    if status == "slp":
        source.tempvals.update(sleep_turns=2, slp_turns=2)
    before = source.to_dict()
    holder.setStatus("tox", source=source, battle=battle, effect="test:status")
    assert source.to_dict() == before


@pytest.mark.parametrize("effect", ("ability:synchronize", "synchronize", "move:toxicspikes",
                                  SimpleNamespace(id="toxicspikes")))
def test_reflected_and_toxic_spikes_effects_do_not_start_another_reflection(effect):
    """Keep the primary hazard exception and PF2's explicit reflected-effect guard."""
    battle, holder, source = pair("", ability="Synchronize")
    source.ability = "No Ability"
    holder.setStatus("tox", source=source, battle=battle, effect=effect)
    assert holder.status == "tox" and not source.status


@pytest.mark.parametrize("source_kind", ("missing", "self", "ally", "opponent", "suppressed"))
def test_source_and_suppression_policy_has_no_invented_opponent_only_gate(source_kind):
    """Allied sources are allowed; missing/self and inactive ability cannot reflect."""
    battle, holder, source = pair("", ability="Synchronize")
    source.ability = "No Ability"
    if source_kind == "ally":
        battle.participants[1].team = battle.participants[0].team = "A"
    if source_kind == "suppressed":
        holder.ability_suppressed = True
    actor = None if source_kind == "missing" else holder if source_kind == "self" else source
    holder.setStatus("brn", source=actor, battle=battle, effect="test:status")
    assert bool(source.status) is (source_kind in {"ally", "opponent"})


@pytest.mark.parametrize("species,status,ability", (("Metagross", "tox", "Clear Body"),
                                                   ("Charizard", "brn", "Blaze"),
                                                   ("Electivire", "par", "Motor Drive")))
def test_reflection_retains_source_status_immunity(species, status, ability):
    """A reflected status remains subject to the actual native source's defenses."""
    battle, holder, source = pair("", source=species, ability="Synchronize")
    source.ability = ability
    holder.setStatus(status, source=source, battle=battle, effect="test:status")
    assert holder.status == status and not source.status
