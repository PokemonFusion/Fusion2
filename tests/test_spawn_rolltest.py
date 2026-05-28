import random
import sys
import types

import pytest

from pokemon.spawns.adapters import SpawnAdapterError
from pokemon.spawns.rolltest import (
    MAX_ROLL_TEST_COUNT,
    format_spawn_roll_test,
    parse_rolltest_args,
    run_spawn_roll_test,
)
from pokemon.spawns.schema import SpawnChart, SpawnEntry


def test_successful_dry_run_with_small_chart():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="A", frequency="frequent", band=1),
            SpawnEntry(species_id="B", frequency="common", band=1),
        ],
    )

    result = run_spawn_roll_test(chart, band=1, count=10, rng=random.Random(4))
    text = format_spawn_roll_test(result, source="hunt_chart")

    assert result.successful_rolls == 10
    assert sum(result.species_counts.values()) == 10
    assert sum(result.frequency_counts.values()) == 10
    assert "PF2 Spawn Roll Test" in text
    assert "Area key: route-alpha" in text
    assert "Source: hunt_chart" in text
    assert "Roll count: 10" in text
    assert "Successful rolls: 10" in text
    assert "Frequency breakdown:" in text
    assert "Top species:" in text


def test_band_filter_uses_requested_band():
    chart = SpawnChart(
        area_key="route-beta",
        entries=[
            SpawnEntry(species_id="A", frequency="frequent", band=1),
            SpawnEntry(species_id="B", frequency="common", band=2),
        ],
    )

    result = run_spawn_roll_test(chart, band=2, count=5, rng=random.Random(2))

    assert result.successful_rolls == 5
    assert result.species_counts == {"B": 5}
    assert result.frequency_counts == {"common": 5}


def test_empty_chart_returns_clear_no_roll_result():
    chart = SpawnChart(area_key="empty", entries=[])

    result = run_spawn_roll_test(chart, band=1, count=20, rng=random.Random(1))
    text = format_spawn_roll_test(result, source="empty")

    assert result.successful_rolls == 0
    assert "No normal spawn entries are available for band 1." in text


def test_invalid_band_is_friendly():
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        parse_rolltest_args("5")
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        parse_rolltest_args("rare")


def test_invalid_count_is_friendly():
    with pytest.raises(ValueError, match="Count must be a positive number"):
        parse_rolltest_args("1 0")
    with pytest.raises(ValueError, match="Count must be a positive number"):
        parse_rolltest_args("1 many")


def test_count_above_max_is_clamped():
    options = parse_rolltest_args("1 999")
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="A", frequency="frequent", band=1)],
    )

    result = run_spawn_roll_test(
        chart,
        band=options.band,
        count=options.count,
        requested_count=options.requested_count,
        rng=random.Random(1),
    )
    text = format_spawn_roll_test(result, source="hunt_chart")

    assert options.count == MAX_ROLL_TEST_COUNT
    assert options.requested_count == 999
    assert "Roll count: 200 (clamped from 999)" in text


def test_special_entries_are_ignored_by_normal_roll_test():
    chart = SpawnChart(
        area_key="route-special",
        entries=[
            SpawnEntry(species_id="Legend", frequency="special", band=4),
            SpawnEntry(species_id="Common", frequency="common", band=4),
        ],
    )

    result = run_spawn_roll_test(chart, band=4, count=50, rng=random.Random(5))
    text = format_spawn_roll_test(result, source="hunt_chart")

    assert "Legend" not in result.species_counts
    assert result.species_counts == {"Common": 50}
    assert "normal roll tests ignore special" in text


def test_special_only_chart_reports_no_normal_entries():
    chart = SpawnChart(
        area_key="route-special",
        entries=[SpawnEntry(species_id="Legend", frequency="special", band=4)],
    )

    result = run_spawn_roll_test(chart, band=4, count=10, rng=random.Random(1))

    assert result.successful_rolls == 0
    assert result.error == "No normal spawn entries are available for band 4."


def test_command_handles_adapter_error_without_traceback(monkeypatch):
    cmd_spawnrolltest = import_spawnrolltest_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    def fail_adapter(room):
        raise SpawnAdapterError("bad spawn data")

    monkeypatch.setattr(cmd_spawnrolltest, "spawn_chart_from_room", fail_adapter)
    cmd = cmd_spawnrolltest.CmdSpawnRollTest()
    cmd.caller = Caller()
    cmd.args = "1 5"

    cmd.func()

    assert cmd.caller.messages == ["Spawn roll test error: bad spawn data"]


def import_spawnrolltest_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnpreview", None)
    sys.modules.pop("commands.admin.cmd_spawnrolltest", None)
    from commands.admin import cmd_spawnrolltest

    return cmd_spawnrolltest
