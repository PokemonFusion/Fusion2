"""PostgreSQL commit-time ownership/placement integrity.

Row CHECKs cannot inspect other tables or require a referencing placement row.
Deferred triggers allow atomic creation, moves and release, then validate the
final state. Production uses PostgreSQL (the models already use ArrayField).
"""

from django.db import migrations


CHECK_SQL = r"""
CREATE FUNCTION pf2_check_placement(pokemon_uuid uuid) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    owner_user bigint;
    placement_user bigint;
    placement_count integer;
    box_storage bigint;
    owner_storage bigint;
BEGIN
    SELECT t.user_id INTO owner_user
      FROM pokemon_ownedpokemon p LEFT JOIN pokemon_trainer t ON t.id = p.trainer_id
      WHERE p.unique_id = pokemon_uuid;
    IF NOT FOUND THEN RETURN; END IF; -- released/deleted in this transaction
    IF owner_user IS NULL THEN
        RAISE EXCEPTION 'Pokemon % has no owner', pokemon_uuid USING ERRCODE = '23514';
    END IF;
    SELECT count(*) INTO placement_count FROM pokemon_pokemonplacement WHERE pokemon_id = pokemon_uuid;
    IF placement_count <> 1 THEN
        RAISE EXCEPTION 'Pokemon % requires exactly one placement (found %)', pokemon_uuid, placement_count
          USING ERRCODE = '23514';
    END IF;
    SELECT s.user_id, s.id, b.storage_id INTO placement_user, owner_storage, box_storage
      FROM pokemon_pokemonplacement p
      JOIN pokemon_userstorage s ON s.id = p.storage_id
      LEFT JOIN pokemon_storagebox b ON b.id = p.box_id
      WHERE p.pokemon_id = pokemon_uuid;
    IF placement_user IS DISTINCT FROM owner_user THEN
        RAISE EXCEPTION 'Pokemon % owner/placement mismatch', pokemon_uuid USING ERRCODE = '23514';
    END IF;
    IF box_storage IS NOT NULL AND box_storage <> owner_storage THEN
        RAISE EXCEPTION 'Pokemon % box/storage mismatch', pokemon_uuid USING ERRCODE = '23514';
    END IF;
END;
$$;
CREATE FUNCTION pf2_placement_integrity() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    pid uuid;
BEGIN
    IF TG_TABLE_NAME = 'pokemon_ownedpokemon' THEN
        IF TG_OP <> 'DELETE' THEN PERFORM pf2_check_placement(NEW.unique_id); END IF;
    ELSIF TG_TABLE_NAME = 'pokemon_pokemonplacement' THEN
        IF TG_OP <> 'INSERT' THEN PERFORM pf2_check_placement(OLD.pokemon_id); END IF;
        IF TG_OP <> 'DELETE' THEN PERFORM pf2_check_placement(NEW.pokemon_id); END IF;
    ELSIF TG_TABLE_NAME = 'pokemon_userstorage' THEN
        FOR pid IN SELECT pokemon_id FROM pokemon_pokemonplacement WHERE storage_id = NEW.id LOOP
            PERFORM pf2_check_placement(pid);
        END LOOP;
    ELSIF TG_TABLE_NAME = 'pokemon_storagebox' THEN
        FOR pid IN SELECT pokemon_id FROM pokemon_pokemonplacement WHERE box_id = NEW.id LOOP
            PERFORM pf2_check_placement(pid);
        END LOOP;
    ELSIF TG_TABLE_NAME = 'pokemon_trainer' THEN
        FOR pid IN SELECT unique_id FROM pokemon_ownedpokemon WHERE trainer_id = NEW.id LOOP
            PERFORM pf2_check_placement(pid);
        END LOOP;
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER pf2_owned_placement
AFTER INSERT OR UPDATE ON pokemon_ownedpokemon
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_placement_integrity();
CREATE CONSTRAINT TRIGGER pf2_location_integrity
AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonplacement
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_placement_integrity();
CREATE CONSTRAINT TRIGGER pf2_storage_owner
AFTER UPDATE ON pokemon_userstorage
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_placement_integrity();
CREATE CONSTRAINT TRIGGER pf2_box_owner
AFTER UPDATE ON pokemon_storagebox
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_placement_integrity();
CREATE CONSTRAINT TRIGGER pf2_trainer_owner
AFTER UPDATE ON pokemon_trainer
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_placement_integrity();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS pf2_owned_placement ON pokemon_ownedpokemon;
DROP TRIGGER IF EXISTS pf2_location_integrity ON pokemon_pokemonplacement;
DROP TRIGGER IF EXISTS pf2_storage_owner ON pokemon_userstorage;
DROP TRIGGER IF EXISTS pf2_box_owner ON pokemon_storagebox;
DROP TRIGGER IF EXISTS pf2_trainer_owner ON pokemon_trainer;
DROP FUNCTION IF EXISTS pf2_placement_integrity();
DROP FUNCTION IF EXISTS pf2_check_placement(uuid);
"""


def install(apps, schema_editor):
    """Install the commit-time guard only on the supported production backend."""
    if schema_editor.connection.vendor == "postgresql":
        from importlib import import_module
        import_module("pokemon.migrations.0040_canonical_placement").require_valid_placements(apps, schema_editor)
        schema_editor.execute(CHECK_SQL, params=None)


def uninstall(apps, schema_editor):
    """Remove only the integrity functions/triggers introduced here."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("pokemon", "0040_canonical_placement")]
    operations = [migrations.RunPython(install, uninstall)]
