import types

from commands.admin import cmd_gymbattle
from pokemon.services.gym_leaders import GymLeaderCheck
from pokemon.services.trainer_encounters import StaticTrainerTemplateCheck


class DummyCaller:
    def __init__(self):
        self.key = "Caller"
        self.messages = []
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace()
        self.trainer = types.SimpleNamespace()
        self.location = types.SimpleNamespace(
            db=types.SimpleNamespace(battles=[]),
            ndb=types.SimpleNamespace(battle_instances={}),
        )

    def msg(self, text):
        self.messages.append(text)


def _check(**overrides):
    values = {
        "identifier": "pewter",
        "found": True,
        "name": "Brock",
        "enabled": True,
        "eligible": True,
        "league_key": "kanto",
        "gym_key": "pewter",
        "badge_key": "boulder",
        "badge_name": "Boulder Badge",
        "required_badge_count": 0,
        "badge_count": 0,
        "templates": (StaticTrainerTemplateCheck("lead", "Onix", 12, 1),),
        "issues": (),
    }
    values.update(overrides)
    return GymLeaderCheck(**values)


def test_gymbattle_command_starts_gym_leader_battle(monkeypatch):
    caller = DummyCaller()
    encounter = types.SimpleNamespace(display_name="Brock", team=[object(), object()])
    captured = {}

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            captured["checked"] = player
            return None

        def __init__(self, player):
            captured["player"] = player
            self.battle_id = 202

        def start_trainer_encounter(self, passed_encounter):
            captured["encounter"] = passed_encounter

    def fake_generate(identifier, *, player=None):
        captured["identifier"] = identifier
        captured["gym_player"] = player
        return encounter

    monkeypatch.setattr(cmd_gymbattle, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_gymbattle, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(cmd_gymbattle, "generate_gym_leader_encounter", fake_generate)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "pewter"

    cmd.func()

    assert captured["checked"] is caller
    assert captured["player"] is caller
    assert captured["identifier"] == "pewter"
    assert captured["gym_player"] is caller
    assert captured["encounter"] is encounter
    assert caller.messages[-1] == "Started gym leader battle #202 against Brock."


def test_gymbattle_command_reports_gym_error(monkeypatch):
    caller = DummyCaller()

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            return None

    def raise_error(identifier, *, player=None):
        raise cmd_gymbattle.GymLeaderError("Gym leader 'missing' was not found.")

    monkeypatch.setattr(cmd_gymbattle, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_gymbattle, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(cmd_gymbattle, "generate_gym_leader_encounter", raise_error)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "missing"

    cmd.func()

    assert caller.messages[-1] == "Gym leader 'missing' was not found."


def test_gymbattle_list_shows_enabled_leaders(monkeypatch):
    caller = DummyCaller()
    monkeypatch.setattr(
        cmd_gymbattle,
        "list_gym_leaders",
        lambda player=None, include_disabled=False: [_check()],
    )

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = ""
    cmd.switches = {"list"}

    cmd.func()

    text = caller.messages[-1]
    assert "Enabled gym leaders:" in text
    assert "pewter - Brock - Boulder Badge (boulder) - requires 0 badge(s) - 1 Pokemon - ready" in text


def test_gymbattle_list_all_shows_disabled_leaders(monkeypatch):
    caller = DummyCaller()
    captured = {}

    def fake_list(player=None, include_disabled=False):
        captured["include_disabled"] = include_disabled
        return [_check(enabled=False, eligible=True, issues=("Gym leader profile is disabled.",))]

    monkeypatch.setattr(cmd_gymbattle, "list_gym_leaders", fake_list)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = ""
    cmd.switches = {"list", "all"}

    cmd.func()

    text = caller.messages[-1]
    assert captured["include_disabled"] is True
    assert "Gym leaders:" in text
    assert "pewter - Brock - Boulder Badge (boulder) - requires 0 badge(s) - 1 Pokemon - disabled" in text


def test_gymbattle_check_reports_missing_leader(monkeypatch):
    caller = DummyCaller()
    check = GymLeaderCheck(
        identifier="missing",
        found=False,
        name="missing",
        issues=("Gym leader 'missing' was not found.",),
    )
    monkeypatch.setattr(cmd_gymbattle, "check_gym_leader", lambda identifier, player=None: check)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "missing"
    cmd.switches = {"check"}

    cmd.func()

    assert caller.messages[-1] == "Gym leader 'missing' was not found."


def test_gymbattle_check_reports_no_templates(monkeypatch):
    caller = DummyCaller()
    check = _check(
        templates=(),
        issues=("No Pokemon templates.",),
    )
    monkeypatch.setattr(cmd_gymbattle, "check_gym_leader", lambda identifier, player=None: check)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "pewter"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "Gym leader check: Brock" in text
    assert "Template Pokemon: 0" in text
    assert "Battle startup: blocked" in text
    assert "No Pokemon templates." in text


def test_gymbattle_check_reports_templates_in_order(monkeypatch):
    caller = DummyCaller()
    check = _check(
        templates=(
            StaticTrainerTemplateCheck("lead", "Geodude", 10, 1),
            StaticTrainerTemplateCheck("ace", "Onix", 12, 2),
        )
    )
    monkeypatch.setattr(cmd_gymbattle, "check_gym_leader", lambda identifier, player=None: check)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "pewter"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "1. lead: Geodude Lv10 - OK" in text
    assert "2. ace: Onix Lv12 - OK" in text
    assert text.index("1. lead: Geodude") < text.index("2. ace: Onix")
    assert "Team: Geodude Lv10, Onix Lv12" in text
    assert "Battle startup: should work" in text


def test_gymbattle_check_reports_team_size_warning(monkeypatch):
    caller = DummyCaller()
    check = _check(
        templates=tuple(
            StaticTrainerTemplateCheck(f"slot-{index}", "Pikachu", 5, index)
            for index in range(1, 8)
        ),
        warnings=("Trainer has 7 template Pokemon; battle Team storage is capped at 6.",),
    )
    monkeypatch.setattr(cmd_gymbattle, "check_gym_leader", lambda identifier, player=None: check)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "pewter"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "Template Pokemon: 7" in text
    assert "Battle startup: should work" in text
    assert "Warnings:" in text
    assert "Trainer has 7 template Pokemon; battle Team storage is capped at 6." in text


def test_gymbattle_check_reports_invalid_move_warning(monkeypatch):
    caller = DummyCaller()
    check = _check(
        templates=(
            StaticTrainerTemplateCheck(
                "lead",
                "Pikachu",
                5,
                1,
                warnings=("unknown move name(s): Definitely Fake Move",),
            ),
        ),
        warnings=("Template 1: unknown move name(s): Definitely Fake Move",),
    )
    monkeypatch.setattr(cmd_gymbattle, "check_gym_leader", lambda identifier, player=None: check)

    cmd = cmd_gymbattle.CmdGymBattle()
    cmd.caller = caller
    cmd.args = "pewter"
    cmd.switches = {"check"}

    cmd.func()

    text = caller.messages[-1]
    assert "lead: Pikachu Lv5 - OK; Warnings: unknown move name(s): Definitely Fake Move" in text
    assert "Template 1: unknown move name(s): Definitely Fake Move" in text


def test_gymbattle_command_is_builder_locked():
    assert cmd_gymbattle.CmdGymBattle.locks == "cmd:perm(Builder)"
