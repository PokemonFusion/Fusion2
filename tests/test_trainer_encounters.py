"""Tests for trainer encounter Pokémon generation."""

from __future__ import annotations

import random
import types

import pytest

from pokemon.battle import pokemon_factory


@pytest.fixture(autouse=True)
def restore_factory(monkeypatch):
        """Ensure ``TRAINER_ENCOUNTERS`` is restored after each test."""

        original_table = pokemon_factory.TRAINER_ENCOUNTERS
        yield
        monkeypatch.setattr(pokemon_factory, "TRAINER_ENCOUNTERS", original_table, raising=False)


def test_generate_trainer_pokemon_uses_custom_roster(monkeypatch):
        """The generator should draw from a trainer-specific roster when provided."""

        calls = {}

        def fake_create(species, level, trainer=None, is_wild=False):
                calls.update({
                        "species": species,
                        "level": level,
                        "trainer": trainer,
                        "is_wild": is_wild,
                })
                return types.SimpleNamespace(name=species, level=level)

        roster = [
                {"species": "Magnemite", "min_level": 10, "max_level": 10, "weight": 1},
                {"species": "Voltorb", "min_level": 9, "max_level": 11, "weight": 1},
        ]

        monkeypatch.setattr(pokemon_factory, "create_battle_pokemon", fake_create)
        monkeypatch.setattr(pokemon_factory, "TRAINER_ENCOUNTERS", {"default": []}, raising=False)

        trainer = types.SimpleNamespace(id=42)
        rng = random.Random(5)

        mon = pokemon_factory.generate_trainer_pokemon(
                trainer,
                context={"roster": roster},
                rng=rng,
        )

        assert mon.name == "Voltorb"
        assert mon.level == 11
        assert calls["is_wild"] is False
        assert getattr(mon, "trainer_id") == 42
        assert getattr(mon, "trainer_identifier") == 42


def test_generate_trainer_pokemon_respects_location_archetype(monkeypatch):
        """Location and archetype hints should select matching encounter data."""

        def fake_create(species, level, trainer=None, is_wild=False):
                return types.SimpleNamespace(name=species, level=level)

        table = {
                "default": [{"species": "Fallback", "min_level": 1, "max_level": 1, "weight": 1}],
                "locations": {
                        "tower": [{"species": "Gastly", "min_level": 10, "max_level": 10, "weight": 1}],
                },
                "archetypes": {
                        "hex_maniac": [{"species": "Misdreavus", "min_level": 12, "max_level": 12, "weight": 1}],
                },
                "pairs": {
                        ("tower", "hex_maniac"): [
                                {"species": "Haunter", "min_level": 15, "max_level": 17, "weight": 1}
                        ]
                },
        }

        monkeypatch.setattr(pokemon_factory, "create_battle_pokemon", fake_create)
        monkeypatch.setattr(pokemon_factory, "TRAINER_ENCOUNTERS", table, raising=False)

        rng = random.Random(7)
        context = {"location": "Tower", "archetype": "Hex Maniac"}

        mon = pokemon_factory.generate_trainer_pokemon(context=context, rng=rng)

        assert mon.name == "Haunter"
        assert mon.level == 15
        assert getattr(mon, "trainer_identifier") == "tower:hex_maniac:haunter"
        assert getattr(mon, "is_wild") is False
