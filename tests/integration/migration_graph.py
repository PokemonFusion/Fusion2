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

print("Merged migration graph is connected; only SQLite memory was used.")
