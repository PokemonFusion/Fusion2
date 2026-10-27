"""Approval-only 0059 rehearsals, confined to new random loopback test schemas.

Never falls back to game database settings. This is migration qualification,
not a release, stock installation or ordinary player acquisition walkthrough.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from isolated_postgres import IsolatedPostgres

SCENARIOS = (
    "fresh",
    "upgrade",
    "active-pair",
    "reverse-reapply",
    "paid-reverse-refusal",
    "atomic-failure",
)
BASELINE = [("pokemon", "0058_necrozma_integrity")]


class MintMigrationRehearsal:
    """Preserve genetic rows, companion custody, earned assets and existing guards."""

    def __init__(self, scenario):
        self.scenario = scenario

    @staticmethod
    def snapshot(history):
        """Read every relevant legacy row without relying on current model fields."""
        names = (
            "OwnedPokemon",
            "PokemonPlacement",
            "ActivePokemonSlot",
            "Moveset",
            "MovesetSlot",
            "ActiveMoveslot",
            "PokemonLearnedMove",
            "MovePPBoost",
            "NecrozmaCombination",
            "NecrozmaResource",
            "NecrozmaOperation",
            "InventoryEntry",
            "GymVictory",
            "GymLeaderProfile",
            "AdventureParticipation",
        )
        return {
            name: list(history.get_model("pokemon", name).objects.order_by("pk").values())
            for name in names
        }

    @staticmethod
    def assert_common(before, after):
        """The one new nullable field must be the only change introduced by migration."""
        for name, rows in after.items():
            for row in rows:
                if name == "OwnedPokemon":
                    assert (
                        row.pop("trained_stat_nature", None) is None
                    ), "Migration inferred paid training"
            assert rows == before[name], f"0059 changed legacy {name}"

    @staticmethod
    def seed_pair(history, seed):
        """Historical-model prerequisite only: a valid pair already present at 0058."""
        from django.db import transaction
        from django.utils import timezone
        from datetime import timedelta
        from pokemon.helpers.pokemon_helpers import get_max_hp

        def model(name):
            return history.get_model("pokemon", name)

        storage = model("UserStorage").objects.get(user_id=seed["player"])
        with transaction.atomic():
            host = model("OwnedPokemon").objects.create(
                trainer_id=seed["trainer"],
                species="Necrozma-Dusk-Mane",
                ability="Prism Armor",
                nature="Jolly",
                level=50,
                total_exp=125000,
                ivs=[0] * 6,
                evs=[0] * 6,
                flags=["hypertrained:attack"],
            )
            companion = model("OwnedPokemon").objects.create(
                trainer_id=seed["trainer"],
                species="Solgaleo",
                ability="Full Metal Body",
                nature="Bold",
                level=50,
                total_exp=125000,
                ivs=[0] * 6,
                evs=[0] * 6,
            )
            for mon in (host, companion):
                mon.current_hp = (
                    get_max_hp(
                        SimpleNamespace(
                            **model("OwnedPokemon").objects.filter(pk=mon.pk).values().get()
                        )
                    )
                    - 7
                )
                mon.save(update_fields=["current_hp"])
            model("PokemonPlacement").objects.create(
                pokemon=host, storage=storage, location_type="party", slot=4
            )
            model("ActivePokemonSlot").objects.create(pokemon=host, storage=storage, slot=4)
            moveset = model("Moveset").objects.create(pokemon=host, index=0)
            model("OwnedPokemon").objects.filter(pk=host.pk).update(active_moveset=moveset)
            move, _ = model("Move").objects.get_or_create(name="Sunsteel Strike")
            model("PokemonLearnedMove").objects.create(pokemon=host, move=move)
            model("MovesetSlot").objects.create(moveset=moveset, slot=2, move=move)
            model("ActiveMoveslot").objects.create(pokemon=host, slot=2, move=move, current_pp=3)
            resource = model("NecrozmaResource").objects.create(
                host=host, source=move.name, current_pp=3
            )
            pair = model("NecrozmaCombination")(
                storage=storage,
                host=host,
                companion=companion,
                target_species=host.species,
                resource=resource,
                moveset=moveset,
                move_slot=2,
                return_type="party",
                return_slot=5,
            )
            model("PokemonPlacement").objects.create(
                pokemon=companion, storage=storage, location_type="combined", combination_id=pair.pk
            )
            pair.save()
            # Immutable historical receipt is deliberately not rewritten by 0059.
            model("NecrozmaOperation").objects.create(
                storage=storage,
                action="combine",
                state="completed",
                completed_at=timezone.now(),
                expires_at=timezone.now() + timedelta(minutes=10),
                terms={
                    "legacy_fixture": True,
                    "genetic_nature": "Jolly",
                    "host": str(host.pk),
                    "companion": str(companion.pk),
                    "source": move.name,
                },
                result={"lifecycle": str(pair.pk), "host": str(host.pk)},
            )
        return host.pk, companion.pk

    def run(self):
        """Apply only inside the IsolatedPostgres connection guard, then inspect SQL."""
        from django.apps import apps
        from django.db import connection, IntegrityError, transaction
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.executor import MigrationExecutor
        from django.db.migrations.state import ProjectState
        from unittest.mock import patch
        from recovery_migrations import RecoveryMigrationRehearsal

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        assert ("pokemon", "0059_owned_trained_stat_nature") in targets
        seed, pair_ids, before = None, None, None
        if self.scenario != "fresh":
            executor.migrate(BASELINE)
            history = executor.loader.project_state(BASELINE).apps
            seed = RecoveryMigrationRehearsal.seed_progression(history)
            history.get_model("pokemon", "OwnedPokemon").objects.filter(pk=seed["pokemon"]).update(
                nature="Jolly", flags=["hypertrained:attack"], current_hp=1
            )
            if self.scenario == "active-pair":
                pair_ids = self.seed_pair(history, seed)
                from pokemon.services.placement_audit import audit_placements_v3

                initial_problems = list(audit_placements_v3(history))
                assert not initial_problems, [str(problem) for problem in initial_problems]
            before = self.snapshot(history)
        if self.scenario == "atomic-failure":
            # Baseline migration changed the recorder after the initial loader
            # was built. Refresh it before constructing the injected forward
            # plan, just as the successful upgrade path does below.
            executor = MigrationExecutor(connection)
            migration = executor.loader.get_migration("pokemon", "0059_owned_trained_stat_nature")
            last = migration.operations[-1]

            def fail(*args, **kwargs):
                """Fail after real field/constraint DDL to prove PostgreSQL rollback."""
                raise RuntimeError("post-0059-DDL fixture")

            with patch.object(last, "database_forwards", side_effect=fail):
                try:
                    executor.migrate(targets)
                except RuntimeError as error:
                    assert "post-0059-DDL" in str(error)
                else:
                    raise AssertionError("Injected DDL error was swallowed")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='pokemon_ownedpokemon' AND column_name='trained_stat_nature'"
                )
                assert cursor.fetchone()[0] == 0, "Failed atomic migration left a partial field"
            assert self.snapshot(history) == before
            assert ("pokemon", "0059_owned_trained_stat_nature") not in MigrationExecutor(
                connection
            ).loader.applied_migrations
        MigrationExecutor(connection).migrate(targets)
        executor = MigrationExecutor(connection)
        assert not executor.migration_plan(targets)
        changes = MigrationAutodetector(
            executor.loader.project_state(), ProjectState.from_apps(apps)
        ).changes(graph=executor.loader.graph, trim_to_apps={"pokemon"})
        assert not changes.get("pokemon"), f"Model drift: {changes}"
        current = executor.loader.project_state(targets).apps
        if before is not None:
            self.assert_common(before, self.snapshot(current))
        if seed is None:
            seed = RecoveryMigrationRehearsal.seed_progression(current)
            # This fresh-install fixture has no legacy row to preserve. The
            # inherited generic seed intentionally leaves Nature blank; mint
            # stat checks instead need an explicitly labelled canonical parent.
            # This is QA setup after migration, never an inferred backfill.
            current.get_model("pokemon", "OwnedPokemon").objects.filter(pk=seed["pokemon"]).update(
                nature="Jolly"
            )
        if self.scenario == "reverse-reapply":
            baseline_snapshot = self.snapshot(current)
            MigrationExecutor(connection).migrate(BASELINE)
            MigrationExecutor(connection).migrate(targets)
            assert self.snapshot(current) == baseline_snapshot
        from pokemon.models.core import OwnedPokemon
        from pokemon.nature_training import NatureTraining
        from pokemon.helpers.pokemon_helpers import get_stats
        from pokemon.services.ownership import fresh_owned

        identifier = pair_ids[0] if pair_ids else seed["pokemon"]
        # Every allowed value and invalid constraint case uses real upgraded SQL.
        for name in NatureTraining.mint_names:
            OwnedPokemon.objects.filter(pk=identifier).update(trained_stat_nature=name)
            assert fresh_owned(identifier).trained_stat_nature == name
            get_stats(fresh_owned(identifier))
        for value in ("Hardy", "invented", "adamant"):
            try:
                with transaction.atomic():
                    OwnedPokemon.objects.filter(pk=identifier).update(trained_stat_nature=value)
            except IntegrityError:
                pass
            else:
                raise AssertionError("Migrated constraint accepted invalid training")
        if pair_ids:
            companion_before = OwnedPokemon.objects.filter(pk=pair_ids[1]).values().get()
            try:
                with transaction.atomic():
                    OwnedPokemon.objects.filter(pk=pair_ids[1]).update(
                        trained_stat_nature="Adamant"
                    )
            except IntegrityError:
                pass
            else:
                raise AssertionError("Upgrade lost the frozen-companion guard")
            assert OwnedPokemon.objects.filter(pk=pair_ids[1]).values().get() == companion_before
        if self.scenario == "paid-reverse-refusal":
            trained_before = self.snapshot(current)
            try:
                MigrationExecutor(connection).migrate(BASELINE)
            except RuntimeError as error:
                assert "data-preserving plan" in str(error)
            else:
                raise AssertionError("Rollback discarded paid training")
            assert self.snapshot(current) == trained_before
            assert not MigrationExecutor(connection).migration_plan(targets)
        # The inherited v1 audit predates combined companions. Preserve that
        # historical audit; check its progression assertions with the current
        # v3 placement/native audit when this fixture includes an active pair.
        if pair_ids:
            from evennia.objects.models import ObjectDB
            from pokemon.adventures.progress import claim_completed_rewards
            from pokemon.models.trainer import Trainer
            from pokemon.models.gym import GymVictory
            from pokemon.models.adventures import AdventureParticipation

            trainer = Trainer.objects.get(pk=seed["trainer"])
            assert trainer.get_item_quantity("Potion") == 2
            assert trainer.badges.filter(pk=seed["badge"]).exists()
            victory = GymVictory.objects.get(pk=seed["victory"])
            assert victory.claimed_at is None and victory.metadata["badge_id"] == seed["badge"]
            receipt = AdventureParticipation.objects.get(session_id=seed["run"])
            assert receipt.route_key == "wild" and receipt.encounter_result == "capture"
            assert receipt.reward_claimed_at is None
            player = ObjectDB.objects.get(pk=seed["player"])
            assert "Potion x1" in claim_completed_rewards(player)
            assert claim_completed_rewards(player) == "No unclaimed Adventure rewards."
            assert trainer.get_item_quantity("Potion") == 3
        else:
            RecoveryMigrationRehearsal.verify_progression(seed)
        from pokemon.services.placement_audit import audit_placements_v3

        problems = list(audit_placements_v3(apps))
        assert not problems, [str(problem) for problem in problems]
        print(
            f"Mint migration {self.scenario}: passed; genetics/assets/guards preserved; no model drift."
        )


def main():
    """One fresh process and random schema per approved rehearsal scenario."""
    from psycopg2.extensions import parse_dsn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS)
    args = parser.parse_args()
    parameters = parse_dsn(os.environ.get("PF2_TEST_POSTGRES_DSN", ""))
    if parameters.get("host") not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(
            "Mint migration rehearsals require the explicit task-owned loopback fixture."
        )
    if args.scenario:
        with IsolatedPostgres():
            MintMigrationRehearsal(args.scenario).run()
    else:
        for scenario in SCENARIOS:
            subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()), "--scenario", scenario],
                check=True,
            )


if __name__ == "__main__":
    main()
