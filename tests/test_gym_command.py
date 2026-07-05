import types
from pathlib import Path

from commands.player import cmd_gym
from pokemon.services import gym_leaders
from pokemon.services.gym_leaders import GymLeaderCheck
from pokemon.services.trainer_encounters import StaticTrainerTemplateCheck


class DummyCaller:
    def __init__(self):
        self.key = "Caller"
        self.messages = []
        self.trainer = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.db = types.SimpleNamespace()

    def msg(self, text):
        self.messages.append(text)


def _check(**overrides):
    values = {
        "identifier": "alpha_gym",
        "found": True,
        "name": "Alpha Gym Leader - Rowan",
        "enabled": True,
        "eligible": True,
        "league_key": "alpha",
        "gym_key": "alpha_gym",
        "badge_key": "alpha_badge",
        "badge_name": "Alpha Badge",
        "required_badge_count": 0,
        "badge_count": 0,
        "has_badge": False,
        "templates": (
            StaticTrainerTemplateCheck("alpha-rowan-1", "Pikachu", 8, 1),
        ),
        "issues": (),
        "warnings": (),
    }
    values.update(overrides)
    return GymLeaderCheck(**values)


def _run_command(args, caller=None):
    caller = caller or DummyCaller()
    cmd = cmd_gym.CmdGym()
    cmd.caller = caller
    cmd.args = args
    cmd.func()
    return caller


def test_gym_command_is_registered_in_pokemon_core_cmdset():
    text = Path("commands/cmdsets/pokemon_core.py").read_text(encoding="utf-8")

    assert "from commands.player.cmd_gym import CmdGym" in text
    assert "CmdGym," in text


def test_gym_list_shows_enabled_player_visible_gyms(monkeypatch):
    captured = {}

    def fake_list(player=None, include_disabled=False):
        captured["player"] = player
        captured["include_disabled"] = include_disabled
        return [
            _check(),
            _check(gym_key="disabled_gym", enabled=False, name="Disabled Leader"),
        ]

    monkeypatch.setattr(cmd_gym, "list_gym_leaders", fake_list)

    caller = _run_command("list")

    text = caller.messages[-1]
    assert captured["player"] is caller
    assert captured["include_disabled"] is False
    assert "Available gyms:" in text
    assert "alpha_gym | Leader: Alpha Gym Leader - Rowan" in text
    assert "Requires: 0 badge(s)" in text
    assert "Qualifies: yes" in text
    assert "Badge earned: no" in text
    assert "disabled_gym" not in text


def test_gym_check_reports_eligibility_and_badge_status(monkeypatch):
    monkeypatch.setattr(
        cmd_gym,
        "check_gym_leader",
        lambda identifier, player=None: _check(
            required_badge_count=1,
            badge_count=1,
            has_badge=True,
        ),
    )

    caller = _run_command("check alpha_gym")

    text = caller.messages[-1]
    assert "Gym: alpha_gym" in text
    assert "Leader: Alpha Gym Leader - Rowan" in text
    assert "Badge awarded: Alpha Badge" in text
    assert "Required badges: 1" in text
    assert "Your badges: 1" in text
    assert "Qualifies: yes" in text
    assert "Already earned: yes" in text
    assert "No additional badge will be awarded." in text


def test_gym_challenge_starts_existing_gym_service_encounter(monkeypatch):
    caller = DummyCaller()
    encounter = types.SimpleNamespace(display_name="Alpha Gym Leader - Rowan")
    captured = {}

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            captured["checked_battle"] = player
            return None

        def __init__(self, player):
            captured["session_player"] = player
            self.battle_id = 303

        def start_trainer_encounter(self, passed_encounter):
            captured["encounter"] = passed_encounter

    def fake_generate(identifier, *, player=None):
        captured["identifier"] = identifier
        captured["generate_player"] = player
        return encounter

    monkeypatch.setattr(cmd_gym, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_gym, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(cmd_gym, "check_gym_leader", lambda identifier, player=None: _check())
    monkeypatch.setattr(cmd_gym, "generate_gym_leader_encounter", fake_generate)

    _run_command("challenge alpha_gym", caller=caller)

    assert captured["checked_battle"] is caller
    assert captured["session_player"] is caller
    assert captured["identifier"] == "alpha_gym"
    assert captured["generate_player"] is caller
    assert captured["encounter"] is encounter
    assert caller.messages[-1] == "Started gym challenge #303 against Alpha Gym Leader - Rowan."


def test_gym_challenge_blocks_badge_requirement_failure(monkeypatch):
    monkeypatch.setattr(cmd_gym, "BattleSession", _not_in_battle_session())
    monkeypatch.setattr(cmd_gym, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(
        cmd_gym,
        "check_gym_leader",
        lambda identifier, player=None: _check(
            eligible=False,
            required_badge_count=2,
            badge_count=1,
            issues=("Requires at least 2 badge(s); you have 1.",),
        ),
    )
    monkeypatch.setattr(
        cmd_gym,
        "generate_gym_leader_encounter",
        lambda identifier, player=None: (_ for _ in ()).throw(AssertionError("should not generate")),
    )

    caller = _run_command("challenge alpha_gym")

    assert caller.messages[-1] == "Requires at least 2 badge(s); you have 1."


def test_gym_challenge_hides_disabled_gym(monkeypatch):
    monkeypatch.setattr(cmd_gym, "BattleSession", _not_in_battle_session())
    monkeypatch.setattr(cmd_gym, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(
        cmd_gym,
        "check_gym_leader",
        lambda identifier, player=None: _check(
            enabled=False,
            issues=("Gym leader profile is disabled.",),
        ),
    )

    caller = _run_command("challenge alpha_gym")

    assert caller.messages[-1] == (
        "Gym 'alpha_gym' is not available right now. Use +gym list to see available gyms."
    )


def test_gym_challenge_blocks_missing_required_configuration(monkeypatch):
    monkeypatch.setattr(cmd_gym, "BattleSession", _not_in_battle_session())
    monkeypatch.setattr(cmd_gym, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(
        cmd_gym,
        "check_gym_leader",
        lambda identifier, player=None: _check(
            templates=(),
            issues=("No Pokemon templates.",),
        ),
    )
    monkeypatch.setattr(
        cmd_gym,
        "generate_gym_leader_encounter",
        lambda identifier, player=None: (_ for _ in ()).throw(AssertionError("should not generate")),
    )

    caller = _run_command("challenge alpha_gym")

    assert caller.messages[-1] == "That gym is not ready for challenges yet: No Pokemon templates."


def test_gym_challenge_blocks_when_already_in_battle(monkeypatch):
    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            return object()

    monkeypatch.setattr(cmd_gym, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(
        cmd_gym,
        "has_usable_pokemon",
        lambda player: (_ for _ in ()).throw(AssertionError("should not check party")),
    )

    caller = _run_command("challenge alpha_gym")

    assert caller.messages[-1] == "You are already in a battle."


def test_gym_challenge_allows_rematch_after_badge_earned(monkeypatch):
    caller = DummyCaller()
    encounter = types.SimpleNamespace(display_name="Alpha Gym Leader - Rowan")

    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            return None

        def __init__(self, player):
            self.battle_id = 404

        def start_trainer_encounter(self, passed_encounter):
            self.encounter = passed_encounter

    monkeypatch.setattr(cmd_gym, "BattleSession", FakeBattleSession)
    monkeypatch.setattr(cmd_gym, "has_usable_pokemon", lambda player: True)
    monkeypatch.setattr(
        cmd_gym,
        "check_gym_leader",
        lambda identifier, player=None: _check(has_badge=True),
    )
    monkeypatch.setattr(
        cmd_gym,
        "generate_gym_leader_encounter",
        lambda identifier, player=None: encounter,
    )

    _run_command("challenge alpha_gym", caller=caller)

    assert caller.messages[0] == (
        "You already have the Alpha Badge. This rematch will not award another badge."
    )
    assert caller.messages[-1] == "Started gym challenge #404 against Alpha Gym Leader - Rowan."


def test_gym_badge_award_service_awards_once_for_rematches(monkeypatch):
    badge = types.SimpleNamespace(id=21, pk=21, name="Alpha Badge")
    profile = types.SimpleNamespace(
        id=31,
        pk=31,
        npc_trainer=types.SimpleNamespace(id=41, pk=41, name="Alpha Gym Leader - Rowan"),
        badge=badge,
        league_key="alpha",
        gym_key="alpha_gym",
        badge_key="alpha_badge",
        required_badge_count=0,
        is_enabled=True,
    )
    player = types.SimpleNamespace(trainer=types.SimpleNamespace(badges=FakeBadges()))
    monkeypatch.setattr(gym_leaders, "_all_profiles", lambda: [profile])

    first = gym_leaders.grant_gym_badge_for_victory(
        player,
        {"source_type": "gym_leader", "gym_key": "alpha_gym"},
    )
    second = gym_leaders.grant_gym_badge_for_victory(
        player,
        {"source_type": "gym_leader", "gym_key": "alpha_gym"},
    )

    assert first.awarded
    assert not first.already_had
    assert second.already_had
    assert not second.awarded
    assert player.trainer.badges.rows == [badge]


def _not_in_battle_session():
    class FakeBattleSession:
        @staticmethod
        def ensure_for_player(player):
            return None

    return FakeBattleSession


class FakeBadges:
    def __init__(self):
        self.rows = []

    def all(self):
        return list(self.rows)

    def add(self, badge):
        if badge not in self.rows:
            self.rows.append(badge)
