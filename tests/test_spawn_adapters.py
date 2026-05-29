from collections import UserDict, UserList
import types
from dataclasses import fields

import pytest

from pokemon.spawns.adapters import (
    SpawnAdapterError,
    coerce_spawn_data_entries,
    normalize_band,
    normalize_frequency,
    normalize_species_id,
    spawn_chart_from_hunt_chart,
    spawn_chart_from_room,
    spawn_chart_from_spawn_table,
)
from pokemon.spawns.schema import SpawnChart, SpawnEntry


class DummyDB(types.SimpleNamespace):
    pass


class DummyRoom:
    def __init__(self, **kwargs):
        self.key = kwargs.pop("key", "Route 1")
        self.id = kwargs.pop("id", 1001)
        self.db = DummyDB(**kwargs)


def entry_tuples(chart):
    return [
        (entry.species_id, entry.frequency, entry.band, entry.enabled)
        for entry in chart.entries
    ]


def test_converts_representative_hunt_chart_shape():
    chart = spawn_chart_from_hunt_chart(
        [
            {"name": " Rattata ", "rarity": "rare", "min_level": 5, "max_level": 5},
            {"species": "Pidgey", "frequency": "Common", "tiers": ["T1"]},
            {"name": "Oddish", "weight": 30},
        ],
        area_key="route-1",
    )

    assert isinstance(chart, SpawnChart)
    assert chart.area_key == "route-1"
    assert entry_tuples(chart) == [
        ("Rattata", "rare", 1, True),
        ("Pidgey", "common", 1, True),
        ("Oddish", "common", 1, True),
    ]


def test_converts_stringified_hunt_chart_shape_from_batchcommands():
    chart = spawn_chart_from_hunt_chart(
        '[{"name": "Rattata", "weight": 30, "min_level": 3, "max_level": 5}]',
        area_key="route-string",
    )

    assert entry_tuples(chart) == [("Rattata", "common", 1, True)]


def test_converts_python_literal_stringified_spawn_data():
    entries = coerce_spawn_data_entries("[{'name': 'Pidgey', 'weight': 25}]")

    assert entries == [{"name": "Pidgey", "weight": 25}]


def test_converts_evennia_style_list_and_mapping_wrappers():
    entries = coerce_spawn_data_entries(
        UserList([UserDict({"name": "Rattata", "weight": 30})])
    )

    assert entries == [{"name": "Rattata", "weight": 30}]


def test_converts_representative_spawn_table_shape():
    chart = spawn_chart_from_spawn_table(
        [
            {
                "species": "Pidgey",
                "rarity": "uncommon",
                "tiers": ["T2", "T3"],
                "generations": ["1"],
            }
        ],
        area_key="route-2",
    )

    assert entry_tuples(chart) == [
        ("Pidgey", "uncommon", 2, True),
        ("Pidgey", "uncommon", 3, True),
    ]


def test_hunt_chart_takes_priority_over_spawn_table():
    room = DummyRoom(
        hunt_chart=[{"name": "Hoothoot", "rarity": "common"}],
        spawn_table=[{"species": "Sentret", "rarity": "frequent", "tiers": ["T1"]}],
    )

    chart = spawn_chart_from_room(room, area_key="route-priority")

    assert entry_tuples(chart) == [("Hoothoot", "common", 1, True)]


def test_spawn_table_is_used_when_hunt_chart_is_empty():
    room = DummyRoom(
        hunt_chart=[],
        spawn_table=[{"species": "Sentret", "rarity": "frequent", "tiers": ["T1"]}],
    )

    chart = spawn_chart_from_room(room, area_key="route-fallback")

    assert entry_tuples(chart) == [("Sentret", "frequent", 1, True)]


def test_area_key_fallback_prefers_room_spawn_area_key():
    room = DummyRoom(spawn_area_key="route-db-key", hunt_chart=[{"name": "Rattata"}])

    assert spawn_chart_from_room(room).area_key == "route-db-key"


def test_area_key_fallback_uses_room_key_then_id():
    room_with_key = DummyRoom(key="Route Key", hunt_chart=[{"name": "Rattata"}])
    room_without_key = DummyRoom(key="", id=42, hunt_chart=[{"name": "Rattata"}])

    assert spawn_chart_from_room(room_with_key).area_key == "Route Key"
    assert spawn_chart_from_room(room_without_key).area_key == "42"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("f", "frequent"),
        ("c", "common"),
        ("u", "uncommon"),
        ("r", "rare"),
        ("s", "special"),
    ],
)
def test_one_letter_frequencies_normalize(raw, expected):
    assert normalize_frequency(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Frequent", "frequent"),
        ("COMMON", "common"),
        (" uncommon ", "uncommon"),
        ("Rare", "rare"),
        ("Special", "special"),
        ("legendary", "special"),
        ("epic", "rare"),
    ],
)
def test_full_frequency_names_normalize(raw, expected):
    assert normalize_frequency(raw) == expected


def test_multiple_tiers_produce_multiple_entries():
    chart = spawn_chart_from_spawn_table(
        [{"species": "Pikachu", "rarity": "common", "tiers": ["T1", "T2", "3"]}],
        area_key="route-multi",
    )

    assert entry_tuples(chart) == [
        ("Pikachu", "common", 1, True),
        ("Pikachu", "common", 2, True),
        ("Pikachu", "common", 3, True),
    ]


def test_alternate_form_species_strings_are_preserved():
    chart = spawn_chart_from_spawn_table(
        [
            {"species": "479F", "rarity": "common", "tiers": ["T1"]},
            {"species": "487+", "rarity": "uncommon", "tiers": ["T2"]},
            {"species": "678M", "rarity": "rare", "tiers": ["T4"]},
        ],
        area_key="forms",
    )

    assert [entry.species_id for entry in chart.entries] == ["479F", "487+", "678M"]


def test_enabled_flag_is_preserved_when_present():
    chart = spawn_chart_from_spawn_table(
        [{"species": "Zubat", "rarity": "common", "tiers": ["T1"], "enabled": False}],
        area_key="cave",
    )

    assert chart.entries[0].enabled is False


def test_invalid_frequency_raises_clear_error():
    with pytest.raises(SpawnAdapterError, match="Unknown spawn frequency"):
        normalize_frequency("everywhere")
    with pytest.raises(SpawnAdapterError, match="Unknown spawn frequency"):
        spawn_chart_from_spawn_table(
            [{"species": "Pikachu", "rarity": "everywhere", "tiers": ["T1"]}],
            area_key="bad-frequency",
        )


def test_invalid_band_raises_clear_error():
    with pytest.raises(SpawnAdapterError, match="Invalid spawn band"):
        normalize_band("T5")
    with pytest.raises(SpawnAdapterError, match="Invalid spawn band"):
        spawn_chart_from_spawn_table(
            [{"species": "Pikachu", "rarity": "common", "tiers": ["T5"]}],
            area_key="bad-band",
        )


def test_empty_species_id_raises_clear_error():
    with pytest.raises(SpawnAdapterError, match="species_id"):
        normalize_species_id(" ")


def test_empty_or_missing_room_data_returns_empty_valid_chart():
    empty_chart = spawn_chart_from_room(DummyRoom(hunt_chart=[], spawn_table=[]), area_key="empty")
    missing_chart = spawn_chart_from_room(DummyRoom(), area_key="missing")

    assert empty_chart == SpawnChart(area_key="empty", entries=[])
    assert missing_chart == SpawnChart(area_key="missing", entries=[])


def test_no_version_or_variant_fields_are_introduced():
    chart = spawn_chart_from_spawn_table(
        [{"species": "Pikachu", "rarity": "common", "tiers": ["T1"]}],
        area_key="route-clean",
    )
    field_names = {field.name for field in fields(SpawnEntry)}

    assert field_names == {"species_id", "frequency", "band", "enabled"}
    assert not hasattr(chart.entries[0], "version")
    assert not hasattr(chart.entries[0], "variant")
