import importlib
import sys
import types

from pokemon.spawns.legacy_migration import (
    LegacyHuntChartAudit,
    audit_legacy_hunt_chart,
    format_legacy_hunt_chart_audit,
    recommend_bands_from_level_range,
    recommend_frequency_from_weight,
)


def test_weight_recommendation_thresholds():
    assert recommend_frequency_from_weight(65) == "frequent"
    assert recommend_frequency_from_weight(60) == "frequent"
    assert recommend_frequency_from_weight(30) == "common"
    assert recommend_frequency_from_weight(10) == "uncommon"
    assert recommend_frequency_from_weight(5) == "rare"


def test_missing_weight_warns():
    audit = audit_legacy_hunt_chart(
        [{"name": "Pidgey", "min_level": 5, "max_level": 10}],
        area_key="route-alpha",
    )

    entry = audit.entries[0]
    assert entry.original_weight is None
    assert entry.recommended_frequency is None
    assert "Missing or invalid weight" in entry.warnings[0]


def test_simple_level_range_maps_to_one_band():
    assert recommend_bands_from_level_range(5, 10) == [1]
    assert recommend_bands_from_level_range(16, 25) == [2]
    assert recommend_bands_from_level_range(45, 60) == [4]


def test_overlapping_level_range_maps_to_multiple_bands_with_warning():
    audit = audit_legacy_hunt_chart(
        [{"name": "Pidgey", "weight": 20, "min_level": 10, "max_level": 20}],
        area_key="route-alpha",
    )

    assert audit.entries[0].recommended_bands == [1, 2]
    assert "Level range overlaps multiple PF2 spawn bands." in audit.entries[0].warnings


def test_invalid_max_below_min_warns():
    audit = audit_legacy_hunt_chart(
        [{"name": "Pidgey", "weight": 20, "min_level": 20, "max_level": 10}],
        area_key="route-alpha",
    )

    entry = audit.entries[0]
    assert entry.recommended_bands == []
    assert "Invalid level range: max_level is below min_level." in entry.warnings


def test_out_of_range_levels_warn():
    audit = audit_legacy_hunt_chart(
        [{"name": "Pidgey", "weight": 20, "min_level": 1, "max_level": 6}],
        area_key="route-alpha",
    )

    entry = audit.entries[0]
    assert entry.recommended_bands == [1]
    assert "Level range extends outside PF2 band levels." in entry.warnings


def test_existing_frequency_is_preserved_in_audit_output():
    audit = audit_legacy_hunt_chart(
        [{"name": "Pidgey", "weight": 65, "rarity": "rare", "min_level": 5, "max_level": 10}],
        area_key="route-alpha",
    )
    text = format_legacy_hunt_chart_audit(audit)

    entry = audit.entries[0]
    assert entry.existing_frequency == "rare"
    assert entry.recommended_frequency == "frequent"
    assert "Existing frequency differs from weight recommendation." in entry.warnings
    assert "existing frequency rare" in text


def test_existing_tiers_are_parsed_and_shown():
    audit = audit_legacy_hunt_chart(
        [{"species": "Pidgey", "weight": 20, "min_level": 16, "max_level": 25, "tiers": ["T1", "band2"]}],
        area_key="route-alpha",
    )
    text = format_legacy_hunt_chart_audit(audit)

    entry = audit.entries[0]
    assert entry.existing_tiers == [1, 2]
    assert entry.recommended_bands == [2]
    assert "existing tiers 1, 2" in text


def test_species_strings_and_forms_are_preserved():
    audit = audit_legacy_hunt_chart(
        [
            {"species": "479F", "weight": 10, "min_level": 5, "max_level": 10},
            {"name": "487+", "weight": 5, "min_level": 45, "max_level": 60},
        ],
        area_key="forms",
    )

    assert [entry.species_id for entry in audit.entries] == ["479F", "487+"]


def test_empty_species_warns():
    audit = audit_legacy_hunt_chart(
        [{"name": " ", "weight": 10, "min_level": 5, "max_level": 10}],
        area_key="route-alpha",
    )

    assert audit.entries[0].species_id == ""
    assert "Missing species id." in audit.entries[0].warnings
    assert "Entry #1 is missing a species id." in audit.warnings


def test_full_sample_legacy_chart_audits_correctly():
    audit = audit_legacy_hunt_chart(
        [
            {"name": "Eevee", "weight": 10, "min_level": 5, "max_level": 8},
            {"name": "Pikachu", "weight": 10, "min_level": 5, "max_level": 8},
            {"name": "Abra", "weight": 10, "min_level": 5, "max_level": 8},
            {"name": "Dratini", "weight": 5, "min_level": 5, "max_level": 7},
            {"name": "Rattata", "weight": 65, "min_level": 4, "max_level": 6},
        ],
        area_key="Alpha Route 5 - Rare Patch",
    )

    by_species = {entry.species_id: entry for entry in audit.entries}
    assert by_species["Rattata"].recommended_frequency == "frequent"
    assert by_species["Dratini"].recommended_frequency == "rare"
    assert by_species["Eevee"].recommended_frequency == "uncommon"
    assert by_species["Rattata"].recommended_bands == [1]
    assert "Level range extends outside PF2 band levels." in by_species["Rattata"].warnings


def test_formatter_includes_key_recommendations():
    audit = audit_legacy_hunt_chart(
        [{"name": "Rattata", "weight": 65, "min_level": 4, "max_level": 6}],
        area_key="route-alpha",
    )
    text = format_legacy_hunt_chart_audit(audit)

    assert "PF2 Legacy Hunt Chart Migration Audit" in text
    assert "Area key: route-alpha" in text
    assert "Rattata: weight 65 -> frequent; levels 4-6 -> bands 1" in text
    assert "Recommendations are read-only; no room data was modified." in text


def test_non_list_chart_returns_chart_warning():
    audit = audit_legacy_hunt_chart("bad", area_key="route-alpha")

    assert audit == LegacyHuntChartAudit(
        area_key="route-alpha",
        entries=[],
        warnings=["Legacy hunt_chart data must be a list of entry dictionaries."],
    )


def test_formatter_truncates_large_charts():
    audit = audit_legacy_hunt_chart(
        [
            {"name": f"{index:03d}", "weight": 10, "min_level": 5, "max_level": 10}
            for index in range(1, 16)
        ],
        area_key="large",
    )
    text = format_legacy_hunt_chart_audit(audit, limit=3)

    assert "001: weight 10 -> uncommon" in text
    assert "... (+12 more entries)" in text


def test_command_requires_location(monkeypatch):
    cmd_mod = import_spawnmigratepreview_command(monkeypatch)

    class Caller:
        location = None

        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnMigratePreview()
    cmd.caller = Caller()

    cmd.func()

    assert cmd.caller.messages == ["You must be in a room to preview legacy spawn migration."]


def test_command_reads_room_hunt_chart_without_writing(monkeypatch):
    cmd_mod = import_spawnmigratepreview_command(monkeypatch)

    class DB(types.SimpleNamespace):
        pass

    class Room:
        key = "Route Command"
        id = 42

        def __init__(self):
            self.db = DB(
                hunt_chart=[{"name": "Rattata", "weight": 65, "min_level": 5, "max_level": 10}]
            )

    class Caller:
        def __init__(self):
            self.location = Room()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    caller = Caller()
    before = list(caller.location.db.hunt_chart)
    cmd = cmd_mod.CmdSpawnMigratePreview()
    cmd.caller = caller

    cmd.func()

    assert caller.location.db.hunt_chart == before
    assert "Route Command" in caller.messages[0]
    assert "Rattata: weight 65 -> frequent" in caller.messages[0]


def import_spawnmigratepreview_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnmigratepreview", None)
    return importlib.import_module("commands.admin.cmd_spawnmigratepreview")
