import importlib
import random
import sys
import types

import pytest

from pokemon.spawns.profile_data import (
    SAMPLE_AREA_PROFILES_PATH,
    SAMPLE_SPECIES_PROFILES_PATH,
    SpawnProfileDataError,
    load_area_profiles_from_mapping,
    load_area_profiles_from_path,
    load_species_profiles_from_mapping,
    load_species_profiles_from_path,
    resolve_area_from_profile_data,
)
from pokemon.spawns.profiles import AreaSpawnEntry, AreaSpawnProfile, SpawnProfileError, SpeciesSpawnProfile
from pokemon.spawns.schema import SpawnEntry
from pokemon.spawns.selection import roll_spawn


def species_data():
    return {
        "profiles": [
            {
                "species_id": "019",
                "enabled": True,
                "frequencies_by_band": {"1": "frequent", "2": "common", "3": None, "4": None},
            },
            {
                "species_id": "025",
                "enabled": True,
                "frequencies_by_band": {"1": "uncommon", "2": "uncommon", "3": "rare", "4": "rare"},
            },
            {
                "species_id": "479F",
                "enabled": True,
                "frequencies_by_band": {"1": "rare", "2": "rare", "3": "rare", "4": "rare"},
            },
            {
                "species_id": "144",
                "enabled": True,
                "frequencies_by_band": {"1": None, "2": None, "3": None, "4": "special"},
            },
        ]
    }


def area_data():
    return {
        "areas": [
            {
                "area_key": "route_test",
                "entries": [
                    {"species_id": "019", "enabled": True, "frequency_overrides_by_band": {}},
                    {"species_id": "025", "enabled": True, "frequency_overrides_by_band": {"1": "rare"}},
                    {"species_id": "479F", "enabled": True, "frequency_overrides_by_band": {}},
                    {"species_id": "MissingOverride", "enabled": True, "frequency_overrides_by_band": {"1": "common"}},
                    {"species_id": "MissingSkipped", "enabled": True, "frequency_overrides_by_band": {}},
                ],
            },
            {
                "area_key": "special_test",
                "entries": [
                    {"species_id": "144", "enabled": True, "frequency_overrides_by_band": {}},
                ],
            },
        ]
    }


def test_load_species_profiles_from_mapping():
    profiles = load_species_profiles_from_mapping(species_data())

    assert profiles["019"] == SpeciesSpawnProfile(
        species_id="019",
        enabled=True,
        frequencies_by_band={1: "frequent", 2: "common", 3: None, 4: None},
    )


def test_load_area_profiles_from_mapping():
    profiles = load_area_profiles_from_mapping(area_data())

    assert profiles["route_test"].entries[1] == AreaSpawnEntry(
        species_id="025",
        enabled=True,
        frequency_overrides_by_band={1: "rare"},
    )


def test_resolve_area_profile_data_into_spawn_chart():
    chart = resolve_area_from_profile_data(
        "route_test",
        load_species_profiles_from_mapping(species_data()),
        load_area_profiles_from_mapping(area_data()),
    )

    assert chart.area_key == "route_test"
    assert SpawnEntry("019", "frequent", 1) in chart.entries
    assert SpawnEntry("019", "common", 2) in chart.entries


def test_area_override_changes_one_band_frequency():
    chart = resolve_area_from_profile_data(
        "route_test",
        load_species_profiles_from_mapping(species_data()),
        load_area_profiles_from_mapping(area_data()),
    )

    pikachu_band_one = [entry for entry in chart.entries if entry.species_id == "025" and entry.band == 1]

    assert pikachu_band_one == [SpawnEntry("025", "rare", 1)]


def test_missing_global_profile_skipped_unless_override_exists():
    chart = resolve_area_from_profile_data(
        "route_test",
        load_species_profiles_from_mapping(species_data()),
        load_area_profiles_from_mapping(area_data()),
    )

    assert SpawnEntry("MissingOverride", "common", 1) in chart.entries
    assert all(entry.species_id != "MissingSkipped" for entry in chart.entries)


def test_alternate_form_species_string_preserved():
    chart = resolve_area_from_profile_data(
        "route_test",
        load_species_profiles_from_mapping(species_data()),
        load_area_profiles_from_mapping(area_data()),
    )

    assert any(entry.species_id == "479F" for entry in chart.entries)


def test_special_species_loaded_and_resolved():
    chart = resolve_area_from_profile_data(
        "special_test",
        load_species_profiles_from_mapping(species_data()),
        load_area_profiles_from_mapping(area_data()),
    )

    assert chart.entries == [SpawnEntry("144", "special", 4)]


def test_duplicate_global_species_raises_error():
    data = {
        "profiles": [
            {"species_id": "019", "frequencies_by_band": {"1": "common"}},
            {"species_id": "019", "frequencies_by_band": {"1": "rare"}},
        ]
    }

    with pytest.raises(SpawnProfileDataError, match="Duplicate species profile"):
        load_species_profiles_from_mapping(data)


def test_duplicate_area_key_raises_error():
    data = {
        "areas": [
            {"area_key": "route_test", "entries": []},
            {"area_key": "route_test", "entries": []},
        ]
    }

    with pytest.raises(SpawnProfileDataError, match="Duplicate area profile"):
        load_area_profiles_from_mapping(data)


def test_duplicate_area_species_raises_error():
    data = {
        "areas": [
            {
                "area_key": "route_test",
                "entries": [
                    {"species_id": "019", "frequency_overrides_by_band": {}},
                    {"species_id": "019", "frequency_overrides_by_band": {}},
                ],
            }
        ]
    }

    with pytest.raises(SpawnProfileDataError, match="Duplicate species"):
        load_area_profiles_from_mapping(data)


def test_invalid_frequency_raises_error():
    data = {"profiles": [{"species_id": "019", "frequencies_by_band": {"1": "everywhere"}}]}

    with pytest.raises(SpawnProfileError, match="Invalid spawn frequency"):
        load_species_profiles_from_mapping(data)


def test_invalid_band_raises_error():
    data = {"profiles": [{"species_id": "019", "frequencies_by_band": {"5": "common"}}]}

    with pytest.raises(SpawnProfileError, match="Invalid spawn band"):
        load_species_profiles_from_mapping(data)


def test_missing_required_keys_raise_clear_error():
    with pytest.raises(SpawnProfileDataError, match="Missing profiles"):
        load_species_profiles_from_mapping({})
    with pytest.raises(SpawnProfileDataError, match="Missing area_key"):
        load_area_profiles_from_mapping({"areas": [{"entries": []}]})
    with pytest.raises(SpawnProfileDataError, match="Missing frequencies_by_band"):
        load_species_profiles_from_mapping({"profiles": [{"species_id": "019"}]})


def test_sample_json_files_load_successfully():
    species_profiles = load_species_profiles_from_path(SAMPLE_SPECIES_PROFILES_PATH)
    area_profiles = load_area_profiles_from_path(SAMPLE_AREA_PROFILES_PATH)

    assert "019" in species_profiles
    assert "route_1" in area_profiles
    assert "special_test" in area_profiles


def test_resolved_sample_area_works_with_roll_spawn():
    chart = resolve_area_from_profile_data(
        "route_1",
        load_species_profiles_from_path(SAMPLE_SPECIES_PROFILES_PATH),
        load_area_profiles_from_path(SAMPLE_AREA_PROFILES_PATH),
    )

    result = roll_spawn(chart, 1, rng=random.Random(1))

    assert result.species_id in {"019", "016", "025"}
    assert result.band == 1


def test_profile_preview_command_uses_sample_file_data(monkeypatch):
    cmd_mod = import_spawnprofilepreview_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnProfilePreview()
    cmd.caller = Caller()
    cmd.args = "route_1"

    cmd.func()

    assert cmd.caller.messages
    assert "PF2 Spawn Preview" in cmd.caller.messages[-1]
    assert "Area key: route_1" in cmd.caller.messages[-1]
    assert "Source: sample file-backed profile data" in cmd.caller.messages[-1]


def import_spawnprofilepreview_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnprofilepreview", None)
    return importlib.import_module("commands.admin.cmd_spawnprofilepreview")
