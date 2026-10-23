"""Reject mismatched reservations and mutable consent/receipts on PostgreSQL."""

from django.db import migrations


SQL = r"""
CREATE FUNCTION pf2_check_reservation(pokemon_uuid uuid) RETURNS void AS $$
DECLARE r record; owner_id bigint; placement_kind text; op record;
BEGIN
    SELECT * INTO r FROM pokemon_pokemonreservation WHERE pokemon_id = pokemon_uuid;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT t.user_id, p.location_type INTO owner_id, placement_kind
      FROM pokemon_ownedpokemon o JOIN pokemon_trainer t ON t.id = o.trainer_id
      JOIN pokemon_pokemonplacement p ON p.pokemon_id = o.unique_id
      JOIN pokemon_userstorage s ON s.id = p.storage_id
      WHERE o.unique_id = pokemon_uuid AND s.id = r.storage_id AND s.user_id = t.user_id;
    IF NOT FOUND OR placement_kind NOT IN ('party', 'box') THEN
        RAISE EXCEPTION 'Reservation has invalid owner or placement: %', pokemon_uuid USING ERRCODE = '23514';
    END IF;
    IF r.kind = 'trade' THEN
        SELECT * INTO op FROM pokemon_ownershiptransfer WHERE id = r.transfer_id;
        IF NOT FOUND OR op.state <> 'pending' OR op.id <> r.token
           OR NOT op.approvals @> jsonb_build_array(owner_id)
           OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(op.terms) term
                          WHERE term->>'pokemon' = pokemon_uuid::text
                            AND (term->>'source')::bigint = owner_id) THEN
            RAISE EXCEPTION 'Reservation has invalid transfer consent: %', pokemon_uuid USING ERRCODE = '23514';
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION pf2_reservation_guard() RETURNS trigger AS $$
BEGIN
    IF TG_TABLE_NAME = 'pokemon_ownedpokemon' THEN
        IF TG_OP <> 'DELETE' THEN PERFORM pf2_check_reservation(NEW.unique_id); END IF;
    ELSIF TG_TABLE_NAME = 'pokemon_ownershiptransfer' THEN
        PERFORM pf2_check_reservation(pokemon_id) FROM pokemon_pokemonreservation WHERE transfer_id = NEW.id;
    ELSIF TG_TABLE_NAME = 'pokemon_userstorage' THEN
        PERFORM pf2_check_reservation(pokemon_id) FROM pokemon_pokemonreservation WHERE storage_id = NEW.id;
    ELSIF TG_TABLE_NAME = 'pokemon_trainer' THEN
        PERFORM pf2_check_reservation(unique_id) FROM pokemon_ownedpokemon WHERE trainer_id = NEW.id;
    ELSE
        IF TG_OP <> 'INSERT' THEN PERFORM pf2_check_reservation(OLD.pokemon_id); END IF;
        IF TG_OP <> 'DELETE' THEN PERFORM pf2_check_reservation(NEW.pokemon_id); END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER pf2_reservation_row AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonreservation
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();
CREATE CONSTRAINT TRIGGER pf2_reservation_owned AFTER UPDATE ON pokemon_ownedpokemon
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();
CREATE CONSTRAINT TRIGGER pf2_reservation_placement AFTER UPDATE OR DELETE ON pokemon_pokemonplacement
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();
CREATE CONSTRAINT TRIGGER pf2_reservation_transfer AFTER UPDATE ON pokemon_ownershiptransfer
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();
CREATE CONSTRAINT TRIGGER pf2_reservation_storage AFTER UPDATE ON pokemon_userstorage
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();
CREATE CONSTRAINT TRIGGER pf2_reservation_trainer AFTER UPDATE ON pokemon_trainer
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_reservation_guard();

CREATE FUNCTION pf2_transfer_seal() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.terms IS DISTINCT FROM OLD.terms
          OR NEW.proposer_id IS DISTINCT FROM OLD.proposer_id OR NEW.recipient_id IS DISTINCT FROM OLD.recipient_id
          OR NEW.expires_at IS DISTINCT FROM OLD.expires_at OR NEW.created_at IS DISTINCT FROM OLD.created_at
          OR (OLD.state <> 'pending' AND NEW IS DISTINCT FROM OLD) THEN
            RAISE EXCEPTION 'Transfer terms and terminal receipts are immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF jsonb_typeof(NEW.terms) <> 'array' OR jsonb_array_length(NEW.terms) NOT BETWEEN 1 AND 12
      OR jsonb_typeof(NEW.approvals) <> 'array'
      OR NOT NEW.approvals <@ jsonb_build_array(NEW.proposer_id, NEW.recipient_id)
      OR NOT NEW.approvals @> jsonb_build_array(NEW.proposer_id)
      OR (NEW.state = 'completed' AND NOT NEW.approvals @> jsonb_build_array(NEW.recipient_id)) THEN
        RAISE EXCEPTION 'Invalid transfer terms or approvals' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_transfer_sealed BEFORE INSERT OR UPDATE ON pokemon_ownershiptransfer
  FOR EACH ROW EXECUTE FUNCTION pf2_transfer_seal();
"""


def install(apps, schema_editor):
    """Audit without repairing before installing PostgreSQL-only guarantees."""
    if schema_editor.connection.vendor != "postgresql":
        return
    from pokemon.services.ownership_audit import audit_ownership_v1

    schema_editor.execute("LOCK TABLE pokemon_ownershiptransfer, pokemon_pokemonreservation, "
                          "pokemon_ownedpokemon, pokemon_pokemonplacement, pokemon_userstorage, "
                          "pokemon_trainer IN SHARE ROW EXCLUSIVE MODE")
    problems = list(audit_ownership_v1(apps, schema_editor.connection.alias))
    if problems:
        raise RuntimeError("Ownership audit failed; no automatic repairs: " + "; ".join(map(str, problems[:20])))
    schema_editor.execute(SQL, params=None)


def uninstall(apps, schema_editor):
    """Remove only this migration's triggers and functions."""
    if schema_editor.connection.vendor != "postgresql":
        return
    for trigger, table in (
        ("pf2_transfer_sealed", "pokemon_ownershiptransfer"),
        ("pf2_reservation_row", "pokemon_pokemonreservation"),
        ("pf2_reservation_owned", "pokemon_ownedpokemon"),
        ("pf2_reservation_placement", "pokemon_pokemonplacement"),
        ("pf2_reservation_transfer", "pokemon_ownershiptransfer"),
        ("pf2_reservation_storage", "pokemon_userstorage"),
        ("pf2_reservation_trainer", "pokemon_trainer"),
    ):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS pf2_transfer_seal(), pf2_reservation_guard(), pf2_check_reservation(uuid)")


class Migration(migrations.Migration):
    """Add fail-closed checks without modifying existing player assets."""

    dependencies = [("pokemon", "0047_ownership_transfers")]
    operations = [migrations.RunPython(install, uninstall)]
