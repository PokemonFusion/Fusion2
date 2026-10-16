"""Test production gym rewards in SQLite memory; never open the game database."""

import importlib
import importlib.machinery
import sys
import types
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.apps import AppConfig
from django.conf import settings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for name, path in (
    ("pokemon", ROOT / "pokemon"),
    ("pokemon.models", ROOT / "pokemon" / "models"),
    ("objects", ROOT), ("objects.models", ROOT),
    ("evennia", ROOT), ("evennia.objects", ROOT), ("evennia.objects.models", ROOT),
):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    sys.modules[name] = module


class TestPokemonConfig(AppConfig):
    """Load the production badge, trainer, and victory models only."""

    name = "pokemon"
    path = str(ROOT / "pokemon")
    default_auto_field = "django.db.models.BigAutoField"


class TestObjectsConfig(AppConfig):
    """Provide the character foreign key without booting Evennia."""

    name = "objects"
    path = str(ROOT)


settings.configure(
    INSTALLED_APPS=["__main__.TestPokemonConfig", "__main__.TestObjectsConfig"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    USE_TZ=True,
    SECRET_KEY="isolated-gym-test",
)

import django

django.setup()

from django.db import connection, models
from django.db.migrations.state import ModelState, ProjectState


class ObjectDB(models.Model):
    """Minimal character identity for the real Trainer and GymVictory models."""

    key = models.CharField(max_length=80)

    class Meta:
        app_label = "objects"


class SpeciesEntry(models.Model):
    """Provide Trainer's unrelated seen-species relation."""

    name = models.CharField(max_length=80)

    class Meta:
        app_label = "pokemon"


sys.modules["evennia.objects.models"].ObjectDB = ObjectDB
core = types.ModuleType("pokemon.models.core")
core.SpeciesEntry = SpeciesEntry
sys.modules["pokemon.models.core"] = core

from pokemon.models.gym import GymVictory
from pokemon.models.trainer import GymBadge, Trainer
from pokemon.services.gym_rewards import GymVictoryRewards

# Compare migration state without applying a migration to any database.
migration = importlib.import_module("pokemon.migrations.0043_gym_victory").Migration
assert migration.dependencies == [("pokemon", "0042_merge_adventure_placement")]
state = ProjectState()
for operation in migration.operations:
    operation.state_forwards("pokemon", state)
expected = ModelState.from_model(GymVictory)
actual = state.models["pokemon", "gymvictory"]
assert set(actual.fields) == set(expected.fields)
for name in expected.fields:
    assert actual.fields[name].deconstruct()[1:] == expected.fields[name].deconstruct()[1:], name
assert actual.options["ordering"] == expected.options["ordering"]
assert [index.deconstruct() for index in actual.options["indexes"]] == [
    index.deconstruct() for index in expected.options["indexes"]
]

with connection.schema_editor() as editor:
    for model in (ObjectDB, SpeciesEntry, GymBadge, Trainer, GymVictory):
        editor.create_model(model)

player = ObjectDB.objects.create(key="Player A")
other = ObjectDB.objects.create(key="Player B")
trainer = Trainer.objects.create(user=player, trainer_number=1)
other_trainer = Trainer.objects.create(user=other, trainer_number=2)
badge = GymBadge.objects.create(name="Original Badge", region="Test")
replacement = GymBadge.objects.create(name="Replacement Badge", region="Test")
metadata = {"source_type": "gym_leader", "badge_id": badge.pk, "gym_key": "test_gym"}
victory_id = uuid4()
rewards = GymVictoryRewards(player)
victory = rewards.record(victory_id, metadata)
assert rewards.record(victory_id, {**metadata, "badge_id": replacement.pk}).metadata == metadata
assert GymVictory.objects.count() == 1

original_add = Trainer.add_badge


def fail_after_badge_write(self, award):
    """Fail after the real many-to-many write so rollback must remove it."""
    original_add(self, award)
    raise RuntimeError("delivery interrupted after badge write")


with patch.object(Trainer, "add_badge", fail_after_badge_write):
    results = rewards.claim_pending()
    assert len(results) == 1 and not results[0].completed
assert trainer.badges.count() == 0
victory.refresh_from_db()
assert victory.claimed_at is None

original_save = GymVictory.save


def fail_claim_marker(self, *args, **kwargs):
    """The claim-marker failure must also roll back a successful badge write."""
    if "claimed_at" in kwargs.get("update_fields", ()):
        raise RuntimeError("claim marker unavailable")
    return original_save(self, *args, **kwargs)


with patch.object(GymVictory, "save", fail_claim_marker):
    assert not rewards.claim_pending()[0].completed
assert trainer.badges.count() == 0
victory.refresh_from_db()
assert victory.claimed_at is None

assert GymVictoryRewards(other).claim_pending() == ()
try:
    GymVictoryRewards(other).claim(victory_id)
except GymVictory.DoesNotExist:
    pass
else:
    raise AssertionError("another character claimed this victory")
try:
    GymVictoryRewards(other).record(victory_id, metadata)
except ValueError:
    pass
else:
    raise AssertionError("another character replaced this victory")
assert other_trainer.badges.count() == 0

# A fresh character instance models reconnect with no battle or cached service.
reconnected = GymVictoryRewards(ObjectDB.objects.get(pk=player.pk))
assert reconnected.claim(victory_id).awarded
assert not reconnected.claim(victory_id).awarded
assert reconnected.claim_pending() == ()
assert list(trainer.badges.values_list("pk", flat=True)) == [badge.pk]
assert not trainer.badges.filter(pk=replacement.pk).exists()
victory.refresh_from_db()
claimed_at = victory.claimed_at
assert claimed_at is not None
reconnected.record(victory_id, metadata)
victory.refresh_from_db()
assert victory.claimed_at == claimed_at

rematch_id = uuid4()
reconnected.record(rematch_id, metadata)
assert reconnected.claim(rematch_id).completed
assert trainer.badges.count() == 1

# One unresolved award must not prevent a different pending badge being claimed.
missing_badge_id = uuid4()
reconnected.record(missing_badge_id, {**metadata, "badge_id": 99999})
new_badge_id = uuid4()
reconnected.record(new_badge_id, {**metadata, "badge_id": replacement.pk})
results = reconnected.claim_pending()
assert len(results) == 2
assert sum(result.completed for result in results) == 1
assert GymVictory.objects.get(pk=missing_badge_id).claimed_at is None
assert trainer.badges.count() == 2

# Missing progression records remain recoverable once the trainer is repaired.
fresh = ObjectDB.objects.create(key="Missing trainer")
fresh_rewards = GymVictoryRewards(fresh)
fresh_id = uuid4()
fresh_rewards.record(fresh_id, metadata)
assert not fresh_rewards.claim(fresh_id).completed
Trainer.objects.create(user=fresh, trainer_number=3)
assert GymVictoryRewards(ObjectDB.objects.get(pk=fresh.pk)).claim(fresh_id).awarded

print("Gym recovery ORM checks passed")
