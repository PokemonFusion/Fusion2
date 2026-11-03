import importlib
import sys
import types

import pytest

from pokemon.spawns.profile_compare import (
    ProfileSpawnComparison,
    compare_profile_area,
    format_profile_spawn_comparison,
)
from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.profiles import AreaSpawnEntry, AreaSpawnProfile, SpeciesSpawnProfile


def species_profiles():
    return {
        "A": SpeciesSpawnProfile("A", {1: "common"}),
        "B": SpeciesSpawnProfile("B", {1: "common", 2: "rare"}),
        "S": SpeciesSpawnProfile("S", {4: "special"}),
        "DisabledProfile": SpeciesSpawnProfile("DisabledProfile", {1: "common"}, enabled=False),
    }


def area_profiles():
    return {
        "test_area": AreaSpawnProfile(
            area_key="test_area",
            entries=[
                AreaSpawnEntry("A"),
                AreaSpawnEntry("B", frequency_overrides_by_band={1: "rare"}),
                AreaSpawnEntry("LocalOnly", frequency_overrides_by_band={1: "common"}),
                AreaSpawnEntry("Missing"),
                AreaSpawnEntry("DisabledArea", enabled=False),
                AreaSpawnEntry("DisabledProfile"),
                AreaSpawnEntry("S"),
            ],
        )
    }


def test_area_species_using_global_default_reported():
    comparison = compare_profile_area("test_area", species_profiles(), area_profiles())

    assert "A" in comparison.global_default_species
    assert "B" in comparison.global_default_species


def test_area_species_using_override_reported():
    comparison = compare_profile_area("test_area", species_profiles(), area_profiles())

    assert comparison.override_species == ("B", "LocalOnly")


def test_enabled_species_without_global_profile_or_override_reported_unresolved():
    comparison = compare_profile_area("test_area", species_profiles(), area_profiles())

    assert "Missing" in comparison.unresolved_species
    assert "DisabledProfile" in comparison.unresolved_species


def test_disabled_entries_reported():
    comparison = compare_profile_area("test_area", species_profiles(), area_profiles())

    assert comparison.disabled_species == ("DisabledArea",)


def test_special_configured_entries_reported():
    comparison = compare_profile_area("test_area", species_profiles(), area_profiles())
    text = format_profile_spawn_comparison(comparison)

    assert comparison.special_species == ("S",)
    assert "Special configured: S" in text
    assert "Special entries are configured separately from normal roll tests." in text


def test_unknown_area_key_handled():
    with pytest.raises(SpawnProfileDataError, match="Unknown area profile"):
        compare_profile_area("missing", species_profiles(), area_profiles())


def test_large_list_truncation():
    comparison = ProfileSpawnComparison(
        area_key="large",
        area_entry_count=15,
        resolved_entry_count=0,
        resolved_species=(),
        global_default_species=(),
        override_species=(),
        unresolved_species=tuple(f"{index:03d}" for index in range(1, 16)),
        disabled_species=(),
        special_species=(),
    )

    text = format_profile_spawn_comparison(comparison, limit=3)

    assert "Enabled unresolved: 001, 002, 003, ... (+12 more)" in text


def test_profile_compare_command_unknown_area_has_friendly_error(monkeypatch):
    cmd_mod = import_spawnprofilecompare_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnProfileCompare()
    cmd.caller = Caller()
    cmd.args = "missing_area"

    cmd.func()

    assert cmd.caller.messages == ["Spawn profile compare error: Unknown area profile: 'missing_area'."]


def import_spawnprofilecompare_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnprofilecompare", None)
    return importlib.import_module("commands.admin.cmd_spawnprofilecompare")
