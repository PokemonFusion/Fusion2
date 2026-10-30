import types

from commands.admin import cmd_npcbattle
from pokemon.services.trainer_encounters import StaticTrainerCheck, StaticTrainerTemplateCheck


class DummyCaller:
    def __init__(self):
        self.key = "Caller"
        self.messages = []
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace()
        self.location = types.SimpleNamespace(
            db=types.SimpleNamespace(battles=[]),
            ndb=types.SimpleNamespace(battle_instances={}),
        )

    def msg(self, text):
        self.messages.append(text)


def test_npcbattle_command_starts_static_trainer_battle(monkeypatch):
    caller = DummyCaller()
    encounter = types.SimpleNamespace(display_name="Test Trainer", team=[object(), object()])
    captured = {}

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            captured["checked"] = player
            return None

        def __init__(self, player):
            captured["player"] = player
            self.battle_id = 101

        def start_trainer_encounter(self, passed_encounter):
            captured["encounter"] = passed_encounter

    monkeypatch.setattr(cmd_npcbattle, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_npcbattle, "has_usable_pokemon", lambda player: True)
    def fake_generate_static_trainer_encounter(name):
        captured["name"] = name
        return encounter

    monkeypatch.setattr(
        cmd_npcbattle,
        "generate_static_trainer_encounter",
        fake_generate_static_trainer_encounter,
    )

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = "Test Trainer"

    cmd.func()

    assert captured["checked"] is caller
    assert captured["player"] is caller
    assert captured["name"] == "Test Trainer"
    assert captured["encounter"] is encounter
    assert caller.messages[-1] == "Started NPC trainer battle #101 against Test Trainer."


def test_npcbattle_command_reports_static_trainer_error(monkeypatch):
    caller = DummyCaller()

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            return None

    def raise_error(name):
        raise cmd_npcbattle.TrainerEncounterError("NPC trainer 'Missing' was not found.")

    monkeypatch.setattr(cmd_npcbattle, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_npcbattle, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(cmd_npcbattle, "generate_static_trainer_encounter", raise_error)

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = "Missing"

    cmd.func()

    assert caller.messages[-1] == "NPC trainer 'Missing' was not found."


def test_npcbattle_list_shows_usable_trainers(monkeypatch):
    caller = DummyCaller()
    checks = [
        StaticTrainerCheck(
            name="Test Trainer",
            found=True,
            templates=(
                StaticTrainerTemplateCheck("lead", "Pikachu", 8, 1),
            ),
        )
    ]
    monkeypatch.setattr(cmd_npcbattle, "list_static_trainers_with_templates", lambda: checks)

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = ""
    cmd.switches = {"list"}

    cmd.func()

    assert "Static NPC trainers with templates:" in caller.messages[-1]
    assert "Test Trainer - 1 Pokemon - ready - Pikachu Lv8" in caller.messages[-1]


def test_npcbattle_check_reports_missing_trainer(monkeypatch):
    caller = DummyCaller()
    check = StaticTrainerCheck(
        name="Missing",
        found=False,
        issues=("NPC trainer 'Missing' was not found.",),
    )
    monkeypatch.setattr(cmd_npcbattle, "check_static_trainer", lambda name: check)

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = "Missing"
    cmd.switches = {"check"}

    cmd.func()

    assert caller.messages[-1] == "NPC trainer 'Missing' was not found."


def test_npcbattle_check_reports_no_templates(monkeypatch):
    caller = DummyCaller()
    check = StaticTrainerCheck(
        name="Empty Trainer",
        found=True,
        issues=("No Pokemon templates.",),
    )
    monkeypatch.setattr(cmd_npcbattle, "check_static_trainer", lambda name: check)

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = "Empty Trainer"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "Static NPC trainer check: Empty Trainer" in text
    assert "Template Pokemon: 0" in text
    assert "Battle startup: blocked" in text
    assert "No Pokemon templates." in text


def test_npcbattle_check_reports_templates_in_order(monkeypatch):
    caller = DummyCaller()
    check = StaticTrainerCheck(
        name="Ordered Trainer",
        found=True,
        templates=(
            StaticTrainerTemplateCheck("lead", "Pikachu", 8, 1),
            StaticTrainerTemplateCheck("second", "Eevee", 6, 2),
        ),
    )
    monkeypatch.setattr(cmd_npcbattle, "check_static_trainer", lambda name: check)

    cmd = cmd_npcbattle.CmdNPCBattle()
    cmd.caller = caller
    cmd.args = "Ordered Trainer"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "1. lead: Pikachu Lv8 - OK" in text
    assert "2. second: Eevee Lv6 - OK" in text
    assert text.index("1. lead: Pikachu") < text.index("2. second: Eevee")
    assert "Battle startup: should work" in text


def test_npcbattle_command_is_builder_locked():
    assert cmd_npcbattle.CmdNPCBattle.locks == "cmd:perm(Builder)"
