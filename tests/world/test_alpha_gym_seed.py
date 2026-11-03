import types
from pathlib import Path

from pokemon.services import alpha_gym_seed


class FakeRow(types.SimpleNamespace):
    def save(self, *args, **kwargs):
        self.save_calls = getattr(self, "save_calls", 0) + 1
        self.last_save_kwargs = kwargs


class FakeQS(list):
    def first(self):
        return self[0] if self else None

    def order_by(self, *fields):
        def key(row):
            values = []
            for field in fields:
                values.append(getattr(row, field.lstrip("-"), 0))
            return tuple(values)

        return FakeQS(sorted(self, key=key))


class FakeManager:
    def __init__(self):
        self.rows = []

    def filter(self, **kwargs):
        matches = []
        for row in self.rows:
            matched = True
            for key, value in kwargs.items():
                if getattr(row, key, None) is not value and getattr(row, key, None) != value:
                    matched = False
                    break
            if matched:
                matches.append(row)
        return FakeQS(matches)

    def create(self, **kwargs):
        row_id = len(self.rows) + 1
        row = FakeRow(id=row_id, pk=row_id, **kwargs)
        self.rows.append(row)
        return row


def _fake_model():
    return types.SimpleNamespace(objects=FakeManager())


def _fake_models():
    return types.SimpleNamespace(
        GymBadge=_fake_model(),
        GymLeaderProfile=_fake_model(),
        NPCPokemonTemplate=_fake_model(),
        NPCTrainer=_fake_model(),
    )


def test_seed_alpha_gym_content_creates_expected_rows(monkeypatch):
    models = _fake_models()
    monkeypatch.setattr(alpha_gym_seed, "_trainer_models", lambda: models)

    result = alpha_gym_seed.seed_alpha_gym_content()

    assert result.badge.name == "Alpha Badge"
    assert result.badge.region == "Alpha Test League"
    assert result.leader.name == "Alpha Gym Leader - Rowan"
    assert result.follower.name == "Alpha Gym Trainer - Scout Mina"
    assert result.profile.npc_trainer is result.leader
    assert result.profile.badge is result.badge
    assert result.profile.league_key == "alpha"
    assert result.profile.gym_key == "alpha_gym"
    assert result.profile.badge_key == "alpha_badge"
    assert result.profile.required_badge_count == 0
    assert result.profile.is_enabled is True
    assert [template.template_key for template in result.leader_templates] == [
        "alpha-rowan-1",
        "alpha-rowan-2",
        "alpha-rowan-3",
    ]
    assert [template.species for template in result.leader_templates] == [
        "Pikachu",
        "Bulbasaur",
        "Charmander",
    ]
    assert [template.template_key for template in result.follower_templates] == [
        "alpha-scout-mina-1",
        "alpha-scout-mina-2",
    ]
    assert [template.species for template in result.follower_templates] == [
        "Rattata",
        "Pidgey",
    ]


def test_seed_alpha_gym_content_is_idempotent(monkeypatch):
    models = _fake_models()
    monkeypatch.setattr(alpha_gym_seed, "_trainer_models", lambda: models)

    first = alpha_gym_seed.seed_alpha_gym_content()
    second = alpha_gym_seed.seed_alpha_gym_content()

    assert len(models.GymBadge.objects.rows) == 1
    assert len(models.NPCTrainer.objects.rows) == 2
    assert len(models.GymLeaderProfile.objects.rows) == 1
    assert len(models.NPCPokemonTemplate.objects.rows) == 5
    assert second.badge is first.badge
    assert second.leader is first.leader
    assert second.follower is first.follower
    assert second.profile is first.profile


def test_alpha_gym_lobby_is_in_alpha_batch_file():
    text = Path("world/alpha_gym.ev").read_text(encoding="utf-8")

    assert "batchcommands alpha_gym" in text
    assert "@teleport Alpha Test Hub" in text
    assert (
        "@dig Alpha Gym Lobby;(A)lpha (G)ym;alpha gym;gym:typeclasses.rooms.FusionRoom = "
        "(A)lpha (G)ym;alpha gym;gym;ag;south;s, (H)ub;hub;north;n"
    ) in text
    assert "@set Alpha Gym Lobby/allow_hunting = False" in text
    assert "+npcbattle/check Alpha Gym Trainer - Scout Mina" in text
    assert "+gymbattle/check alpha_gym" in text
    assert "first victory should grant Alpha Badge" in text
    assert "placed NPC interaction exists" in text
