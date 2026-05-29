import importlib
import sys
import types

from pokemon.spawns.alpha_sync import (
    AlphaLiveRoomMatch,
    alpha_spawn_diff_is_clean,
    apply_alpha_spawn_seed_updates,
    format_alpha_spawn_apply,
)


class DB(types.SimpleNamespace):
    pass


class Room:
    def __init__(self, key="Alpha Route", dbref=67, hunt_chart=None):
        self.key = key
        self.id = dbref
        self.db = DB(
            hunt_chart=hunt_chart if hunt_chart is not None else [],
            notes="leave me alone",
        )


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


def stale_entry(**overrides):
    entry = seed_entry()
    entry.pop("frequency")
    entry.pop("tiers")
    entry.update(overrides)
    return entry


def lookup_from(rooms):
    return lambda room_key: rooms.get(room_key)


def test_apply_updates_only_safe_rooms():
    seed_charts = {
        "Alpha Route 1": [seed_entry(name="Rattata")],
        "Alpha Route 2": [seed_entry(name="Pidgey", weight=25, frequency="uncommon")],
    }
    room_1 = Room(key="Alpha Route 1", dbref=67, hunt_chart=[stale_entry(name="Rattata")])
    room_2 = Room(
        key="Alpha Route 2",
        dbref=70,
        hunt_chart=[stale_entry(name="Pidgey", weight=25)],
    )

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route 1": room_1, "Alpha Route 2": room_2}),
    )

    assert result.refused_rooms == ()
    assert [update.room_key for update in result.updated_rooms] == ["Alpha Route 1", "Alpha Route 2"]
    assert room_1.db.hunt_chart == seed_charts["Alpha Route 1"]
    assert room_2.db.hunt_chart == seed_charts["Alpha Route 2"]


def test_apply_refuses_unsafe_species_mismatch_without_writing():
    seed_charts = {"Alpha Route": [seed_entry(name="Rattata")]}
    live_chart = [seed_entry(name="Pidgey")]
    room = Room(hunt_chart=live_chart)

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )

    assert result.updated_rooms == ()
    assert len(result.refused_rooms) == 1
    assert room.db.hunt_chart == live_chart


def test_apply_refuses_missing_live_room_without_writing_other_rooms():
    seed_charts = {
        "Alpha Route 1": [seed_entry(name="Rattata")],
        "Alpha Route 2": [seed_entry(name="Pidgey")],
    }
    room_1 = Room(key="Alpha Route 1", hunt_chart=[stale_entry(name="Rattata")])

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route 1": room_1}),
    )

    assert result.updated_rooms == ()
    assert [room.room_key for room in result.refused_rooms] == ["Alpha Route 2"]
    assert room_1.db.hunt_chart == [stale_entry(name="Rattata")]


def test_apply_refuses_duplicate_live_room_key():
    seed_charts = {"Alpha Route": [seed_entry()]}

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lambda room_key: AlphaLiveRoomMatch(
            room=None,
            error="Multiple live rooms found for 'Alpha Route': #67, #99.",
        ),
    )

    assert result.updated_rooms == ()
    assert len(result.refused_rooms) == 1
    assert "Multiple live rooms found" in result.refused_rooms[0].errors[0]


def test_apply_refuses_missing_seed_chart():
    room = Room(hunt_chart=[seed_entry()])

    result = apply_alpha_spawn_seed_updates(
        seed_charts={},
        live_room_lookup=lookup_from({"Alpha Route": room}),
        expected_room_keys=("Alpha Route",),
    )

    assert result.updated_rooms == ()
    assert len(result.refused_rooms) == 1
    assert result.refused_rooms[0].errors == ("Seed chart missing.",)


def test_post_apply_comparison_reports_clean():
    seed_charts = {"Alpha Route": [seed_entry()]}
    room = Room(hunt_chart=[stale_entry()])

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )

    assert result.after_report is not None
    assert alpha_spawn_diff_is_clean(result.after_report) is True
    assert "Post-apply diff: clean" in format_alpha_spawn_apply(result)


def test_apply_does_not_change_unrelated_attrs():
    seed_charts = {"Alpha Route": [seed_entry()]}
    room = Room(hunt_chart=[stale_entry()])

    apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )

    assert room.db.notes == "leave me alone"


def test_apply_writes_exact_parsed_seed_hunt_chart_as_copy():
    seed_charts = {"Alpha Route": [seed_entry()]}
    room = Room(hunt_chart=[stale_entry()])

    apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )

    assert room.db.hunt_chart == seed_charts["Alpha Route"]
    assert room.db.hunt_chart is not seed_charts["Alpha Route"]
    room.db.hunt_chart[0]["frequency"] = "rare"
    assert seed_charts["Alpha Route"][0]["frequency"] == "common"


def test_apply_formatter_lists_refused_rooms():
    seed_charts = {"Alpha Route": [seed_entry(name="Rattata")]}
    room = Room(hunt_chart=[seed_entry(name="Pidgey")])

    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )
    text = format_alpha_spawn_apply(result)

    assert "Apply refused" in text
    assert "Updated rooms: 0" in text
    assert "Species only live: Pidgey" in text
    assert "Species only seed: Rattata" in text


def test_command_outputs_apply_result(monkeypatch):
    cmd_mod = import_alphaspawnapply_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    seed_charts = {"Alpha Route": [seed_entry()]}
    room = Room(hunt_chart=[stale_entry()])
    result = apply_alpha_spawn_seed_updates(
        seed_charts=seed_charts,
        live_room_lookup=lookup_from({"Alpha Route": room}),
    )
    monkeypatch.setattr(cmd_mod, "apply_alpha_spawn_seed_updates", lambda **kwargs: result)
    cmd = cmd_mod.CmdAlphaSpawnApply()
    cmd.caller = Caller()

    cmd.func()

    assert "Alpha Spawn Apply" in cmd.caller.messages[0]
    assert "Updated rooms: 1" in cmd.caller.messages[0]


def test_command_aliases_match_requested_names(monkeypatch):
    cmd_mod = import_alphaspawnapply_command(monkeypatch)
    cmd = cmd_mod.CmdAlphaSpawnApply()

    assert cmd.key == "@alphaspawnapply"
    assert cmd.aliases == ["+alphaspawnapply", "+alpha/spawnapply"]


def import_alphaspawnapply_command(monkeypatch):
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_alphaspawndiff", None)
    sys.modules.pop("commands.admin.cmd_alphaspawnapply", None)
    return importlib.import_module("commands.admin.cmd_alphaspawnapply")
