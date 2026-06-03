import random
import types

from pokemon.battle import pokemon_factory
from pokemon.services import trainer_encounters


def _room(**attrs):
    return types.SimpleNamespace(db=types.SimpleNamespace(**attrs))


def _stub_factory(monkeypatch):
    calls = []

    def fake_create_battle_pokemon(
        species,
        level,
        *,
        trainer=None,
        is_wild=False,
        template_key="",
        move_names=None,
    ):
        calls.append(
            {
                "species": species,
                "level": level,
                "trainer": trainer,
                "is_wild": is_wild,
                "template_key": template_key,
                "move_names": move_names,
            }
        )
        return types.SimpleNamespace(
            name=species,
            level=level,
            model_id=f"encounter:{species}:{level}",
            move_names=list(move_names or []),
        )

    monkeypatch.setattr(trainer_encounters, "_create_battle_pokemon", fake_create_battle_pokemon)
    return calls


class FakeQS(list):
    def order_by(self, *fields):
        return FakeQS(
            sorted(
                self,
                key=lambda obj: tuple(getattr(obj, field, 0) for field in fields),
            )
        )

    def first(self):
        return self[0] if self else None


class FakeManager:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return FakeQS(self.rows)

    def filter(self, **kwargs):
        matches = []
        for row in self.rows:
            matched = True
            for key, value in kwargs.items():
                if key.endswith("__iexact"):
                    attr = key.removesuffix("__iexact")
                    matched = str(getattr(row, attr, "")).lower() == str(value).lower()
                else:
                    matched = getattr(row, key, None) is value or getattr(row, key, None) == value
                if not matched:
                    break
            if matched:
                matches.append(row)
        return FakeQS(matches)


def test_random_trainer_encounter_uses_npc_trainer_chart(monkeypatch):
    calls = _stub_factory(monkeypatch)
    room = _room(
        npc_trainer_chart=[
            {
                "trainer_class": "Hiker",
                "trainer_name": "Hiker Rowan",
                "species": "Geodude",
                "min_level": 7,
                "max_level": 7,
                "move_names": ["Tackle"],
                "ai_profile": "basic",
                "source_type": "random",
                "reward_profile": {"money": "default"},
                "ruleset": {"format": "single"},
            }
        ]
    )

    encounter = trainer_encounters.generate_random_trainer_encounter(room, rng=random.Random(1))

    assert encounter.display_name == "Hiker Rowan"
    assert encounter.trainer_class == "Hiker"
    assert encounter.source_type == "random"
    assert encounter.ai_profile == "basic"
    assert encounter.reward_profile == {"money": "default"}
    assert encounter.ruleset == {"format": "single"}
    assert encounter.team[0].name == "Geodude"
    assert encounter.intro_text == "Hiker Rowan challenges you with Geodude!"
    assert calls == [
        {
            "species": "Geodude",
            "level": 7,
            "trainer": None,
            "is_wild": False,
            "template_key": "random",
            "move_names": ["Tackle"],
        }
    ]


def test_random_trainer_encounter_derives_from_hunt_chart(monkeypatch):
    calls = _stub_factory(monkeypatch)
    room = _room(
        hunt_chart=[
            {
                "name": "Pidgey",
                "rarity": "rare",
                "tiers": ["T2"],
            }
        ]
    )

    encounter = trainer_encounters.generate_random_trainer_encounter(room, rng=random.Random(2))

    assert encounter.team[0].name == "Pidgey"
    assert 10 <= encounter.team[0].level <= 25
    assert calls[0]["trainer"] is None
    assert calls[0]["is_wild"] is False


def test_random_trainer_encounter_can_build_more_than_one_team_member(monkeypatch):
    _stub_factory(monkeypatch)
    room = _room(
        npc_trainer_chart=[
            {
                "trainer_class": "Duo",
                "trainer_name": "Duo Lane",
                "team": [
                    {"species": "Rattata", "level": 5},
                    {"species": "Pidgey", "level": 6},
                ],
            }
        ]
    )

    encounter = trainer_encounters.generate_random_trainer_encounter(room, rng=random.Random(3))

    assert encounter.display_name == "Duo Lane"
    assert [poke.name for poke in encounter.team] == ["Rattata", "Pidgey"]
    assert [poke.level for poke in encounter.team] == [5, 6]


def test_random_trainer_fallback_is_not_fixed_charmander(monkeypatch):
    _stub_factory(monkeypatch)

    seen = {
        trainer_encounters.generate_random_trainer_encounter(rng=random.Random(seed)).team[0].name
        for seed in range(20)
    }

    assert "Charmander" not in seen
    assert seen <= {"Rattata", "Pidgey", "Caterpie"}
    assert len(seen) > 1


def test_generate_trainer_pokemon_compatibility_wrapper(monkeypatch):
    lead = types.SimpleNamespace(name="Rattata", level=5)
    captured = {}

    def fake_generate_random_trainer_encounter(*, display_name=None):
        captured["display_name"] = display_name
        return types.SimpleNamespace(team=[lead])

    monkeypatch.setattr(
        trainer_encounters,
        "generate_random_trainer_encounter",
        fake_generate_random_trainer_encounter,
    )

    assert pokemon_factory.generate_trainer_pokemon("Trainer Casey") is lead
    assert captured["display_name"] == "Trainer Casey"


def test_static_trainer_encounter_copies_templates(monkeypatch):
    trainer = types.SimpleNamespace(id=22, name="Test Trainer", trainer_class="Rival")
    template = types.SimpleNamespace(
        id=7,
        npc_trainer=trainer,
        template_key="lead",
        species="Pikachu",
        level=8,
        ability="Static",
        nature="Hardy",
        gender="F",
        ivs=[1, 2, 3, 4, 5, 6],
        evs=[0, 0, 0, 0, 0, 0],
        held_item="Berry",
        move_names=["Thunder Shock", "Quick Attack"],
        sort_order=1,
    )
    before = dict(template.__dict__)
    created = []

    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([trainer])),
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_template_model",
        lambda: types.SimpleNamespace(objects=FakeManager([template])),
    )

    def fake_create_encounter_pokemon(**kwargs):
        created.append(kwargs)
        return types.SimpleNamespace(encounter_id="copy-1")

    monkeypatch.setattr(trainer_encounters, "_create_encounter_pokemon", fake_create_encounter_pokemon)
    monkeypatch.setattr(trainer_encounters, "_encounter_ref", lambda encounter: f"encounter:{encounter.encounter_id}")

    encounter = trainer_encounters.generate_static_trainer_encounter("test trainer")

    assert encounter.display_name == "Test Trainer"
    assert encounter.trainer_class == "Rival"
    assert encounter.source_type == "static"
    assert encounter.ai_profile == "basic"
    assert encounter.team[0] is not template
    assert encounter.team[0].name == "Pikachu"
    assert encounter.team[0].level == 8
    assert [move.name for move in encounter.team[0].moves] == ["Thunder Shock", "Quick Attack"]
    assert encounter.team[0].model_id == "encounter:copy-1"
    assert template.__dict__ == before
    assert created[0]["npc_trainer"] is trainer
    assert created[0]["species"] == "Pikachu"
    assert created[0]["level"] == 8
    assert created[0]["move_names"] == ["Thunder Shock", "Quick Attack"]
    assert created[0]["template_key"] == "lead"


def test_static_trainer_missing_name_raises_clean_error(monkeypatch):
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([])),
    )

    try:
        trainer_encounters.generate_static_trainer_encounter("Unknown Trainer")
    except trainer_encounters.StaticTrainerNotFoundError as err:
        assert "Unknown Trainer" in str(err)
    else:
        raise AssertionError("Expected StaticTrainerNotFoundError")


def test_static_trainer_without_templates_raises_clean_error(monkeypatch):
    trainer = types.SimpleNamespace(id=23, name="Empty Trainer")
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([trainer])),
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_template_model",
        lambda: types.SimpleNamespace(objects=FakeManager([])),
    )

    try:
        trainer_encounters.generate_static_trainer_encounter("Empty Trainer")
    except trainer_encounters.StaticTrainerTeamError as err:
        assert "no Pokemon templates" in str(err)
    else:
        raise AssertionError("Expected StaticTrainerTeamError")


def test_list_static_trainers_with_templates_returns_only_trainers_with_templates(monkeypatch):
    usable = types.SimpleNamespace(id=31, name="Usable Trainer")
    empty = types.SimpleNamespace(id=32, name="Empty Trainer")
    template = types.SimpleNamespace(
        id=9,
        npc_trainer=usable,
        template_key="lead",
        species="Eevee",
        level=5,
        move_names=["Tackle"],
        sort_order=1,
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([empty, usable])),
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_template_model",
        lambda: types.SimpleNamespace(objects=FakeManager([template])),
    )

    checks = trainer_encounters.list_static_trainers_with_templates()

    assert [check.name for check in checks] == ["Usable Trainer"]
    assert checks[0].template_count == 1
    assert checks[0].templates[0].species == "Eevee"


def test_static_trainer_check_warns_when_team_exceeds_six(monkeypatch):
    trainer = types.SimpleNamespace(id=41, name="Crowded Trainer")
    templates = [
        types.SimpleNamespace(
            id=index,
            npc_trainer=trainer,
            template_key=f"slot-{index}",
            species="Pikachu",
            level=5,
            move_names=["Tackle"],
            sort_order=index,
        )
        for index in range(1, 8)
    ]
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([trainer])),
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_template_model",
        lambda: types.SimpleNamespace(objects=FakeManager(templates)),
    )
    monkeypatch.setattr(trainer_encounters, "_move_exists", lambda move_name: True)

    check = trainer_encounters.check_static_trainer("Crowded Trainer")

    assert check.template_count == 7
    assert check.can_start_battle
    assert check.warnings == (
        "Trainer has 7 template Pokemon; battle Team storage is capped at 6.",
    )


def test_static_trainer_check_warns_about_unknown_move_names(monkeypatch):
    trainer = types.SimpleNamespace(id=42, name="Move Warning Trainer")
    template = types.SimpleNamespace(
        id=1,
        npc_trainer=trainer,
        template_key="lead",
        species="Pikachu",
        level=5,
        move_names=["Tackle", "Definitely Fake Move"],
        sort_order=1,
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_trainer_model",
        lambda: types.SimpleNamespace(objects=FakeManager([trainer])),
    )
    monkeypatch.setattr(
        trainer_encounters,
        "_npc_template_model",
        lambda: types.SimpleNamespace(objects=FakeManager([template])),
    )
    monkeypatch.setattr(trainer_encounters, "_move_exists", lambda move_name: move_name == "Tackle")

    check = trainer_encounters.check_static_trainer("Move Warning Trainer")

    assert check.can_start_battle
    assert check.templates[0].warnings == ("unknown move name(s): Definitely Fake Move",)
    assert check.warnings == ("Template 1: unknown move name(s): Definitely Fake Move",)
