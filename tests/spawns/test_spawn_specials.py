import copy
import random

from pokemon.spawns.constants import SPAWN_BANDS, SpawnFrequency
from pokemon.spawns.schema import SpawnChart, SpawnEntry, SpawnRollResult
from pokemon.spawns.specials import (
    SPECIAL_BASE_DENOMINATOR,
    SPECIAL_COOLDOWN_SECONDS,
    SPECIAL_MIN_DENOMINATOR,
    SPECIAL_PITY_CAP_TICKS,
    SPECIAL_PITY_STEP,
    SPECIAL_REQUIRED_BAND,
    SpecialSpawnState,
    eligible_special_entries,
    passes_special_roll,
    roll_special_spawn,
    special_cooldown_remaining,
    special_pity_ticks,
    special_roll_denominator,
)


class FixedSpecialRng:
    def __init__(self, randrange_value=0, level=45):
        self.randrange_value = randrange_value
        self.level = level
        self.randrange_stops = []
        self.randint_bounds = []

    def randrange(self, stop):
        self.randrange_stops.append(stop)
        return self.randrange_value

    def choice(self, values):
        return list(values)[0]

    def randint(self, low, high):
        self.randint_bounds.append((low, high))
        return self.level


def special_chart(*entries):
    return SpawnChart(area_key="special-test", entries=list(entries))


def special_entry(species_id="144", enabled=True):
    return SpawnEntry(
        species_id=species_id,
        frequency=SpawnFrequency.SPECIAL.value,
        band=SPECIAL_REQUIRED_BAND,
        enabled=enabled,
    )


def ready_state(**overrides):
    values = {
        "current_time": 100000,
        "last_special_at": None,
        "current_tick": 40,
        "last_special_tick": 0,
        "ignore_special_finder": False,
    }
    values.update(overrides)
    return SpecialSpawnState(**values)


def test_special_constants_match_pf1_pity_values():
    assert SPECIAL_REQUIRED_BAND == 4
    assert SPECIAL_COOLDOWN_SECONDS == 86400
    assert SPECIAL_BASE_DENOMINATOR == 10000
    assert SPECIAL_PITY_STEP == 225
    assert SPECIAL_PITY_CAP_TICKS == 40
    assert SPECIAL_MIN_DENOMINATOR == 1000


def test_band_one_to_three_never_roll_specials():
    chart = special_chart(special_entry())
    state = ready_state()
    rng = FixedSpecialRng(randrange_value=0)

    assert [roll_special_spawn(chart, band, state, rng=rng) for band in (1, 2, 3)] == [None, None, None]
    assert rng.randrange_stops == []


def test_band_four_with_no_special_entries_returns_none():
    chart = special_chart(SpawnEntry(species_id="025", frequency="rare", band=4))

    assert roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=0)) is None


def test_eligible_special_entries_returns_enabled_band_four_specials_only():
    chart = special_chart(
        special_entry("144"),
        special_entry("145", enabled=False),
        SpawnEntry(species_id="025", frequency="rare", band=4),
    )

    assert [entry.species_id for entry in eligible_special_entries(chart, 4)] == ["144"]
    assert eligible_special_entries(chart, 3) == []


def test_band_four_with_special_entries_can_return_when_roll_passes():
    chart = special_chart(
        SpawnEntry(species_id="025", frequency="rare", band=4),
        special_entry("144"),
    )

    result = roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=0, level=55))

    assert result == SpawnRollResult(
        species_id="144",
        frequency=SpawnFrequency.SPECIAL.value,
        band=4,
        level=55,
    )


def test_special_only_chart_can_produce_special_result():
    chart = special_chart(special_entry("150"))

    result = roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=0))

    assert result.species_id == "150"
    assert result.frequency == "special"


def test_cooldown_blocks_special_roll():
    chart = special_chart(special_entry())
    state = ready_state(current_time=1000, last_special_at=900)
    rng = FixedSpecialRng(randrange_value=0)

    assert roll_special_spawn(chart, 4, state, rng=rng) is None
    assert rng.randrange_stops == []


def test_cooldown_remaining_returns_correct_seconds():
    assert special_cooldown_remaining(ready_state(last_special_at=None)) == 0
    assert special_cooldown_remaining(ready_state(current_time=4600, last_special_at=1000)) == 82800
    assert special_cooldown_remaining(ready_state(current_time=90000, last_special_at=1000)) == 0


def test_expired_cooldown_allows_roll_attempt():
    chart = special_chart(special_entry())
    state = ready_state(
        current_time=1000 + SPECIAL_COOLDOWN_SECONDS,
        last_special_at=1000,
    )
    rng = FixedSpecialRng(randrange_value=0)

    assert roll_special_spawn(chart, 4, state, rng=rng).species_id == "144"
    assert rng.randrange_stops == [SPECIAL_MIN_DENOMINATOR]


def test_ignore_special_finder_blocks_roll():
    chart = special_chart(special_entry())
    rng = FixedSpecialRng(randrange_value=0)

    assert roll_special_spawn(chart, 4, ready_state(ignore_special_finder=True), rng=rng) is None
    assert rng.randrange_stops == []


def test_pity_ticks_cap_at_forty():
    assert special_pity_ticks(ready_state(current_tick=0, last_special_tick=10)) == 0
    assert special_pity_ticks(ready_state(current_tick=15, last_special_tick=10)) == 5
    assert special_pity_ticks(ready_state(current_tick=41, last_special_tick=0)) == 40


def test_denominator_formula_matches_pf1_values():
    assert special_roll_denominator(ready_state(current_tick=0, last_special_tick=0)) == 10000
    assert special_roll_denominator(ready_state(current_tick=1, last_special_tick=0)) == 9775
    assert special_roll_denominator(ready_state(current_tick=40, last_special_tick=0)) == 1000
    assert special_roll_denominator(ready_state(current_tick=41, last_special_tick=0)) == 1000


def test_seeded_rng_gives_deterministic_pass_fail_behavior():
    state = ready_state(current_tick=40, last_special_tick=0)
    first_rng = random.Random(7)
    second_rng = random.Random(7)

    assert [passes_special_roll(state, first_rng) for _ in range(20)] == [
        passes_special_roll(state, second_rng) for _ in range(20)
    ]


def test_result_frequency_is_special_and_level_is_within_band_four_range():
    chart = special_chart(special_entry())
    result = roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=0, level=60))
    band_definition = SPAWN_BANDS[4]

    assert result.frequency == SpawnFrequency.SPECIAL.value
    assert band_definition.min_level <= result.level <= band_definition.max_level


def test_alternate_form_species_strings_are_preserved():
    chart = special_chart(special_entry("487+"))

    result = roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=0))

    assert result.species_id == "487+"


def test_failed_pity_roll_returns_none():
    chart = special_chart(special_entry())

    assert roll_special_spawn(chart, 4, ready_state(), rng=FixedSpecialRng(randrange_value=1)) is None


def test_roll_special_spawn_does_not_mutate_state():
    chart = special_chart(special_entry())
    state = ready_state()
    original = copy.deepcopy(state)

    roll_special_spawn(chart, 4, state, rng=FixedSpecialRng(randrange_value=0))

    assert state == original
