import importlib
import random
import sys
import types

import pytest

from pokemon.spawns.profile_data import SpawnProfileDataError
from pokemon.spawns.schema import SpawnChart, SpawnEntry


class FakeBattleSession:
    instances = []
    active = None

    @staticmethod
    def ensure_for_player(player):
        return FakeBattleSession.active

    def __init__(self, caller):
        self.caller = caller
        self.battle_id = 91
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


def import_profile_hunttest(monkeypatch):
    FakeBattleSession.instances = []
    FakeBattleSession.active = None
    battle_mod = types.ModuleType("pokemon.battle.battleinstance")
    battle_mod.BattleSession = FakeBattleSession
    monkeypatch.setitem(sys.modules, "pokemon.battle.battleinstance", battle_mod)
    sys.modules.pop("pokemon.spawns.hunttest", None)
    sys.modules.pop("pokemon.spawns.profile_hunttest", None)
    return importlib.import_module("pokemon.spawns.profile_hunttest")


def test_invalid_band_rejected(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)

    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        profile_hunttest.parse_profile_hunttest_args("route_1 5")
    with pytest.raises(ValueError, match="Band must be a number from 1 to 4"):
        profile_hunttest.parse_profile_hunttest_args("route_1 rare")
    with pytest.raises(ValueError, match="Usage"):
        profile_hunttest.parse_profile_hunttest_args("")


def test_unknown_area_key_handled(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())

    with pytest.raises(SpawnProfileDataError, match="Unknown area profile"):
        profile_hunttest.run_profile_spawn_hunt_test(caller, "missing_area", band=1)

    assert FakeBattleSession.instances == []


def test_empty_chart_does_not_start_battle(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())

    with pytest.raises(ValueError, match="No normal spawn entries"):
        profile_hunttest.run_profile_spawn_hunt_test(
            caller,
            "empty",
            band=1,
            rng=random.Random(1),
            chart_resolver=lambda area_key: SpawnChart(area_key=area_key, entries=[]),
        )

    assert FakeBattleSession.instances == []


def test_special_only_chart_does_not_start_battle(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())
    chart = SpawnChart(
        area_key="special",
        entries=[SpawnEntry(species_id="144", frequency="special", band=4)],
    )

    with pytest.raises(ValueError, match="No normal spawn entries"):
        profile_hunttest.run_profile_spawn_hunt_test(
            caller,
            "special",
            band=4,
            rng=random.Random(1),
            chart_resolver=lambda area_key: chart,
        )

    assert FakeBattleSession.instances == []


def test_valid_profile_area_produces_roll_and_requests_wild_battle(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())

    result = profile_hunttest.run_profile_spawn_hunt_test(
        caller,
        "route_1",
        band=1,
        rng=random.Random(1),
    )

    assert result.roll.species_id in {"019", "016", "025"}
    assert result.roll.band == 1
    assert result.battle_id == 91
    assert FakeBattleSession.instances[0].started == [
        {
            "species": result.roll.species_id,
            "level": result.roll.level,
            "opponent_kind": "wild",
        }
    ]


def test_already_in_battle_blocks_before_roll_or_start(monkeypatch):
    profile_hunttest = import_profile_hunttest(monkeypatch)
    FakeBattleSession.active = object()
    caller = types.SimpleNamespace(ndb=types.SimpleNamespace(), db=types.SimpleNamespace())

    with pytest.raises(profile_hunttest.SpawnHuntTestError, match="already in a battle"):
        profile_hunttest.run_profile_spawn_hunt_test(
            caller,
            "route_1",
            band=1,
            rng=random.Random(1),
        )

    assert FakeBattleSession.instances == []


def test_command_does_not_use_room_spawn_attrs(monkeypatch):
    cmd_mod = import_spawnprofilehunttest_command(monkeypatch)

    class ExplodingLocation:
        @property
        def db(self):
            raise AssertionError("room attrs should not be read")

    class Caller:
        def __init__(self):
            self.location = ExplodingLocation()
            self.ndb = types.SimpleNamespace()
            self.db = types.SimpleNamespace()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnProfileHuntTest()
    cmd.caller = Caller()
    cmd.args = "route_1 1"

    cmd.func()

    assert cmd.caller.messages
    assert "PF2 profile spawn hunt test started battle #91: area route_1" in cmd.caller.messages[-1]


def test_command_unknown_area_has_friendly_error(monkeypatch):
    cmd_mod = import_spawnprofilehunttest_command(monkeypatch)

    class Caller:
        def __init__(self):
            self.location = object()
            self.messages = []

        def msg(self, text):
            self.messages.append(text)

    cmd = cmd_mod.CmdSpawnProfileHuntTest()
    cmd.caller = Caller()
    cmd.args = "missing_area 1"

    cmd.func()

    assert cmd.caller.messages == ["Spawn profile hunt test error: Unknown area profile: 'missing_area'."]


def import_spawnprofilehunttest_command(monkeypatch):
    import_profile_hunttest(monkeypatch)
    fake_evennia = types.ModuleType("evennia")
    fake_evennia.Command = type("Command", (), {})
    monkeypatch.setitem(sys.modules, "evennia", fake_evennia)
    sys.modules.pop("commands.admin.cmd_spawnprofilehunttest", None)
    return importlib.import_module("commands.admin.cmd_spawnprofilehunttest")
