"""Stable name labels for doubles and Multi without mutating battle state."""

from types import SimpleNamespace as NS

from pokemon.battle.labels import BattlerLabels


def participant(*, team="A", capacity=2, position=None):
    """Create distinct battlers whose display names and values are identical."""
    active = [NS(name="Echo", species="Eevee") for _ in range(capacity)]
    return NS(team=team, max_active=capacity, field_position=position,
              active=active, _active_slots=dict(enumerate(active)))


def test_identical_names_use_identity_and_do_not_change_pokemon():
    """Value equality must never make A2 look like A1 or change a nickname."""
    left, right = participant(), participant(team="B")
    labels = BattlerLabels(NS(participants=[left, right]))
    before = [dict(mon.__dict__) for part in (left, right) for mon in part.active]
    assert [labels.name(mon) for part in (left, right) for mon in part.active] == [
        "Echo (A1)", "Echo (A2)", "Echo (B1)", "Echo (B2)"]
    assert [mon.__dict__ for part in (left, right) for mon in part.active] == before
    assert labels.name(NS(name="Echo")) == "Echo"  # A reserve has no field slot.


def test_sparse_slots_remain_stable_after_fainting_and_replacement():
    """A sole survivor remains A2; its same-named replacement occupies A1."""
    left, right = participant(), participant(team="B")
    labels = BattlerLabels(NS(participants=[left, right]))
    retired, survivor = left.active
    left.active[:] = [survivor]
    right.active.clear()
    assert labels.name(survivor) == "Echo (A2)"
    assert labels.name(retired) == "Echo"
    replacement = NS(name="Echo")
    left.active.insert(0, replacement)
    assert labels.name(replacement) == "Echo (A1)"
    assert labels.name(survivor) == "Echo (A2)"
    assert left._active_slots == {0: retired, 1: survivor}  # Display is read-only.


def test_multi_uses_controller_position_including_reassigned_positions():
    """Each Multi controller owns one active, but A2/B2 are physical slot two."""
    parts = [participant(team=slot[0], capacity=1, position=slot)
             for slot in ("A1", "A2", "B1", "B2")]
    labels = BattlerLabels(NS(participants=parts))
    assert [labels.name(part.active[0]) for part in parts] == [
        f"Echo ({slot})" for slot in ("A1", "A2", "B1", "B2")]
    parts[0].field_position, parts[1].field_position = "A2", "A1"
    assert labels.name(parts[0].active[0]) == "Echo (A2)"


def test_singles_with_reserves_keep_existing_names():
    """Larger rosters alone must not turn a singles battle into labelled doubles."""
    left, right = participant(capacity=1), participant(team="B", capacity=1)
    left.pokemons = left.active + [NS(name="Echo") for _ in range(5)]
    labels = BattlerLabels(NS(participants=[left, right]))
    assert labels.name(left.active[0]) == "Echo"
    assert labels.name(right.active[0]) == "Echo"
    assert BattlerLabels(None).name(left.active[0]) == "Echo"


def test_display_composites_and_uncached_positions_are_read_only():
    """Keep a Fusion/nickname composite intact and derive missing caches safely."""
    left, right = participant(), participant(team="B")
    del left._active_slots
    labels = BattlerLabels(NS(participants=[left, right]))
    assert labels.name(left.active[1], "Alex (Eevee)") == "Alex (Eevee) (A2)"
    assert not hasattr(left, "_active_slots")
