"""Tests for the +battlecheck administrative command."""

import importlib
import sys
import types
from typing import List

import pytest


@pytest.fixture
def snapshot_env():
    """Set up a fake Evennia environment with a mock battle session."""

    orig_evennia = sys.modules.get("evennia")
    fake_evennia = types.ModuleType("evennia")

    class BaseCommand:
        def __init__(self):
            self.caller = None
            self.args = ""
            self.switches: List[str] = []

    fake_evennia.Command = BaseCommand
    fake_evennia.search_object = lambda *a, **k: []
    sys.modules["evennia"] = fake_evennia

    mod = importlib.import_module("commands.admin.cmd_adminbattle")
    mod = importlib.reload(mod)

    class FakeMove:
        def __init__(self, name):
            self.name = name

    class FakePokemon:
        def __init__(self, name, moves):
            self.name = name
            self.hp = 42
            self.max_hp = 100
            self.status = "ok"
            self.moves = [FakeMove(m) for m in moves]
            self.model_id = 12

    class DummyTeam:
        def __init__(self, trainer_name, mons):
            self.trainer = trainer_name
            self._mons = mons

        def returnlist(self):
            return list(self._mons)

    class FakeParticipant:
        def __init__(self, name, team_key, player, pokemon):
            self.name = name
            self.team = team_key
            self.player = player
            self.is_ai = False
            self.pokemons = [pokemon]
            self.active = [pokemon]
            self.pending_action = types.SimpleNamespace(
                action_type=types.SimpleNamespace(name="MOVE"),
                move=pokemon.moves[0],
                target=player,
                priority=1,
            )

    room_db = types.SimpleNamespace(battles=[77])
    setattr(room_db, "battle_77_data", {"teams": {"A": "Red", "B": "Blue"}})
    setattr(room_db, "battle_77_state", {"turn": 3})
    setattr(room_db, "battle_77_trainers", ["Red", "Blue"])
    setattr(room_db, "battle_77_temp_pokemon_ids", [9001])

    room = types.SimpleNamespace(key="Test Arena", id=5, db=room_db, ndb=types.SimpleNamespace())

    trainer_a = types.SimpleNamespace(
        key="Red",
        id=1,
        db=types.SimpleNamespace(battle_id=77),
        ndb=types.SimpleNamespace(),
        team=[],
        active_pokemon=None,
    )
    trainer_b = types.SimpleNamespace(
        key="Blue",
        id=2,
        db=types.SimpleNamespace(battle_id=77),
        ndb=types.SimpleNamespace(),
        team=[],
        active_pokemon=None,
    )
    class FakeObserver:
        def __init__(self, name: str, ident: int):
            self.key = name
            self.id = ident
            self.db = types.SimpleNamespace()
            self.ndb = types.SimpleNamespace()

        def __hash__(self) -> int:  # pragma: no cover - simple helper
            return hash((self.id, self.key))

    observer = FakeObserver("Watcher", 3)

    mon_a = FakePokemon("Pikachu", ["Thunderbolt", "Quick Attack"])
    mon_b = FakePokemon("Bulbasaur", ["Vine Whip"])

    trainer_a.team = [mon_a]
    trainer_b.team = [mon_b]
    trainer_a.active_pokemon = mon_a
    trainer_b.active_pokemon = mon_b

    participant_a = FakeParticipant("Red", "A", trainer_a, mon_a)
    participant_b = FakeParticipant("Blue", "B", trainer_b, mon_b)

    logic_data = types.SimpleNamespace(teams={"A": DummyTeam("Red", [mon_a]), "B": DummyTeam("Blue", [mon_b])})
    logic_battle = types.SimpleNamespace(participants=[participant_a, participant_b], turn_count=4)
    inst = types.SimpleNamespace(
        battle_id=77,
        room=room,
        teamA=[trainer_a],
        teamB=[trainer_b],
        trainers=[trainer_a, trainer_b],
        observers={observer},
        temp_pokemon_ids=[1234],
        state=types.SimpleNamespace(turn=2),
        battle=types.SimpleNamespace(turn_count=1),
        logic=types.SimpleNamespace(data=logic_data, battle=logic_battle),
        ndb=types.SimpleNamespace(watchers_live={observer.id}),
        captainA=trainer_a,
        captainB=trainer_b,
    )

    trainer_a.ndb.battle_instance = inst
    trainer_b.ndb.battle_instance = inst
    room.ndb.battle_instances = {77: inst}

    orig_handler = mod.battle_handler
    mod.battle_handler = types.SimpleNamespace(instances={77: inst})

    try:
        yield types.SimpleNamespace(module=mod, battle_id=77, room=room)
    finally:
        mod.battle_handler = orig_handler
        sys.modules.pop("commands.admin.cmd_adminbattle", None)
        if orig_evennia is not None:
            sys.modules["evennia"] = orig_evennia
        else:
            sys.modules.pop("evennia", None)


class DummyCaller:
    """Simple caller used to capture command output."""

    def __init__(self, location):
        self.location = location
        self.messages: List[str] = []

    def msg(self, text):
        self.messages.append(text)


def test_battle_snapshot_outputs_expected_sections(snapshot_env):
    env = snapshot_env
    cmd = env.module.CmdBattleSnapshot()
    caller = DummyCaller(env.room)
    cmd.caller = caller
    cmd.args = str(env.battle_id)

    cmd.func()

    assert caller.messages
    text = caller.messages[-1]
    assert f"Battle {env.battle_id} snapshot" in text
    assert "Thunderbolt" in text
    assert "battle_instances" in text
    assert "battle_instance" in text  # trainer ndb info
    assert "temp_pokemon_ids" in text
    assert "watchers_live" in text


def test_battle_snapshot_requires_argument(snapshot_env):
    env = snapshot_env
    cmd = env.module.CmdBattleSnapshot()
    caller = DummyCaller(env.room)
    cmd.caller = caller
    cmd.args = ""

    cmd.func()

    assert caller.messages
    assert caller.messages[0].startswith("Usage: +battlecheck")
