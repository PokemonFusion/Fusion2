"""Approved-only fresh and upgrade rehearsals in guarded disposable schemas.

Never select a game database: IsolatedPostgres requires an explicit test DSN and
rejects connections outside this process's randomly generated schema. This
runner applies migrations and therefore requires operational approval.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


def rehearse(scenario):
    """Apply the current graph, retain progression and verify guarded failures."""
    from django.apps import apps
    from django.db import connection
    from django.db.migrations.autodetector import MigrationAutodetector
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.state import ProjectState
    from django.utils import timezone

    from recovery_migrations import RecoveryMigrationRehearsal

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    seed = None
    if scenario != "fresh":
        baseline = [("pokemon", "0051_daycare" if scenario == "daycare-upgrade" else
                     "0049_marketplace" if scenario == "market-upgrade" else
                     "0047_ownership_transfers" if scenario == "guarded-upgrade" else "0046_berry_bed")]
        executor.migrate(baseline)
        seed = RecoveryMigrationRehearsal.seed_progression(executor.loader.project_state(baseline).apps)
    if scenario == "guarded-upgrade":
        history = executor.loader.project_state(baseline).apps
        # An invalid reservation must block rollout with all old assets intact.
        foreign = history.get_model("objects", "ObjectDB").objects.create(db_key="Foreign custody")
        foreign_storage = history.get_model("pokemon", "UserStorage").objects.create(user=foreign)
        invalid = history.get_model("pokemon", "PokemonReservation").objects.create(
            pokemon_id=seed["pokemon"], storage=foreign_storage, kind="market", token=uuid4())
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(targets)
        except RuntimeError as error:
            assert "Ownership audit failed" in str(error), str(error)
        else:
            raise AssertionError("Invalid reservation did not block deployment.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_proc WHERE proname='pf2_check_reservation' AND pronamespace=current_schema()::regnamespace")
            assert cursor.fetchone()[0] == 0, "Failed migration partially installed functions."
        invalid.delete()  # deliberately remove only our known invalid QA row
    if scenario == "market-upgrade":
        history = executor.loader.project_state(baseline).apps
        from datetime import timedelta

        invalid = history.get_model("pokemon", "MarketListing").objects.create(
            seller_id=seed["player"], seller_character_id=seed["player"], seller_name="Known invalid QA sale",
            pokemon_id=seed["pokemon"], owned_id=seed["pokemon"], request_selector="3", snapshot={}, price=100,
            expires_at=timezone.now() + timedelta(hours=24))
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(targets)
        except RuntimeError as error:
            assert "Market audit failed" in str(error), str(error)
        else:
            raise AssertionError("An active listing without its claim did not block deployment.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_proc WHERE proname='pf2_check_market' AND pronamespace=current_schema()::regnamespace")
            assert cursor.fetchone()[0] == 0, "Failed market migration partially installed functions."
        invalid.delete()  # deliberately remove only the known invalid task-owned listing
    if scenario == "daycare-upgrade":
        history = executor.loader.project_state(baseline).apps
        storage = history.get_model("pokemon", "UserStorage").objects.get(user_id=seed["player"])
        invalid = history.get_model("pokemon", "DaycareEntry").objects.create(
            storage=storage, pokemon_id=seed["pokemon"], owned_id=seed["pokemon"], saved_name="Known invalid QA parent", place=1)
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(targets)
        except RuntimeError as error:
            assert "Daycare audit failed" in str(error), str(error)
        else:
            raise AssertionError("A Daycare entry without matching placement/claim did not block deployment.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_proc WHERE proname='pf2_check_daycare' AND pronamespace=current_schema()::regnamespace")
            assert cursor.fetchone()[0] == 0, "Failed Daycare migration partially installed checks."
        invalid.delete()  # deliberately remove only the known invalid task-owned entry
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    executor = MigrationExecutor(connection)
    assert not executor.migration_plan(targets)
    changes = MigrationAutodetector(executor.loader.project_state(), ProjectState.from_apps(apps)).changes(
        graph=executor.loader.graph, trim_to_apps={"pokemon"})
    assert not changes.get("pokemon"), f"Pokemon model drift: {changes}"
    if seed is None:
        seed = RecoveryMigrationRehearsal.seed_progression(executor.loader.project_state(targets).apps)
    RecoveryMigrationRehearsal.verify_progression(seed)

    from evennia.objects.models import ObjectDB
    from pokemon.models.ownership import OwnershipTransfer
    from pokemon.models.storage import UserStorage
    from pokemon.models.trainer import Trainer
    from pokemon.services.ownership import OwnershipTransfers
    from pokemon.services.ownership_audit import audit_ownership_v1

    sender = ObjectDB.objects.get(pk=seed["player"])
    recipient = ObjectDB.objects.create(db_key="Transfer recipient")
    Trainer.objects.create(user=recipient, trainer_number=2)
    UserStorage.objects.create(user=recipient)
    operation = OwnershipTransfers(sender).prepare(recipient.pk, [{"pokemon": seed["pokemon"],
        "source": sender.pk, "destination": recipient.pk}])
    OwnershipTransfers(recipient).approve(operation.pk)
    receipt = OwnershipTransfers(sender).commit(operation.pk)
    assert OwnershipTransfers(recipient).commit(operation.pk) == receipt
    assert OwnershipTransfer.objects.get(pk=operation.pk).completed_at <= timezone.now()
    assert not list(audit_ownership_v1(apps))
    print(f"Ownership migration {scenario}: passed; preserved progression, transfer/replay, no drift.")


def main():
    """Use one fresh Django process/schema for each scenario."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("fresh", "upgrade", "guarded-upgrade", "market-upgrade", "daycare-upgrade"))
    args = parser.parse_args()
    if args.scenario is None:
        for scenario in ("fresh", "upgrade", "guarded-upgrade", "market-upgrade", "daycare-upgrade"):
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--scenario", scenario], check=True)
    else:
        with IsolatedPostgres():
            rehearse(args.scenario)


if __name__ == "__main__":
    main()
