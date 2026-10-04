"""Placed trainer launch policy and normal player command coverage."""

from types import SimpleNamespace as NS

import pytest

from commands.player import cmd_challenge
from pokemon.services import trainer_challenges as service
from pokemon.services.trainer_encounters import TrainerEncounter, TrainerEncounterError


@pytest.fixture
def world(monkeypatch):
    """An enabled placed trainer with a three-Pokemon roster."""
    room = NS(contents=[])
    player = NS(location=room, db=NS(), ndb=NS(), key="Player")
    npc = NS(location=room, db=NS(npc_trainer_id=7, trainer_challenge={"enabled": True}), ndb=NS(), id=12)
    room.contents = [npc]
    trainer = NS(name="Test Trainer")
    team = [NS(hp=10) for _ in range(3)]
    encounter = TrainerEncounter("Test Trainer", "Trainer", "static", "single", "basic", team, "Hello")
    captured = NS(started=False, ended=False, created=False)

    class Session:
        @staticmethod
        def ensure_for_player(actor):
            return getattr(actor.ndb, "battle_instance", None)

        def __init__(self, caller):
            captured.created = True
            self.battle_id = 22

        def start_trainer_encounter(self, value):
            captured.started = True
            captured.encounter = value

        def end(self):
            captured.ended = True
            service.release_placed_trainer(self)

    monkeypatch.setattr(service, "BattleSession", Session)
    monkeypatch.setattr(service, "get_battle_party_with_fusion", lambda caller: team)
    monkeypatch.setattr(
        service, "_npc_trainer_model", lambda: NS(objects=NS(filter=lambda **kw: NS(first=lambda: trainer)))
    )
    monkeypatch.setattr(
        service, "check_static_trainer", lambda value: NS(can_start_battle=True, warnings=(), template_count=3)
    )
    monkeypatch.setattr(service, "generate_static_trainer_encounter", lambda value: encounter)
    return NS(player=player, npc=npc, trainer=trainer, team=team, captured=captured)


@pytest.mark.parametrize("battle_format, slots", [("single", 1), ("double", 2)])
def test_launch_preserves_roster_and_metadata(world, battle_format, slots):
    world.npc.db.trainer_challenge.update(battle_format=battle_format, cooldown_seconds=30)
    session, encounter = service.TrainerChallenge(world.player, world.npc, now=100).start()
    assert encounter.team is world.team
    assert len(encounter.team) > slots
    assert encounter.battle_format == battle_format
    assert encounter.metadata["placed_npc_id"] == world.npc.id
    assert world.npc.db.battle_id == session.battle_id
    assert world.npc.db.trainer_challenge_next_at == 130
    service.release_placed_trainer(session)
    assert world.npc.db.battle_id is None
    assert world.npc.ndb.battle_instance is None


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda w: setattr(w.npc, "location", None), "same room"),
        (lambda w: setattr(w.npc.db, "trainer_challenge", None), "not accepting"),
        (lambda w: w.npc.db.trainer_challenge.update(enabled=False), "not accepting"),
        (lambda w: w.npc.db.trainer_challenge.update(battle_format="triple"), "invalid battle format"),
        (lambda w: w.npc.db.trainer_challenge.update(ruleset={"x": True}), "unsupported challenge rules"),
        (lambda w: w.npc.db.trainer_challenge.update(cooldown_seconds=-1), "invalid cooldown"),
        (lambda w: setattr(w.npc.db, "trainer_challenge_next_at", 200), "resting"),
        (lambda w: setattr(w.player.db, "battle_id", 55), "already in a battle"),
        (lambda w: setattr(w.player.db, "battle_lock", "55"), "already in a battle"),
        (lambda w: setattr(w.player.ndb, "battle_instance", object()), "already in a battle"),
        (lambda w: setattr(w.npc.db, "battle_id", 55), "already in a battle"),
        (lambda w: setattr(w.npc.ndb, "battle_instance", object()), "already in a battle"),
        (lambda w: setattr(w.npc.db, "npc_trainer_id", "bad"), "valid trainer link"),
        (lambda w: setattr(w.trainer, "gym_leader_profile", object()), "gym leader"),
        (lambda w: [setattr(mon, "hp", 0) for mon in w.team], "conscious Pokemon"),
        (
            lambda w: (
                w.npc.db.trainer_challenge.update(battle_format="double"),
                [setattr(mon, "hp", 0) for mon in w.team[1:]],
            ),
            "at least 2",
        ),
    ],
)
def test_rejected_before_allocation(world, change, message):
    change(world)
    with pytest.raises(TrainerEncounterError, match=message):
        service.TrainerChallenge(world.player, world.npc, now=100).start()
    assert not world.captured.created
    assert not world.captured.started


@pytest.mark.parametrize(
    "count, ready, warnings", [(0, False, ()), (7, True, ()), (3, False, ()), (3, True, ("bad move",))]
)
def test_invalid_team_blocks_generation(world, monkeypatch, count, ready, warnings):
    monkeypatch.setattr(
        service,
        "check_static_trainer",
        lambda value: NS(can_start_battle=ready, warnings=warnings, template_count=count),
    )
    with pytest.raises(TrainerEncounterError, match="team is not ready"):
        service.TrainerChallenge(world.player, world.npc).start()
    assert not world.captured.created


def test_missing_trainer_record(world, monkeypatch):
    monkeypatch.setattr(
        service, "_npc_trainer_model", lambda: NS(objects=NS(filter=lambda **kw: NS(first=lambda: None)))
    )
    with pytest.raises(TrainerEncounterError, match="record is missing"):
        service.TrainerChallenge(world.player, world.npc).start()
    assert not world.captured.created


def test_session_check_failure_does_not_launch(world, monkeypatch):
    def fail(actor):
        raise RuntimeError("restore unavailable")

    monkeypatch.setattr(service.BattleSession, "ensure_for_player", fail)
    with pytest.raises(RuntimeError):
        service.TrainerChallenge(world.player, world.npc).start()
    assert not world.captured.created


def test_start_failure_releases_npc_and_does_not_apply_cooldown(world, monkeypatch):
    def fail(self, encounter):
        raise RuntimeError("startup failed")

    monkeypatch.setattr(service.BattleSession, "start_trainer_encounter", fail)
    with pytest.raises(RuntimeError):
        service.TrainerChallenge(world.player, world.npc).start()
    assert world.captured.ended
    assert world.npc.db.battle_id is None
    assert not hasattr(world.npc.db, "trainer_challenge_next_at")


def test_release_does_not_clear_another_session(world):
    world.npc.db.battle_id = 33
    service.release_placed_trainer(NS(placed_trainer=world.npc, battle_id=22))
    assert world.npc.db.battle_id == 33


def test_player_command_launches_local_target(world):
    messages = []
    world.player.msg = messages.append

    def search(name, candidates):
        assert name == "Test Trainer"
        assert candidates is world.player.location.contents
        return world.npc

    world.player.search = search
    command = cmd_challenge.CmdChallenge()
    command.caller = world.player
    command.args = "Test Trainer"
    command.func()
    assert messages == ["Started trainer challenge #22 against Test Trainer."]
    assert command.locks == "cmd:all()"


def test_player_command_reports_rejection(world):
    messages = []
    world.player.msg = messages.append
    world.player.search = lambda *args, **kwargs: world.npc
    world.npc.db.trainer_challenge = None
    command = cmd_challenge.CmdChallenge()
    command.caller = world.player
    command.args = "Test Trainer"
    command.func()
    assert messages == ["That NPC is not accepting trainer challenges."]


def test_restored_session_releases_placed_npc(world, monkeypatch):
    """Restored sessions resolve the placement from persisted encounter metadata."""
    import sys
    import types

    world.npc.db.battle_id = 22
    search = types.ModuleType("evennia.utils.search")

    def find(dbref):
        assert dbref == "#12"
        return [world.npc]

    search.search_object = find
    monkeypatch.setitem(sys.modules, "evennia.utils.search", search)
    service.release_placed_trainer(NS(battle_id=22, encounter_metadata={"placed_npc_id": 12}))
    assert world.npc.db.battle_id is None


def test_double_requires_two_npc_templates(world, monkeypatch):
    world.npc.db.trainer_challenge["battle_format"] = "double"
    monkeypatch.setattr(
        service, "check_static_trainer", lambda value: NS(can_start_battle=True, warnings=(), template_count=1)
    )
    with pytest.raises(TrainerEncounterError, match="team is not ready"):
        service.TrainerChallenge(world.player, world.npc).start()
    assert not world.captured.created


def test_command_is_registered_in_player_battle_cmdset():
    from pathlib import Path

    text = Path("commands/cmdsets/battle.py").read_text()
    assert "from commands.player.cmd_challenge import CmdChallenge" in text
    assert "            CmdChallenge," in text


def test_command_reports_service_failure(world, monkeypatch):
    messages = []
    world.player.msg = messages.append
    world.player.search = lambda *args, **kwargs: world.npc

    def fail(self):
        raise RuntimeError("service unavailable")

    monkeypatch.setattr(service.TrainerChallenge, "start", fail)
    monkeypatch.setattr(cmd_challenge, "log_warn", lambda *args, **kwargs: None)
    command = cmd_challenge.CmdChallenge()
    command.caller = world.player
    command.args = "Test Trainer"
    command.func()
    assert "could not start" in messages[0]
    assert not world.captured.created
