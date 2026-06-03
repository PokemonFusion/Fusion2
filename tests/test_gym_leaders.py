import importlib
import types

from pokemon.battle.battleinstance import BattleSession
from pokemon.services import gym_leaders
from pokemon.services.trainer_encounters import (
    StaticTrainerCheck,
    StaticTrainerTemplateCheck,
    TrainerEncounter,
)


class FakeQS(list):
    def order_by(self, *fields):
        return FakeQS(
            sorted(
                self,
                key=lambda obj: tuple(getattr(obj, field, 0) for field in fields),
            )
        )

    def select_related(self, *fields):
        return self

    def exists(self):
        return bool(self)


class FakeManager:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return FakeQS(self.rows)


class FakeBadges:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def count(self):
        return len(self.rows)

    def all(self):
        return FakeQS(self.rows)

    def filter(self, **kwargs):
        matches = []
        for row in self.rows:
            matched = True
            for key, value in kwargs.items():
                matched = str(getattr(row, key, None)) == str(value)
                if not matched:
                    break
            if matched:
                matches.append(row)
        return FakeQS(matches)

    def add(self, badge):
        if badge not in self.rows:
            self.rows.append(badge)


class FakeStorage:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value

    def get(self, key, default=None):
        return self.values.get(key, default)


def _trainer(name="Brock", id=11):
    return types.SimpleNamespace(id=id, pk=id, name=name)


def _badge(name="Boulder Badge", id=21):
    return types.SimpleNamespace(id=id, pk=id, name=name)


def _profile(
    *,
    trainer=None,
    badge=None,
    id=31,
    gym_key="pewter",
    league_key="kanto",
    badge_key="boulder",
    required_badge_count=0,
    is_enabled=True,
    sort_order=1,
):
    return types.SimpleNamespace(
        id=id,
        pk=id,
        npc_trainer=trainer or _trainer(),
        badge=badge or _badge(),
        league_key=league_key,
        gym_key=gym_key,
        badge_key=badge_key,
        required_badge_count=required_badge_count,
        is_enabled=is_enabled,
        sort_order=sort_order,
    )


def _player(badges=()):
    trainer = types.SimpleNamespace(badges=FakeBadges(badges))

    def add_badge(badge):
        trainer.badges.add(badge)

    trainer.add_badge = add_badge
    return types.SimpleNamespace(key="Player", trainer=trainer)


def _template(species="Onix", level=12, key="lead", order=1):
    return StaticTrainerTemplateCheck(key, species, level, order)


def _static_check(profile, *, templates=None, issues=()):
    return StaticTrainerCheck(
        name=profile.npc_trainer.name,
        found=True,
        templates=tuple(templates if templates is not None else (_template(),)),
        issues=tuple(issues),
    )


def _install_profiles(monkeypatch, profiles):
    monkeypatch.setattr(
        gym_leaders,
        "_gym_leader_profile_model",
        lambda: types.SimpleNamespace(objects=FakeManager(profiles)),
    )


def test_gym_leader_migration_creates_profile_model():
    migration = importlib.import_module("pokemon.migrations.0038_gym_leader_profile")

    assert any(
        getattr(operation, "name", None) == "GymLeaderProfile"
        for operation in migration.Migration.operations
    )


def test_check_gym_leader_resolves_by_name_and_gym_key(monkeypatch):
    profile = _profile()
    _install_profiles(monkeypatch, [profile])
    monkeypatch.setattr(gym_leaders, "check_static_trainer", lambda trainer: _static_check(profile))

    by_name = gym_leaders.check_gym_leader("Brock", player=_player())
    by_key = gym_leaders.check_gym_leader("pewter", player=_player())

    assert by_name.profile is profile
    assert by_key.profile is profile
    assert by_name.can_start_battle
    assert by_key.badge_name == "Boulder Badge"


def test_missing_gym_leader_reports_clean_error(monkeypatch):
    _install_profiles(monkeypatch, [])

    check = gym_leaders.check_gym_leader("missing", player=_player())

    assert not check.found
    assert "Gym leader 'missing' was not found." in check.issues
    try:
        gym_leaders.generate_gym_leader_encounter("missing", player=_player())
    except gym_leaders.GymLeaderNotFoundError as err:
        assert "missing" in str(err)
    else:
        raise AssertionError("Expected GymLeaderNotFoundError")


def test_disabled_gym_leader_blocks_startup(monkeypatch):
    profile = _profile(is_enabled=False)
    _install_profiles(monkeypatch, [profile])
    monkeypatch.setattr(gym_leaders, "check_static_trainer", lambda trainer: _static_check(profile))

    check = gym_leaders.check_gym_leader("pewter", player=_player())

    assert not check.enabled
    assert not check.can_start_battle
    try:
        gym_leaders.generate_gym_leader_encounter("pewter", player=_player())
    except gym_leaders.GymLeaderDisabledError as err:
        assert "disabled" in str(err)
    else:
        raise AssertionError("Expected GymLeaderDisabledError")


def test_missing_template_team_blocks_startup(monkeypatch):
    profile = _profile()
    _install_profiles(monkeypatch, [profile])
    monkeypatch.setattr(
        gym_leaders,
        "check_static_trainer",
        lambda trainer: _static_check(profile, templates=(), issues=("No Pokemon templates.",)),
    )

    check = gym_leaders.check_gym_leader("pewter", player=_player())

    assert check.template_count == 0
    assert not check.can_start_battle
    try:
        gym_leaders.generate_gym_leader_encounter("pewter", player=_player())
    except gym_leaders.GymLeaderTeamError as err:
        assert "No Pokemon templates." in str(err)
    else:
        raise AssertionError("Expected GymLeaderTeamError")


def test_required_badge_count_blocks_ineligible_player(monkeypatch):
    profile = _profile(required_badge_count=2)
    existing_badge = _badge(name="Stone Badge", id=99)
    _install_profiles(monkeypatch, [profile])
    monkeypatch.setattr(gym_leaders, "check_static_trainer", lambda trainer: _static_check(profile))

    check = gym_leaders.check_gym_leader("pewter", player=_player([existing_badge]))

    assert check.badge_count == 1
    assert not check.eligible
    assert "Requires at least 2 badge(s); you have 1." in check.issues
    try:
        gym_leaders.generate_gym_leader_encounter("pewter", player=_player([existing_badge]))
    except gym_leaders.GymLeaderEligibilityError as err:
        assert "Requires at least 2 badge(s)" in str(err)
    else:
        raise AssertionError("Expected GymLeaderEligibilityError")


def test_generate_gym_leader_encounter_wraps_static_team_metadata(monkeypatch):
    profile = _profile()
    lead = types.SimpleNamespace(name="Geodude")
    reserve = types.SimpleNamespace(name="Onix")
    static_encounter = TrainerEncounter(
        display_name="Brock",
        trainer_class="NPC Trainer",
        source_type="static",
        battle_format="single",
        ai_profile="basic",
        team=[lead, reserve],
        intro_text="Brock challenges you!",
        metadata={"npc_trainer_id": profile.npc_trainer.id},
    )
    _install_profiles(monkeypatch, [profile])
    monkeypatch.setattr(gym_leaders, "check_static_trainer", lambda trainer: _static_check(profile))
    monkeypatch.setattr(
        gym_leaders,
        "generate_static_trainer_encounter",
        lambda trainer: static_encounter,
    )

    encounter = gym_leaders.generate_gym_leader_encounter("pewter", player=_player())

    assert encounter.source_type == "gym_leader"
    assert encounter.team == [lead, reserve]
    assert encounter.metadata["gym_leader_profile_id"] == profile.id
    assert encounter.metadata["npc_trainer_id"] == profile.npc_trainer.id
    assert encounter.metadata["league_key"] == "kanto"
    assert encounter.metadata["gym_key"] == "pewter"
    assert encounter.metadata["badge_id"] == profile.badge.id
    assert encounter.metadata["badge_key"] == "boulder"


def test_grant_gym_badge_for_victory_awards_once(monkeypatch):
    badge = _badge()
    profile = _profile(badge=badge)
    player = _player()
    metadata = gym_leaders._profile_metadata(profile)
    _install_profiles(monkeypatch, [profile])

    first = gym_leaders.grant_gym_badge_for_victory(player, metadata)
    second = gym_leaders.grant_gym_badge_for_victory(player, metadata)

    assert first.awarded
    assert not first.already_had
    assert second.already_had
    assert not second.awarded
    assert player.trainer.badges.rows == [badge]


def test_grant_gym_badge_ignores_non_gym_metadata(monkeypatch):
    badge = _badge()
    profile = _profile(badge=badge)
    player = _player()
    _install_profiles(monkeypatch, [profile])

    result = gym_leaders.grant_gym_badge_for_victory(
        player,
        {"source_type": "static", "gym_key": profile.gym_key},
    )

    assert result is None
    assert player.trainer.badges.rows == []


def test_battle_result_hook_grants_gym_badge_once(monkeypatch):
    player = _player()
    metadata = {"source_type": "gym_leader", "gym_key": "pewter"}
    calls = []

    def fake_grant(passed_player, passed_metadata):
        calls.append((passed_player, passed_metadata))
        return gym_leaders.GymBadgeGrantResult(
            awarded=True,
            already_had=False,
            badge_name="Boulder Badge",
            message="You earned the Boulder Badge!",
        )

    monkeypatch.setattr(gym_leaders, "grant_gym_badge_for_victory", fake_grant)
    session = BattleSession.__new__(BattleSession)
    session.teamA = [player]
    session.teamB = []
    session.trainers = [player]
    session.observers = set()
    session.encounter_metadata = metadata
    session._battle_result_handled = False
    session.storage = FakeStorage()
    messages = []
    session.msg = messages.append
    winner = types.SimpleNamespace(team="A", player=player)

    session._handle_battle_result(winner)
    session._handle_battle_result(winner)

    assert calls == [(player, metadata)]
    assert messages == ["You earned the Boulder Badge!"]
    assert session.storage.values["battle_result"] == {"handled": True}


def test_battle_result_hook_does_not_grant_on_loss(monkeypatch):
    player = _player()
    calls = []
    monkeypatch.setattr(
        gym_leaders,
        "grant_gym_badge_for_victory",
        lambda passed_player, metadata: calls.append((passed_player, metadata)),
    )
    session = BattleSession.__new__(BattleSession)
    session.teamA = [player]
    session.teamB = []
    session.trainers = [player]
    session.observers = set()
    session.encounter_metadata = {"source_type": "gym_leader", "gym_key": "pewter"}
    session._battle_result_handled = False
    session.storage = FakeStorage()
    session.msg = lambda text: None
    winner = types.SimpleNamespace(team="B", player=None)

    session._handle_battle_result(winner)

    assert calls == []
