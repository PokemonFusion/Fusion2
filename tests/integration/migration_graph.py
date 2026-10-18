"""Validate merged migration history without opening the game database."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from django.conf import settings

settings.DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
}

import django
from django.db.backends.base.base import BaseDatabaseWrapper

_connect = BaseDatabaseWrapper.connect


def connect_memory_only(connection):
    """Allow historical Evennia import-time introspection in SQLite memory."""
    assert connection.vendor == "sqlite", connection.vendor
    assert connection.settings_dict["NAME"] == ":memory:"
    return _connect(connection)


with patch(
    "django.db.backends.base.base.BaseDatabaseWrapper.connect",
    connect_memory_only,
):
    django.setup()

    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None)
    loader.graph.validate_consistency()
    assert not loader.detect_conflicts(), loader.detect_conflicts()
    leaves = loader.graph.leaf_nodes("pokemon")
    assert len(leaves) == 1, leaves
    plan = loader.graph.forwards_plan(leaves[0])
    for name in ("0040_adventure_participation", "0041_placement_integrity_triggers"):
        assert ("pokemon", name) in plan, name
    from django.db.migrations.state import ModelState

    from pokemon.models.gym import GymVictory
    from pokemon.models.trainer import GymLeaderProfile, NPCPokemonTemplate

    state = loader.project_state()
    for model in (GymLeaderProfile, GymVictory):
        expected = ModelState.from_model(model)
        actual = state.models["pokemon", model._meta.model_name]
        assert set(actual.fields) == set(expected.fields), model.__name__
        for name in expected.fields:
            assert actual.fields[name].deconstruct()[1:] == expected.fields[name].deconstruct()[1:], name
    expected = ModelState.from_model(NPCPokemonTemplate).fields["tera_type"]
    actual = state.models["pokemon", "npcpokemontemplate"].fields["tera_type"]
    assert actual.deconstruct()[1:] == expected.deconstruct()[1:]

print("Merged migration graph is connected; only SQLite memory was used.")
