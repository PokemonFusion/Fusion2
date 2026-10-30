import sys
import types

import pytest

from pokemon.spawns.adapters import SpawnAdapterError
from pokemon.spawns.compare import (
    ComparableSpawnEntry,
    SpawnCompareError,
    compare_room_spawns,
    compare_spawn_entries,
    format_spawn_comparison,
    live_spawn_entries_from_room,
)


class DummyDB(types.SimpleNamespace):
    pass


class DummyRoom:
    def __init__(self, **kwargs):
        self.key = kwargs.pop("key", "Route 1")
        self.id = kwargs.pop("id", 1001)
        self.db = DummyDB(**kwargs)


def test_identical_old_and_new_entries():
    entry = ComparableSpawnEntry("A", "common", ("B1",))

    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="hunt_chart",
        live_entries=[entry],
        new_entries=[entry],
    )
    text = format_spawn_comparison(comparison)

    assert comparison.species_in_both == ("A",)
    assert comparison.species_only_live == ()
    assert comparison.species_only_new == ()
    assert comparison.frequency_differences == ()
    assert comparison.band_differences == ()
    assert "Species in both: A" in text
    assert "Frequency differences: none" in text
    assert "Band/tier differences: none" in text


def test_species_only_in_old_and_new_are_reported():
    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="spawn_table",
        live_entries=[ComparableSpawnEntry("Old", "common", ("B1",))],
        new_entries=[ComparableSpawnEntry("New", "common", ("B1",))],
    )

    assert comparison.species_only_live == ("Old",)
    assert comparison.species_only_new == ("New",)


def test_frequency_mismatch_is_reported():
    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="hunt_chart",
        live_entries=[ComparableSpawnEntry("A", "common", ("B1",))],
        new_entries=[ComparableSpawnEntry("A", "frequent", ("B1",))],
    )
    text = format_spawn_comparison(comparison)

    assert len(comparison.frequency_differences) == 1
    assert "A: live common; new frequent" in text


def test_band_mismatch_is_reported():
    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="spawn_table",
        live_entries=[ComparableSpawnEntry("A", "common", ("B1",))],
        new_entries=[ComparableSpawnEntry("A", "common", ("B2",))],
    )
    text = format_spawn_comparison(comparison)

    assert len(comparison.band_differences) == 1
    assert "A: live B1; new B2" in text


def test_empty_old_and_new_data():
    comparison = compare_spawn_entries(
        area_key="empty",
        source="empty",
        live_entries=[],
        new_entries=[],
    )
    text = format_spawn_comparison(comparison)

    assert comparison.live_entry_count == 0
    assert comparison.new_entry_count == 0
    assert "No live or new spawn entries were found." in text


def test_band_filter_limits_comparison():
    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="spawn_table",
        live_entries=[
            ComparableSpawnEntry("A", "common", ("B1",)),
            ComparableSpawnEntry("B", "rare", ("B2",)),
        ],
        new_entries=[
            ComparableSpawnEntry("A", "common", ("B1",)),
            ComparableSpawnEntry("B", "rare", ("B2",)),
            ComparableSpawnEntry("C", "common", ("B3",)),
        ],
        band=2,
    )

    assert comparison.band == 2
    assert comparison.live_entry_count == 1
    assert comparison.new_entry_count == 1
    assert comparison.species_in_both == ("B",)


def test_large_lists_are_truncated():
    live_entries = [ComparableSpawnEntry(f"{index:03d}", "common", ("B1",)) for index in range(1, 16)]

    comparison = compare_spawn_entries(
        area_key="route-alpha",
        source="hunt_chart",
        live_entries=live_entries,
        new_entries=[],
    )
    text = format_spawn_comparison(comparison, limit=3)

    assert "Only live: 001, 002, 003, ... (+12 more)" in text


def test_special_entries_are_visible_as_configured():
    comparison = compare_spawn_entries(
        area_key="route-special",
        source="hunt_chart",
        live_entries=[],
        new_entries=[ComparableSpawnEntry("Legend", "special", ("B4",))],
    )
    text = format_spawn_comparison(comparison)

    assert comparison.special_species == ("Legend",)
    assert "Special configured: Legend" in text
    assert "normal roll tests ignore special" in text


def test_live_interpretation_reproduces_current_room_rules():
    room = DummyRoom(
        hunt_chart=[
            {"name": "A", "frequency": "frequent", "tiers": ["T2"]},
            {"species": "B", "rarity": "rare"},
            {"weight": 5},
        ],
        spawn_table=[{"species": "Ignored", "rarity": "common", "tiers": ["T1"]}],
    )

    entries = live_spawn_entries_from_room(room)

    assert entries == [
        ComparableSpawnEntry("A", "common", ("B2",)),
        ComparableSpawnEntry("B", "rare", ("B1",)),
    ]


def test_compare_room_spawns_uses_adapter_and_live_interpretation():
    room = DummyRoom(
        spawn_area_key="route-live",
        hunt_chart=[{"name": "A", "frequency": "frequent", "tiers": ["T2"]}],
    )

    comparison = compare_room_spawns(room)

    assert comparison.area_key == "route-live"
    assert comparison.source == "hunt_chart"
    assert comparison.species_in_both == ("A",)
    assert comparison.frequency_differences[0].live == ("common",)
    assert comparison.frequency_differences[0].new == ("frequent",)


def test_compare_room_spawns_handles_stringified_hunt_chart():
    room = DummyRoom(
        hunt_chart='[{"name": "Rattata", "weight": 30, "min_level": 3, "max_level": 5}]',
    )

    comparison = compare_room_spawns(room)

    assert comparison.live_entry_count == 1
    assert comparison.new_entry_count == 1
    assert comparison.species_in_both == ("Rattata",)


def test_live_helper_rejects_malformed_live_data():
    room = DummyRoom(hunt_chart="bad")

    with pytest.raises(SpawnCompareError, match="string must contain"):
        live_spawn_entries_from_room(room)


def test_command_handles_adapter_error_without_traceback(monkeypatch):
    cmd_spawncompare = import_spawncompare_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    def fail_compare(room, band=None):
        raise SpawnAdapterError("bad adapter data")

    monkeypatch.setattr(cmd_spawncompare, "compare_room_spawns", fail_compare)
    cmd = cmd_spawncompare.CmdSpawnCompare()
    cmd.caller = Caller()
    cmd.args = ""

    cmd.func()

    assert cmd.caller.messages == ["Spawn compare adapter error: bad adapter data"]


def test_command_handles_live_helper_error_without_traceback(monkeypatch):
    cmd_spawncompare = import_spawncompare_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    def fail_compare(room, band=None):
        raise SpawnCompareError("bad live data")

    monkeypatch.setattr(cmd_spawncompare, "compare_room_spawns", fail_compare)
    cmd = cmd_spawncompare.CmdSpawnCompare()
    cmd.caller = Caller()
    cmd.args = "1"

    cmd.func()

    assert cmd.caller.messages == ["Spawn compare live-data error: bad live data"]


def import_spawncompare_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawncompare", None)
    from commands.admin import cmd_spawncompare

    return cmd_spawncompare
