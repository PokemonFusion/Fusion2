import importlib
import random
import sys
import types

import pytest

from pokemon.spawns.schema import SpawnChart, SpawnEntry


class FakeBattleSession:
    instances = []
    active = None

    @staticmethod
    def ensure_for_player(player):
        return FakeBattleSession.active

    def __init__(self, caller):
        self.caller = caller
        self.battle_id = 77
        self.started = []
        FakeBattleSession.instances.append(self)

    def start_test_battle(self, *, species, level=5, opponent_kind="wild"):
        self.started.append(
            {
                "species": species,
                "level": level,
                "opponent_kind": opponent_kind,
            }
        )


def import_hunttest(monkeypatch):
    FakeBattleSession.instances = []
    FakeBattleSession.active = None
    battle_mod = types.ModuleType("pokemon.battle.battleinstance")
    battle_mod.BattleSession = FakeBattleSession
    monkeypatch.setitem(sys.modules, "pokemon.battle.battleinstance", battle_mod)
    sys.modules.pop("pokemon.spawns.hunttest", None)
    return importlib.import_module("pokemon.spawns.hunttest")


def test_invalid_band_rejected(monkeypatch):
    hunttest = import_hunttest(monkeypatch)

    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        hunttest.parse_hunttest_band("5")
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        hunttest.parse_hunttest_band("rare")
    with pytest.raises(ValueError, match="Usage"):
        hunttest.parse_hunttest_band("1 20")


def test_empty_chart_does_not_start_battle(monkeypatch):
    hunttest = import_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())

    with pytest.raises(ValueError, match="No normal spawn entries"):
        hunttest.run_spawn_hunt_test(
            caller,
            SpawnChart(area_key="empty", entries=[]),
            band=1,
            rng=random.Random(1),
        )

    assert FakeBattleSession.instances == []


def test_special_only_chart_does_not_start_battle(monkeypatch):
    hunttest = import_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())
    chart = SpawnChart(
        area_key="special",
        entries=[SpawnEntry(species_id="Legend", frequency="special", band=4)],
    )

    with pytest.raises(ValueError, match="No normal spawn entries"):
        hunttest.run_spawn_hunt_test(caller, chart, band=4, rng=random.Random(1))

    assert FakeBattleSession.instances == []


def test_valid_chart_rolls_and_requests_wild_test_battle(monkeypatch):
    hunttest = import_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="Pidgey", frequency="frequent", band=1)],
    )

    result = hunttest.run_spawn_hunt_test(caller, chart, band=1, rng=random.Random(1))

    assert result.roll.species_id == "Pidgey"
    assert result.roll.frequency == "frequent"
    assert 5 <= result.roll.level <= 15
    assert result.battle_id == 77
    assert FakeBattleSession.instances[0].started == [
        {
            "species": "Pidgey",
            "level": result.roll.level,
            "opponent_kind": "wild",
        }
    ]


def test_already_in_battle_blocks_before_roll_or_start(monkeypatch):
    hunttest = import_hunttest(monkeypatch)
    FakeBattleSession.active = object()
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="Pidgey", frequency="frequent", band=1)],
    )

    with pytest.raises(hunttest.SpawnHuntTestError, match="already in a battle"):
        hunttest.run_spawn_hunt_test(caller, chart, band=1, rng=random.Random(1))

    assert FakeBattleSession.instances == []


def test_command_handles_adapter_error_without_traceback(monkeypatch):
    cmd_spawnhunttest = import_spawnhunttest_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    def fail_adapter(room):
        from pokemon.spawns.adapters import SpawnAdapterError

        raise SpawnAdapterError("bad adapter data")

    monkeypatch.setattr(cmd_spawnhunttest, "spawn_chart_from_room", fail_adapter)
    cmd = cmd_spawnhunttest.CmdSpawnHuntTest()
    cmd.caller = Caller()
    cmd.args = "1"

    cmd.func()

    assert cmd.caller.messages == ["Spawn hunt test adapter error: bad adapter data"]


def test_command_reports_roll_and_battle(monkeypatch):
    cmd_spawnhunttest = import_spawnhunttest_command(monkeypatch)
    chart = SpawnChart(
        area_key="route-alpha",
        entries=[SpawnEntry(species_id="Pidgey", frequency="frequent", band=1)],
    )

    class Caller:
        def __init__(self):
            self.location = object()
            self.ndb = types.SimpleNamespace()
            self.db = types.SimpleNamespace()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    monkeypatch.setattr(cmd_spawnhunttest, "spawn_chart_from_room", lambda room: chart)
    cmd = cmd_spawnhunttest.CmdSpawnHuntTest()
    cmd.caller = Caller()
    cmd.args = "1"

    cmd.func()

    assert cmd.caller.messages
    assert "PF2 spawn hunt test started battle #77: Pidgey Lv" in cmd.caller.messages[-1]
    assert "(frequent, band 1)" in cmd.caller.messages[-1]


def import_spawnhunttest_command(monkeypatch):
    import_hunttest(monkeypatch)
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnhunttest", None)
    return importlib.import_module("commands.admin.cmd_spawnhunttest")
