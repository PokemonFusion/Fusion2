"""Isolated in-memory ORM smoke test; never connects to the game database."""

import importlib.machinery
import sys
import types
from pathlib import Path
from unittest.mock import patch

from django.apps import AppConfig
from django.conf import settings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Import the real Adventure models without initializing unrelated game models.
for name, path in (
    ("pokemon", ROOT / "pokemon"),
    ("pokemon.models", ROOT / "pokemon" / "models"),
    ("objects", ROOT),
    ("objects.models", ROOT),
    ("evennia", ROOT),
    ("evennia.objects", ROOT),
    ("evennia.objects.models", ROOT),
):
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    sys.modules[name] = module


class TestPokemonConfig(AppConfig):
    """Register only the production Adventure models in this subprocess."""

    name = "pokemon"
    path = str(ROOT / "pokemon")


class TestObjectsConfig(AppConfig):
    """Provide the character foreign-key target without starting Evennia."""

    name = "objects"
    path = str(ROOT)


settings.configure(
    INSTALLED_APPS=["__main__.TestPokemonConfig", "__main__.TestObjectsConfig"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    USE_TZ=True,
    SECRET_KEY="isolated-adventure-test",
)

import django

django.setup()

from django.db import connection, models
from django.utils import timezone


class ObjectDB(models.Model):
    """Minimal character table for production Adventure foreign keys."""

    key = models.CharField(max_length=80)

    class Meta:
        app_label = "objects"

    @property
    def trainer(self):
        """Return a database-backed inventory delivery endpoint."""

        return InventoryDelivery(self)


class Inventory(models.Model):
    """Database-backed inventory quantity used to prove transaction rollback."""

    owner = models.OneToOneField(ObjectDB, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    class Meta:
        app_label = "objects"


class InventoryDelivery:
    """Simulate a delivery failure after its inventory write has succeeded."""

    fail_after_write = False

    def __init__(self, player):
        self.player = player

    def add_item(self, item, amount):
        """Perform a real write so a failed claim must roll it back."""

        assert item == "Potion"
        entry, _created = Inventory.objects.get_or_create(owner=self.player)
        entry.quantity += amount
        entry.save()
        if self.fail_after_write:
            raise RuntimeError("delivery interrupted after inventory write")


sys.modules["evennia.objects.models"].ObjectDB = ObjectDB

from pokemon.adventures import progress, sessions
from pokemon.models.adventures import AdventureParticipation, AdventureSession

with connection.schema_editor() as editor:
    for model in (ObjectDB, Inventory, AdventureSession, AdventureParticipation):
        editor.create_model(model)

player = ObjectDB.objects.create(key="First player")
completed = AdventureSession.objects.create(
    leader=player, template_key="alpha_meadow", current_node="entrance",
    state="completed", completed_at=timezone.now(),
)

InventoryDelivery.fail_after_write = True
assert not progress.finalize_completion(completed)[0]
assert not Inventory.objects.filter(owner=player).exists()
participation = AdventureParticipation.objects.get(session=completed)
assert participation.reward_item == "Potion"
assert participation.reward_claimed_at is None
InventoryDelivery.fail_after_write = False

original_save = AdventureParticipation.save


def fail_claim_marker(self, *args, **kwargs):
    """Fail after the item write, proving item and claim marker are atomic."""

    if "reward_claimed_at" in kwargs.get("update_fields", ()):
        raise RuntimeError("claim marker unavailable")
    return original_save(self, *args, **kwargs)


with patch.object(AdventureParticipation, "save", fail_claim_marker):
    assert not progress.finalize_completion(completed)[0]
assert not Inventory.objects.filter(owner=player).exists()
participation.refresh_from_db()
assert participation.reward_claimed_at is None
assert "Potion x1" in progress.claim_completed_rewards(player)
assert progress.claim_completed_rewards(player) == "No unclaimed Adventure rewards."
assert Inventory.objects.get(owner=player).quantity == 1

second = AdventureSession.objects.create(
    leader=player, template_key="alpha_meadow", current_node="entrance",
    state="completed", completed_at=timezone.now(),
)
assert not progress.finalize_completion(second)[0]
assert Inventory.objects.get(owner=player).quantity == 1

other = ObjectDB.objects.create(key="Second player")
other_run = AdventureSession.objects.create(
    leader=other, template_key="alpha_meadow", current_node="entrance",
    state="completed", completed_at=timezone.now(),
)
with patch.object(progress, "_model", side_effect=RuntimeError("participation table unavailable")):
    assert "+adventure/claim" in progress.safe_finalize_completion(other_run)
assert not AdventureParticipation.objects.filter(session=other_run).exists()
assert progress.claim_completed_rewards(player) == "No unclaimed Adventure rewards."
assert not Inventory.objects.filter(owner=other).exists()
assert "Potion x1" in progress.claim_completed_rewards(other)
assert Inventory.objects.get(owner=other).quantity == 1

active = AdventureSession.objects.create(
    leader=player, template_key="alpha_meadow", current_node="tall_grass",
    metadata={"encounter_state": "pending", "route_key": "wild"},
)
with patch.object(AdventureSession, "save", side_effect=RuntimeError("session write unavailable")):
    try:
        sessions.resolve_encounter_result(active.pk, player, "capture")
    except RuntimeError:
        pass
    else:
        raise AssertionError("failed session save must propagate")
active.refresh_from_db()
assert active.metadata["encounter_state"] == "pending"
assert not AdventureParticipation.objects.filter(session=active).exists()
assert sessions.resolve_encounter_result(active.pk, player, "capture").ok
assert sessions.resolve_encounter_result(active.pk, player, "loss").ok
active.refresh_from_db()
assert active.metadata["encounter_result"] == "capture"
assert active.objective_progress["resolve_encounter"] == 1
assert AdventureParticipation.objects.get(session=active).encounter_result == "capture"

print("Adventure recovery ORM checks passed")
