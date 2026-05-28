"""PF2 spawn constants derived from the PF1 spawn rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SpawnFrequency(str, Enum):
    """Normal PF2 frequency buckets.

    ``special`` is configured with the other frequencies, but it is not part
    of the normal frequency roll. Later hunt integration should apply special
    cooldown and protection logic separately.
    """

    FREQUENT = "frequent"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    SPECIAL = "special"


FREQUENCIES = tuple(frequency.value for frequency in SpawnFrequency)
NORMAL_FREQUENCIES = (
    SpawnFrequency.FREQUENT.value,
    SpawnFrequency.COMMON.value,
    SpawnFrequency.UNCOMMON.value,
    SpawnFrequency.RARE.value,
)


@dataclass(frozen=True)
class SpawnBandDefinition:
    """Progression gate and wild level range for one spawn band."""

    band: int
    access_value: int
    min_level: int
    max_level: int


SPAWN_BANDS = {
    1: SpawnBandDefinition(band=1, access_value=1, min_level=5, max_level=15),
    2: SpawnBandDefinition(band=2, access_value=15, min_level=15, max_level=30),
    3: SpawnBandDefinition(band=3, access_value=30, min_level=30, max_level=45),
    4: SpawnBandDefinition(band=4, access_value=45, min_level=45, max_level=60),
}


ACTIVE_COUNTS = {
    SpawnFrequency.FREQUENT.value: 1,
    SpawnFrequency.COMMON.value: 3,
    SpawnFrequency.UNCOMMON.value: 2,
    SpawnFrequency.RARE.value: 1,
    SpawnFrequency.SPECIAL.value: 1,
}


FREQUENCY_WEIGHTS = {
    1: {
        SpawnFrequency.FREQUENT.value: 470,
        SpawnFrequency.COMMON.value: 350,
        SpawnFrequency.UNCOMMON.value: 150,
        SpawnFrequency.RARE.value: 30,
        SpawnFrequency.SPECIAL.value: 0,
    },
    2: {
        SpawnFrequency.FREQUENT.value: 410,
        SpawnFrequency.COMMON.value: 380,
        SpawnFrequency.UNCOMMON.value: 170,
        SpawnFrequency.RARE.value: 40,
        SpawnFrequency.SPECIAL.value: 0,
    },
    3: {
        SpawnFrequency.FREQUENT.value: 350,
        SpawnFrequency.COMMON.value: 410,
        SpawnFrequency.UNCOMMON.value: 190,
        SpawnFrequency.RARE.value: 50,
        SpawnFrequency.SPECIAL.value: 0,
    },
    4: {
        SpawnFrequency.FREQUENT.value: 270,
        SpawnFrequency.COMMON.value: 440,
        SpawnFrequency.UNCOMMON.value: 210,
        SpawnFrequency.RARE.value: 80,
        SpawnFrequency.SPECIAL.value: 0,
    },
}
