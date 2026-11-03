import types
import sys

import pytest

from pokemon.spawns.adapters import SpawnAdapterError
from pokemon.spawns.preview import (
    format_species_group,
    format_spawn_preview,
    parse_preview_band,
)
from pokemon.spawns.schema import SpawnChart, SpawnEntry


def test_empty_chart_display():
    chart = SpawnChart(area_key="route-empty", entries=[])

    text = format_spawn_preview(chart, source="empty")

    assert "PF2 Spawn Preview" in text
    assert "Area key: route-empty" in text
    assert "Source: empty" in text
    assert "Total converted entries: 0" in text
    assert "No converted spawn entries were found." in text


def test_grouped_chart_display():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="025", frequency="frequent", band=1),
            SpawnEntry(species_id="039", frequency="common", band=1),
            SpawnEntry(species_id="479F", frequency="rare", band=2, enabled=False),
            SpawnEntry(species_id="Legend", frequency="special", band=4),
        ],
    )

    text = format_spawn_preview(chart, source="hunt_chart")

    assert "Source: hunt_chart" in text
    assert "Band 1" in text
    assert "  frequent: 025" in text
    assert "  common: 039" in text
    assert "Band 2" in text
    assert "  rare disabled: 479F" in text
    assert "Band 4" in text
    assert "  special (not normal roll): Legend" in text
    assert "normal roll ignores special" in text


def test_band_filter_limits_displayed_entries():
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[
            SpawnEntry(species_id="A", frequency="frequent", band=1),
            SpawnEntry(species_id="B", frequency="common", band=2),
        ],
    )

    text = format_spawn_preview(chart, source="spawn_table", band=2)

    assert "Band filter: 2 (1 shown)" in text
    assert "Band 1" not in text
    assert "Band 2" in text
    assert "  common: B" in text


def test_invalid_band_is_friendly():
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        parse_preview_band("5")
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        parse_preview_band("rare")


def test_species_group_truncates_large_groups():
    text = format_species_group([f"{index:03d}" for index in range(1, 15)], limit=3)

    assert text == "001, 002, 003, ... (+11 more)"


def test_command_handles_adapter_error_without_traceback(monkeypatch):
    cmd_spawnpreview = import_spawnpreview_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    def fail_adapter(room):
        raise SpawnAdapterError("bad spawn data")

    monkeypatch.setattr(cmd_spawnpreview, "spawn_chart_from_room", fail_adapter)
    cmd = cmd_spawnpreview.CmdSpawnPreview()
    cmd.caller = Caller()
    cmd.args = ""

    cmd.func()

    assert cmd.caller.messages == ["Spawn preview error: bad spawn data"]


def test_command_handles_missing_location(monkeypatch):
    cmd_spawnpreview = import_spawnpreview_command(monkeypatch)

    caller = types.SimpleNamespace(location=None, messages=[])
    caller.msg = caller.messages.append
    cmd = cmd_spawnpreview.CmdSpawnPreview()
    cmd.caller = caller
    cmd.args = ""

    cmd.func()

    assert caller.messages == ["You must be in a room to preview spawn data."]


def import_spawnpreview_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnpreview", None)
    from commands.admin import cmd_spawnpreview

    return cmd_spawnpreview
