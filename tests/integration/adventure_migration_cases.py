"""Approved-only fresh/upgrade/ambiguous-legacy Adventure migration rehearsals.

Requires --approved and an explicit PF2_TEST_POSTGRES_DSN selecting a disposable
fixture. IsolatedPostgres confines all migration connections to its own schema.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from isolated_postgres import IsolatedPostgres

BASELINE = [("pokemon", "0059_owned_trained_stat_nature")]
TARGET = [("pokemon", "0060_adventure_occupancy")]


def run(scenario):
    """Preserve histories/receipts and reject conflicts before installing constraints."""
    from django.apps import apps
    from django.db import connection
    from django.db.migrations.autodetector import MigrationAutodetector
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.state import ProjectState
    from django.utils import timezone
    from evennia.utils.dbserialize import to_pickle

    executor = MigrationExecutor(connection)
    if scenario == "fresh":
        executor.migrate(TARGET)
    else:
        executor.migrate(BASELINE)
        history = executor.loader.project_state(BASELINE).apps
        Object = history.get_model("objects", "ObjectDB")
        Attribute = history.get_model("typeclasses", "Attribute")
        Session = history.get_model("pokemon", "AdventureSession")
        Participation = history.get_model("pokemon", "AdventureParticipation")
        hall = Object.objects.create(db_key="Fixture Hall")
        rooms, leaders, runs = [], [], []

        def attribute(obj, key, value):
            obj.db_attributes.add(Attribute.objects.create(db_key=key, db_value=to_pickle(value)))

        for i, state in enumerate(("active", "completed", "completed", "active")):
            room = Object.objects.create(db_key="Fixture Instance " + str(i))
            leader = Object.objects.create(db_key="Fixture Player " + str(i), db_location=hall if i >= 2 else room)
            session = Session.objects.create(leader=leader, instance_room=room, return_location=hall,
                        template_key="alpha_meadow", current_node="entrance", state=state,
                        completed_at=timezone.now() if state == "completed" else None)
            rooms.append(room)
            leaders.append(leader)
            runs.append(session)
            if i in (0, 1):
                attribute(leader, "adventure_session_id", session.pk)
                attribute(room, "adventure_session_id", session.pk)
        unpaid = Participation.objects.create(session=runs[2], player=leaders[2], route_key="wild",
                    encounter_result="capture", completed_at=timezone.now(), reward_item="Potion", reward_amount=1)
        runs[3].metadata = {"encounter_state": "pending", "route_key": "wild"}
        runs[3].save(update_fields=["metadata"])
        attribute(leaders[3], "pending_adventure_results", {str(runs[3].pk): "win"})
        attribute(rooms[3], "battle_81_encounter", {"source_type": "adventure", "adventure_session_id": runs[3].pk})
        if scenario == "guarded":
            stranger = Object.objects.create(db_key="Fixture Conflicting Player")
            Session.objects.create(leader=stranger, instance_room=rooms[0], template_key="alpha_meadow", current_node="entrance")
        before = list(Session.objects.order_by("pk").values())
        receipts = list(Participation.objects.order_by("pk").values())
        executor = MigrationExecutor(connection)
        if scenario == "guarded":
            try:
                executor.migrate(TARGET)
            except RuntimeError as error:
                assert "Adventure occupancy preflight failed" in str(error), str(error)
                assert "competing sessions" in str(error), str(error)
            else:
                raise AssertionError("Ambiguous legacy room occupancy did not block rollout")
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema=current_schema() "
                               "AND table_name='pokemon_adventuresession' AND column_name='holds_instance'")
                assert cursor.fetchone()[0] == 0, "Rejected migration left a partial schema change"
        else:
            executor.migrate(TARGET)
            Current = apps.get_model("pokemon", "AdventureSession")
            assert list(Current.objects.filter(holds_instance=True).order_by("pk").values_list("pk", flat=True)) == [
                runs[i].pk for i in (0, 1, 3)]
            assert not Current.objects.get(pk=runs[2].pk).holds_instance
        assert list(Session.objects.order_by("pk").values()) == before, "Migration changed run history"
        assert list(Participation.objects.order_by("pk").values()) == receipts, "Migration changed results/unpaid rewards"
        assert Participation.objects.get(pk=unpaid.pk).reward_claimed_at is None
    if scenario != "guarded":
        executor = MigrationExecutor(connection)
        assert not MigrationAutodetector(executor.loader.project_state(), ProjectState.from_apps(apps)).changes(
            graph=executor.loader.graph, trim_to_apps={"pokemon"}), "Pokemon models differ from the migration graph"
    print(json.dumps({"scenario": scenario, "passed": True}))


def main():
    """Require explicit migration approval and isolate each history in a process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", action="store_true", required=True)
    parser.add_argument("--scenario", choices=("fresh", "upgrade", "guarded"))
    args = parser.parse_args()
    if args.scenario is None:
        for scenario in ("fresh", "upgrade", "guarded"):
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--approved", "--scenario", scenario], check=True)
    else:
        with IsolatedPostgres():
            run(args.scenario)


if __name__ == "__main__":
    main()
