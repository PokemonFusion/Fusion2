"""Exact seed registry, saved identity and current-cycle boundary checks."""

from datetime import timedelta

import pytest

from pokemon.services.berry_growing import BerryGrowing, BerryGrowingError
from tests.test_berry_growing import crop


@pytest.mark.parametrize(
    "name", ["Oran Berry", "Cheri Berry", "Pecha Berry", "Rawst Berry", "Aspear Berry",
             "Chesto Berry", "Sitrus Berry", "Lum Berry"]
)
@pytest.mark.parametrize(
    "seconds,stage",
    [
        (0, 0),
        (3599, 0),
        (3600, 1),
        (7199, 1),
        (7200, 2),
        (10799, 2),
        (10800, 3),
        (14399, 3),
        (14400, 4),
    ],
)
def test_every_seed_keeps_exact_identity_and_real_elapsed_stage(name, seconds, stage):
    """Adding seeds cannot change elapsed time, yield or the legacy Oran cycle."""
    bed = crop()
    bed.berry = name
    state = BerryGrowing(None, clock=lambda: bed.planted_at + timedelta(seconds=seconds)).state(bed)
    assert state["berry"] == name and state["stage"] == stage
    assert state["ready"] == (stage == 4) and state["yield"] == 1
    assert BerryGrowing.canonical_seed(name.lower()) == name


@pytest.mark.parametrize(
    "name",
    [
        None,
        True,
        3,
        "",
        "Cheri",
        "Cherry Berry",
        "Cheri Berry 2",
        "Razz Berry",
        "Bluk Berry",
        "Persim Berry",
        "Leppa Berry",
        "Bicycle",
    ],
)
def test_only_exact_reviewed_seed_families_are_enabled(name):
    """Existing snacks, held cures and unreviewed berries do not become seeds."""
    with pytest.raises(BerryGrowingError):
        BerryGrowing.canonical_seed(name)


def test_saved_noncanonical_seed_is_not_silently_repaired():
    """Only authoring input is normalized; corrupted saved crop identity rejects."""
    bed = crop()
    bed.berry = "cheriberry"
    with pytest.raises(BerryGrowingError):
        BerryGrowing(None, clock=lambda: bed.planted_at).state(bed)
