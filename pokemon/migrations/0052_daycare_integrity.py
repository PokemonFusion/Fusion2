"""Commit-time agreement between Daycare entries, claims and canonical custody."""

import importlib

from django.db import migrations


OLD_CHECK = importlib.import_module("pokemon.migrations.0048_ownership_integrity").SQL.split(
    "CREATE FUNCTION pf2_check_reservation", 1)[1].split("CREATE FUNCTION pf2_reservation_guard", 1)[0]
OLD_CHECK = "CREATE OR REPLACE FUNCTION pf2_check_reservation" + OLD_CHECK
NEW_CHECK = OLD_CHECK.replace("placement_kind NOT IN ('party', 'box')",
    "(placement_kind NOT IN ('party', 'box') AND NOT (placement_kind='daycare' AND r.kind='daycare'))")

SQL = r"""
CREATE FUNCTION pf2_check_daycare(pokemon_uuid uuid) RETURNS void AS $$
DECLARE e record; p record;
BEGIN
    SELECT * INTO e FROM pokemon_daycareentry WHERE owned_id=pokemon_uuid AND state='active';
    SELECT * INTO p FROM pokemon_pokemonplacement WHERE pokemon_id=pokemon_uuid;
    IF e.id IS NOT NULL THEN
        IF p.id IS NULL OR p.location_type<>'daycare' OR p.storage_id<>e.storage_id OR e.pokemon_id<>pokemon_uuid
          OR NOT EXISTS(SELECT 1 FROM pokemon_pokemonreservation r WHERE r.pokemon_id=pokemon_uuid
            AND r.storage_id=e.storage_id AND r.kind='daycare' AND r.token=e.id) THEN
            RAISE EXCEPTION 'Daycare entry has invalid canonical custody: %', pokemon_uuid USING ERRCODE='23514';
        END IF;
    ELSIF p.id IS NOT NULL AND p.location_type='daycare' THEN
        RAISE EXCEPTION 'Canonical Daycare placement has no active entry: %', pokemon_uuid USING ERRCODE='23514';
    END IF;
    IF EXISTS(SELECT 1 FROM pokemon_daycareentry d JOIN pokemon_pokemonreservation r ON r.token=d.id
       WHERE d.owned_id=pokemon_uuid AND d.state<>'active' AND r.kind='daycare') THEN
        RAISE EXCEPTION 'Retrieved Daycare entry retains a claim: %', pokemon_uuid USING ERRCODE='23514';
    END IF;
END;
$$ LANGUAGE plpgsql;
CREATE FUNCTION pf2_daycare_guard() RETURNS trigger AS $$
BEGIN
    IF TG_TABLE_NAME='pokemon_daycareentry' THEN
        IF TG_OP<>'INSERT' THEN PERFORM pf2_check_daycare(OLD.owned_id); END IF;
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_daycare(NEW.owned_id); END IF;
    ELSE
        IF TG_OP<>'INSERT' THEN PERFORM pf2_check_daycare(OLD.pokemon_id); END IF;
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_daycare(NEW.pokemon_id); END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER pf2_daycare_entry AFTER INSERT OR UPDATE OR DELETE ON pokemon_daycareentry
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_daycare_guard();
CREATE CONSTRAINT TRIGGER pf2_daycare_placement AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonplacement
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_daycare_guard();
CREATE CONSTRAINT TRIGGER pf2_daycare_claim AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonreservation
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_daycare_guard();
"""


def install(apps, schema_editor):
    """Require a valid versioned placement/claim audit before installing checks."""
    if schema_editor.connection.vendor != "postgresql":
        return
    from pokemon.services.ownership_audit import audit_ownership_v2

    schema_editor.execute("LOCK TABLE pokemon_daycareentry, pokemon_pokemonreservation, pokemon_pokemonplacement, "
                          "pokemon_ownedpokemon, pokemon_userstorage, pokemon_trainer IN SHARE ROW EXCLUSIVE MODE")
    problems = list(audit_ownership_v2(apps, schema_editor.connection.alias))
    if problems:
        raise RuntimeError("Daycare audit failed; no automatic repairs: " + "; ".join(map(str, problems[:20])))
    schema_editor.execute(NEW_CHECK + SQL, params=None)


def uninstall(apps, schema_editor):
    """Restore the earlier generic reservation contract without deleting assets."""
    if schema_editor.connection.vendor != "postgresql":
        return
    for trigger, table in (("pf2_daycare_entry", "pokemon_daycareentry"),
            ("pf2_daycare_placement", "pokemon_pokemonplacement"), ("pf2_daycare_claim", "pokemon_pokemonreservation")):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS pf2_daycare_guard(), pf2_check_daycare(uuid)")
    schema_editor.execute(OLD_CHECK, params=None)


class Migration(migrations.Migration):
    """Validate Daycare custody while retaining previous migration behavior."""

    dependencies = [("pokemon", "0051_daycare")]
    operations = [migrations.RunPython(install, uninstall)]
