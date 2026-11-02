"""Preserve legacy occupancy before enforcing exclusive solo reservations."""

from collections import defaultdict
from collections.abc import Mapping
from types import SimpleNamespace

from django.db import migrations, models


def inspect_legacy_occupancy(apps, alias):
    """Read existing identity evidence; report ambiguity instead of repairing it."""
    from evennia.utils.dbserialize import from_pickle

    Session = apps.get_model("pokemon", "AdventureSession")
    Object = apps.get_model("objects", "ObjectDB")
    # Explicit legacy columns also let the preflight run before AddField.
    sessions = [SimpleNamespace(**row) for row in Session.objects.using(alias).order_by("pk").values(
        "pk", "leader_id", "instance_room_id", "state", "metadata")]
    known = {str(session.pk): session for session in sessions}
    objects = {}
    errors = []

    def object_and_attributes(identifier):
        if identifier not in objects:
            row = Object.objects.using(alias).filter(pk=identifier).values("pk", "db_location_id").first() if identifier else None
            obj = SimpleNamespace(**row) if row else None
            # Query values directly: materializing typeclass objects may run at_init hooks.
            attributes = {} if obj is None else {key: from_pickle(value) for key, value in
                Object.objects.using(alias).filter(
                    models.Q(db_attributes__db_key__in=("adventure_session_id", "pending_adventure_results"))
                    | models.Q(db_attributes__db_key__startswith="battle_", db_attributes__db_key__endswith="_encounter"),
                    pk=identifier, db_attributes__db_category__isnull=True, db_attributes__db_attrtype__isnull=True,
                ).values_list("db_attributes__db_key", "db_attributes__db_value")}
            pointer = attributes.get("adventure_session_id")
            if pointer:
                pointed = known.get(str(pointer))
                if pointed is None or identifier not in (pointed.leader_id, pointed.instance_room_id):
                    errors.append(f"object {identifier}: unknown or foreign session pointer {pointer}")
            pending = attributes.get("pending_adventure_results")
            if pending and not isinstance(pending, Mapping):
                errors.append(f"object {identifier}: invalid pending-result receipt")
            elif isinstance(pending, Mapping):
                for key in pending:
                    pointed = known.get(str(key))
                    if pointed is None or pointed.leader_id != identifier:
                        errors.append(f"object {identifier}: unknown or foreign pending session {key}")
            objects[identifier] = obj, attributes
        return objects[identifier]

    held = []
    leaders, rooms = defaultdict(list), defaultdict(list)
    for session in sessions:
        leader, player_attrs = object_and_attributes(session.leader_id)
        room, room_attrs = object_and_attributes(session.instance_room_id)
        sid = str(session.pk)
        metadata = session.metadata or {}
        if not isinstance(metadata, Mapping):
            errors.append(f"session {session.pk}: invalid encounter metadata")
            metadata = {}
        pending = player_attrs.get("pending_adventure_results") or {}
        original_result = isinstance(pending, Mapping) and sid in {str(key) for key in pending}
        original_battle = any(
            str(key).startswith("battle_") and str(key).endswith("_encounter")
            and isinstance(value, Mapping) and value.get("source_type") == "adventure"
            and str(value.get("adventure_session_id")) == sid
            for key, value in room_attrs.items())
        pointer = any(str(attrs.get("adventure_session_id")) == sid for attrs in (player_attrs, room_attrs))
        physically_present = (session.state == "completed" and leader is not None
                              and room is not None and leader.db_location_id == room.pk
                              and not player_attrs.get("adventure_session_id")
                              and not room_attrs.get("adventure_session_id") and not pending)
        if not (session.state == "active" or pointer or original_result or original_battle
                or physically_present or metadata.get("encounter_state") == "pending"):
            continue
        held.append(session.pk)
        if leader is None or room is None:
            errors.append(f"session {session.pk}: missing leader or instance room")
        leaders[session.leader_id].append(session.pk)
        rooms[session.instance_room_id].append(session.pk)
    for kind, groups in (("character", leaders), ("room", rooms)):
        for identifier, sessions in groups.items():
            if len(sessions) > 1:
                errors.append(f"{kind} {identifier}: competing sessions {sessions}")
    return {"held_session_ids": held, "errors": errors}


def preserve_occupancy(apps, schema_editor):
    """Backfill only unambiguous claims, without editing histories or rewards."""
    alias = schema_editor.connection.alias
    report = inspect_legacy_occupancy(apps, alias)
    if report["errors"]:
        raise RuntimeError("Adventure occupancy preflight failed: " + "; ".join(report["errors"]))
    apps.get_model("pokemon", "AdventureSession").objects.using(alias).filter(
        pk__in=report["held_session_ids"]).update(holds_instance=True)


class Migration(migrations.Migration):
    """Add occupancy independently of completion and reward delivery."""

    dependencies = [("pokemon", "0059_owned_trained_stat_nature")]
    operations = [
        migrations.AddField(model_name="adventuresession", name="holds_instance",
                            field=models.BooleanField(default=False)),
        migrations.RunPython(preserve_occupancy, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="adventuresession", constraint=models.UniqueConstraint(
            fields=("leader",), condition=models.Q(holds_instance=True), name="adventure_occupied_leader_uniq")),
        migrations.AddConstraint(model_name="adventuresession", constraint=models.UniqueConstraint(
            fields=("instance_room",), condition=models.Q(holds_instance=True), name="adventure_occupied_room_uniq")),
        migrations.AddConstraint(model_name="adventuresession", constraint=models.CheckConstraint(
            condition=models.Q(holds_instance=False) | (
                models.Q(leader__isnull=False) & models.Q(instance_room__isnull=False)),
            name="adventure_occupied_identity")),
    ]
