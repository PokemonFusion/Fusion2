"""Pure UTC/corruption guards; durable writes and commands use PostgreSQL tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pokemon.services.berry_growing import BerryGrowing, BerryGrowingError


def crop():
    """Describe one valid saved crop without inventing an inventory backend."""
    planted = datetime(2026, 10, 22, tzinfo=timezone.utc)
    return SimpleNamespace(cycle_id=uuid4(), berry="Oran Berry", planted_at=planted,
                           ready_at=planted + timedelta(hours=4), watered_mask=0)


@pytest.mark.parametrize("seconds,stage", [(0, 0), (3599, 0), (3600, 1), (14399, 3), (14400, 4), (864000, 4)])
def test_stage_comes_from_exact_UTC_elapsed_time(seconds, stage):
    """Offline time reaches readiness without decay, refill or process timers."""
    bed = crop()
    service = BerryGrowing(None, clock=lambda: bed.planted_at + timedelta(seconds=seconds))
    state = service.state(bed)
    assert (state["stage"], state["ready"], state["yield"]) == (stage, stage == 4, 1)


@pytest.mark.parametrize("changes", [
    {"berry": "Razz Berry"}, {"watered_mask": 16}, {"watered_mask": -1},
    {"ready_at": datetime(2026, 10, 22, tzinfo=timezone.utc)},
])
def test_corrupt_saved_crop_fails_closed(changes):
    """Metadata corruption cannot turn a crop into early/free harvest stock."""
    bed = crop()
    for key, value in changes.items():
        setattr(bed, key, value)
    with pytest.raises(BerryGrowingError):
        BerryGrowing(None, clock=lambda: datetime(2026, 10, 23, tzinfo=timezone.utc)).state(bed)


@pytest.mark.parametrize("clock", [datetime(1969, 12, 31, tzinfo=timezone.utc), datetime(2026, 10, 22)])
def test_invalid_server_clock_is_rejected_even_for_empty_bed(clock):
    """Negative and naive server timestamps are never accepted as growing input."""
    with pytest.raises(BerryGrowingError):
        BerryGrowing(None, clock=lambda: clock).state(None)


def test_clock_before_planted_time_cannot_advance_or_rewind_crop():
    """Future-corrupt persisted times need staff review instead of extrapolation."""
    bed = crop()
    with pytest.raises(BerryGrowingError):
        BerryGrowing(None, clock=lambda: bed.planted_at - timedelta(seconds=1)).state(bed)
