import importlib
import random
import sys
import types

import pytest

from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profile_rolltest import (
    parse_profile_rolltest_args,
    run_profile_spawn_roll_test,
)
from pokemon.spawns.rolltest import MAX_ROLL_TEST_COUNT, format_spawn_roll_test
from pokemon.spawns.schema import SpawnChart, SpawnEntry


def test_rolls_sample_area_successfully():
    result = run_profile_spawn_roll_test("route_1", band=1, count=10, rng=random.Random(1))

    assert result.area_key == "route_1"
    assert result.band == 1
    assert result.successful_rolls == 10
    assert sum(result.species_counts.values()) == 10


def test_band_filtering_uses_requested_band():
    result = run_profile_spawn_roll_test("route_1", band=3, count=12, rng=random.Random(2))

    assert result.band == 3
    assert result.successful_rolls == 12
    assert set(result.species_counts).issubset({"020", "017", "025"})


def test_count_aggregation():
    result = run_profile_spawn_roll_test("forest_test", band=1, count=17, rng=random.Random(3))

    assert sum(result.frequency_counts.values()) == 17
    assert sum(result.species_counts.values()) == 17


def test_count_clamp():
    options = parse_profile_rolltest_args("route_1 1 999")

    assert options.count == MAX_ROLL_TEST_COUNT
    assert options.requested_count == 999


def test_unknown_area_key_handled():
    with pytest.raises(SpawnProfileDataError, match="Unknown area profile"):
        run_profile_spawn_roll_test("missing_area", band=1, count=1)


def test_special_only_area_does_not_produce_normal_rolls():
    result = run_profile_spawn_roll_test("special_test", band=4, count=20, rng=random.Random(4))
    text = format_spawn_roll_test(result, source="profile sample data")

    assert result.successful_rolls == 0
    assert "No normal spawn entries are available for band 4." in text


def test_special_entries_ignored_by_normal_profile_roll_test():
    chart = SpawnChart(
        area_key="mixed_special",
        entries=[
            SpawnEntry(species_id="144", frequency="special", band=4),
            SpawnEntry(species_id="025", frequency="common", band=4),
        ],
    )

    result = run_profile_spawn_roll_test(
        "mixed_special",
        band=4,
        count=20,
        rng=random.Random(5),
        chart_resolver=lambda area_key: chart,
    )

    assert result.species_counts == {"025": 20}


def test_seeded_rng_produces_deterministic_helper_output():
    first = run_profile_spawn_roll_test("route_1", band=1, count=20, rng=random.Random(8))
    second = run_profile_spawn_roll_test("route_1", band=1, count=20, rng=random.Random(8))

    assert first.frequency_counts == second.frequency_counts
    assert first.species_counts == second.species_counts


def test_invalid_band_and_count_are_friendly():
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        parse_profile_rolltest_args("route_1 5")
    with pytest.raises(ValueError, match="Count must be a positive number"):
        parse_profile_rolltest_args("route_1 1 zero")


def test_profile_roll_command_unknown_area_has_friendly_error(monkeypatch):
    cmd_mod = import_spawnprofilerolltest_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnProfileRollTest()
    cmd.caller = Caller()
    cmd.args = "missing_area 1 2"

    cmd.func()

    assert cmd.caller.messages == ["Spawn profile roll test error: Unknown area profile: 'missing_area'."]


def import_spawnprofilerolltest_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnprofilerolltest", None)
    return importlib.import_module("commands.admin.cmd_spawnprofilerolltest")
