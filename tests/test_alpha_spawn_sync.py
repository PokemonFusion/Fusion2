import importlib
import sys
import types

from pokemon.spawns.alpha_sync import (
    AlphaLiveRoomMatch,
    compare_alpha_spawn_data,
    format_alpha_spawn_diff,
    parse_alpha_seed_charts,
)


class DB(types.SimpleNamespace):
    pass


class Room:
    def __init__(self, key="Alpha Route", dbref=67, hunt_chart=None):
        self.key = key
        self.id = dbref
        self.db = DB(hunt_chart=hunt_chart or [])


def seed_entry(**overrides):
    entry = {
        "name": "Rattata",
        "weight": 30,
        "min_level": 5,
        "max_level": 5,
        "frequency": "common",
        "tiers": [1],
    }
    entry.update(overrides)
    return entry


def report_for(seed_charts, live_room, expected=("Alpha Route",)):
    return compare_alpha_spawn_data(
        seed_charts=seed_charts,
        live_room_lookup=lambda room_key: live_room,
        expected_room_keys=expected,
    )


def first_room(report):
    return report.rooms[0]


def test_parse_alpha_seed_charts_from_batch_file_text():
    text = (
        '@set Alpha Route 1 - Low Grass/hunt_chart = '
        '[{"name": "Rattata", "weight": 30, "min_level": 5, "max_level": 5, '
        '"frequency": "common", "tiers": [1]}]'
    )

    charts = parse_alpha_seed_charts(text)

    assert charts["Alpha Route 1 - Low Grass"] == [seed_entry()]


def test_identical_live_and_seed_chart_reports_clean():
    seed = {"Alpha Route": [seed_entry()]}
    report = report_for(seed, Room(hunt_chart=[seed_entry()]))
    room = first_room(report)
    text = format_alpha_spawn_diff(report)

    assert room.live_found is True
    assert room.seed_found is True
    assert room.live_entry_count == 1
    assert room.seed_entry_count == 1
    assert room.entry_diffs == ()
    assert room.safe_to_update is True
    assert "Field differences: none" in text


def test_missing_live_room_is_reported():
    seed = {"Alpha Route": [seed_entry()]}
    report = report_for(seed, None)
    room = first_room(report)

    assert room.live_found is False
    assert room.seed_found is True
    assert room.safe_to_update is False


def test_missing_seed_chart_is_reported():
    report = report_for({}, Room(hunt_chart=[seed_entry()]))
    room = first_room(report)

    assert room.live_found is True
    assert room.seed_found is False
    assert room.errors == ("Seed chart missing.",)
    assert room.safe_to_update is False


def test_missing_frequency_detected():
    seed = {"Alpha Route": [seed_entry()]}
    live = seed_entry()
    live.pop("frequency")

    room = first_room(report_for(seed, Room(hunt_chart=[live])))
    diff = room.entry_diffs[0].field_diffs[0]

    assert diff.field_name == "frequency"
    assert diff.live_value is None
    assert diff.seed_value == "common"
    assert room.safe_to_update is True


def test_missing_tiers_detected():
    seed = {"Alpha Route": [seed_entry()]}
    live = seed_entry()
    live.pop("tiers")

    room = first_room(report_for(seed, Room(hunt_chart=[live])))
    diff = room.entry_diffs[0].field_diffs[0]

    assert diff.field_name == "tiers"
    assert diff.live_value is None
    assert diff.seed_value == [1]
    assert room.safe_to_update is True


def test_min_level_difference_detected():
    seed = {"Alpha Route": [seed_entry()]}
    live = seed_entry(min_level=3)

    room = first_room(report_for(seed, Room(hunt_chart=[live])))
    diff = room.entry_diffs[0].field_diffs[0]

    assert diff.field_name == "min_level"
    assert diff.live_value == 3
    assert diff.seed_value == 5
    assert room.safe_to_update is True


def test_species_mismatch_detected_and_blocks_update():
    seed = {"Alpha Route": [seed_entry(name="Rattata")]}
    live = seed_entry(name="Pidgey")

    room = first_room(report_for(seed, Room(hunt_chart=[live])))

    assert room.species_only_live == ("Pidgey",)
    assert room.species_only_seed == ("Rattata",)
    assert room.entry_diffs == ()
    assert room.safe_to_update is False


def test_safe_to_update_false_when_species_order_differs():
    seed = {"Alpha Route": [seed_entry(name="Rattata"), seed_entry(name="Pidgey")]}
    live = [seed_entry(name="Pidgey"), seed_entry(name="Rattata")]

    room = first_room(report_for(seed, Room(hunt_chart=live)))

    assert room.species_only_live == ()
    assert room.species_only_seed == ()
    assert "Species order differs" in room.errors[0]
    assert room.safe_to_update is False


def test_weight_difference_detected():
    seed = {"Alpha Route": [seed_entry(weight=30)]}
    live = seed_entry(weight=20)

    room = first_room(report_for(seed, Room(hunt_chart=[live])))
    diff = room.entry_diffs[0].field_diffs[0]

    assert diff.field_name == "weight"
    assert diff.live_value == 20
    assert diff.seed_value == 30


def test_formatter_reports_room_status_and_field_differences():
    seed = {"Alpha Route": [seed_entry()]}
    live = seed_entry(min_level=3)

    text = format_alpha_spawn_diff(report_for(seed, Room(hunt_chart=[live])))

    assert "Alpha Spawn Data Diff" in text
    assert "Alpha Route (#67) - safe to update" in text
    assert "min_level live 3 -> seed 5" in text


def test_live_lookup_can_report_duplicate_room_error():
    seed = {"Alpha Route": [seed_entry()]}
    report = compare_alpha_spawn_data(
        seed_charts=seed,
        live_room_lookup=lambda room_key: AlphaLiveRoomMatch(
            room=None,
            error="Multiple live rooms found for 'Alpha Route': #67, #90.",
        ),
    )
    room = first_room(report)

    assert room.live_found is False
    assert room.errors == ("Multiple live rooms found for 'Alpha Route': #67, #90.",)
    assert room.safe_to_update is False


def test_command_outputs_diff_without_writing(monkeypatch):
    cmd_mod = import_alphaspawndiff_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    report = report_for({"Alpha Route": [seed_entry()]}, Room(hunt_chart=[seed_entry()]))
    monkeypatch.setattr(cmd_mod, "compare_alpha_spawn_data", lambda **kwargs: report)
    cmd = cmd_mod.CmdAlphaSpawnDiff()
    cmd.caller = Caller()

    cmd.func()

    assert "Alpha Spawn Data Diff" in cmd.caller.messages[0]


def test_command_aliases_match_requested_names(monkeypatch):
    cmd_mod = import_alphaspawndiff_command(monkeypatch)
    cmd = cmd_mod.CmdAlphaSpawnDiff()

    assert cmd.key == "@alphaspawndiff"
    assert cmd.aliases == ["+alphaspawndiff", "+alpha/spawndiff"]


def import_alphaspawndiff_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_alphaspawndiff", None)
    return importlib.import_module("commands.admin.cmd_alphaspawndiff")
