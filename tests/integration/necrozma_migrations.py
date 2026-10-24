"""Approved-only native-pair migration rehearsals in fresh disposable schemas.

Requires PF2_TEST_POSTGRES_DSN and explicit operator approval. The connection
guard rejects every database outside this process's randomly generated schema.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from isolated_postgres import IsolatedPostgres


SCENARIOS = ("fresh", "upgrade", "legacy-fused", "legacy-source", "invalid-integrity", "reverse-reapply", "used-reverse-refusal")


def rehearse(scenario):
    """Check unchanged assets, pre-write refusal, installed guards and model drift."""
    from django.apps import apps
    from django.db import connection
    from django.db.migrations.autodetector import MigrationAutodetector
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.state import ProjectState

    from recovery_migrations import RecoveryMigrationRehearsal

    executor = MigrationExecutor(connection)
    target = executor.loader.graph.leaf_nodes()
    seed = None
    if scenario != "fresh":
        baseline = [("pokemon", "0057_necrozma_pairs" if scenario == "invalid-integrity" else "0056_onboarding_completion")]
        executor.migrate(baseline)
        history = executor.loader.project_state(baseline).apps
        seed = RecoveryMigrationRehearsal.seed_progression(history)
        Owned = history.get_model("pokemon", "OwnedPokemon")
        original = Owned.objects.filter(pk=seed["pokemon"]).values().get()
        if scenario in ("legacy-fused", "invalid-integrity", "legacy-source"):
            Owned.objects.filter(pk=seed["pokemon"]).update(
                species="necrozma" if scenario == "legacy-source" else "Necrozma-Dusk-Mane")
            learned = None
            if scenario == "legacy-source":
                move, _ = history.get_model("pokemon", "Move").objects.get_or_create(name="sunsteelstrike")
                learned = history.get_model("pokemon", "PokemonLearnedMove").objects.create(pokemon_id=seed["pokemon"], move=move)
            invalid = Owned.objects.filter(pk=seed["pokemon"]).values().get()
            try:
                MigrationExecutor(connection).migrate(target)
            except RuntimeError as error:
                assert "Necrozma" in str(error) and "audit failed" in str(error), str(error)
            else:
                raise AssertionError("Ambiguous legacy asset did not block migration")
            assert Owned.objects.filter(pk=seed["pokemon"]).values().get() == invalid
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_proc WHERE proname='pf2_check_necrozma' AND pronamespace=current_schema()::regnamespace")
                assert cursor.fetchone()[0] == 0
                if scenario != "invalid-integrity":
                    cursor.execute("SELECT to_regclass('pokemon_necrozmacombination')")
                    assert cursor.fetchone()[0] is None, "Preflight wrote feature schema before refusing legacy data"
            # Repair only the deliberately introduced QA corruption.
            if learned:
                learned.delete()
            Owned.objects.filter(pk=seed["pokemon"]).update(species=original["species"])
    MigrationExecutor(connection).migrate(target)
    executor = MigrationExecutor(connection)
    assert not executor.migration_plan(target)
    changes = MigrationAutodetector(executor.loader.project_state(), ProjectState.from_apps(apps)).changes(
        graph=executor.loader.graph, trim_to_apps={"pokemon"})
    assert not changes.get("pokemon"), f"Pokemon model drift: {changes}"
    if seed is None:
        seed = RecoveryMigrationRehearsal.seed_progression(executor.loader.project_state(target).apps)
    if scenario == "reverse-reapply":
        def snapshot():
            """Compare common player fields without claiming the pending reward."""
            return {name: list(apps.get_model("pokemon", name).objects.order_by("pk").values())
                for name in ("OwnedPokemon", "InventoryEntry", "GymVictory", "GymLeaderProfile", "AdventureParticipation")}
        before = snapshot()
        MigrationExecutor(connection).migrate([("pokemon", "0056_onboarding_completion")])
        assert snapshot() == before, "Unused feature rollback changed existing progression"
        MigrationExecutor(connection).migrate(target)
        assert snapshot() == before, "Feature reapplication changed existing progression"
    # This inherited acceptance check deliberately *claims* the pending reward;
    # run it once after migration checks, never once per schema stage.
    RecoveryMigrationRehearsal.verify_progression(seed)
    if scenario == "used-reverse-refusal":
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.services.necrozma import NecrozmaService

        room = ObjectDB.objects.create(db_key="Private migration QA Center")
        room.attributes.add("is_pokemon_center", True)
        character = ObjectDB.objects.create(db_key="Private migration pair owner")
        ObjectDB.objects.filter(pk=character.pk).update(db_location_id=room.pk)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        UserStorage.objects.create(user=character)
        host = create_owned_pokemon("Necrozma", trainer, 50, ability="Prism Armor", ivs=[0]*6, evs=[0]*6)
        companion = create_owned_pokemon("Solgaleo", trainer, 50, ability="Full Metal Body", ivs=[0]*6, evs=[0]*6)
        service = NecrozmaService(character)
        operation = service.prepare("combine", str(host.pk), str(companion.pk), 2)
        service.commit(operation.pk)
        pairs = list(NecrozmaCombination.objects.values())
        resources = list(NecrozmaResource.objects.values())
        try:
            MigrationExecutor(connection).migrate([("pokemon", "0056_onboarding_completion")])
        except RuntimeError as error:
            assert "data-preserving plan" in str(error), str(error)
        else:
            raise AssertionError("Rollback silently removed used native pair data")
        assert pairs == list(NecrozmaCombination.objects.values())
        assert resources == list(NecrozmaResource.objects.values())
        assert not MigrationExecutor(connection).migration_plan(target)
    from django.db import IntegrityError, transaction
    from pokemon.models.core import OwnedPokemon
    from pokemon.services.placement_audit import audit_placements_v3

    try:
        with transaction.atomic():
            OwnedPokemon.objects.filter(pk=seed["pokemon"]).update(species="Necrozma-Dawn-Wings")
    except IntegrityError:
        pass
    else:
        raise AssertionError("Actual migrated database accepted an unpaired fused grant")
    assert not list(audit_placements_v3(apps))
    print(f"Necrozma migration {scenario}: passed; assets preserved, deferred checks installed, no model drift.")


def main():
    """Keep every scenario's Django registry, migration graph and schema separate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS)
    args = parser.parse_args()
    if args.scenario:
        with IsolatedPostgres():
            rehearse(args.scenario)
    else:
        for scenario in SCENARIOS:
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--scenario", scenario], check=True)


if __name__ == "__main__":
    main()
