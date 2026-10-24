"""Versioned market custody checks and immutable price/payment receipts."""

import importlib

from django.db import migrations


OLD_SEAL = importlib.import_module("pokemon.migrations.0048_ownership_integrity").SQL.split(
    "CREATE FUNCTION pf2_transfer_seal()", 1)[1].split("CREATE TRIGGER pf2_transfer_sealed", 1)[0]
OLD_SEAL = "CREATE OR REPLACE FUNCTION pf2_transfer_seal()" + OLD_SEAL
NEW_SEAL = OLD_SEAL.replace(
    "OR NEW.expires_at IS DISTINCT FROM OLD.expires_at",
    "OR NEW.purpose IS DISTINCT FROM OLD.purpose OR NEW.expires_at IS DISTINCT FROM OLD.expires_at")

SQL = r"""
CREATE FUNCTION pf2_check_market(listing_uuid uuid) RETURNS void AS $$
DECLARE l record; owner_id bigint; placement_kind text;
BEGIN
    SELECT * INTO l FROM pokemon_marketlisting WHERE id=listing_uuid;
    IF NOT FOUND THEN RETURN; END IF;
    IF l.state='active' THEN
        SELECT t.user_id,p.location_type INTO owner_id,placement_kind
        FROM pokemon_ownedpokemon o JOIN pokemon_trainer t ON t.id=o.trainer_id
        JOIN pokemon_pokemonplacement p ON p.pokemon_id=o.unique_id
        JOIN pokemon_userstorage s ON s.id=p.storage_id
        JOIN pokemon_pokemonreservation r ON r.pokemon_id=o.unique_id AND r.storage_id=s.id
        WHERE o.unique_id=l.owned_id AND r.kind='market' AND r.token=l.id
          AND s.user_id=t.user_id;
        IF NOT FOUND OR owner_id<>l.seller_character_id OR placement_kind NOT IN ('party','box')
          OR l.seller_id<>l.seller_character_id OR l.pokemon_id<>l.owned_id THEN
            RAISE EXCEPTION 'Active market listing has invalid custody: %', listing_uuid USING ERRCODE='23514';
        END IF;
    ELSIF EXISTS(SELECT 1 FROM pokemon_pokemonreservation WHERE kind='market' AND token=l.id) THEN
        RAISE EXCEPTION 'Closed market listing retains a reservation: %', listing_uuid USING ERRCODE='23514';
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION pf2_market_guard() RETURNS trigger AS $$
BEGIN
    IF TG_TABLE_NAME='pokemon_marketlisting' THEN
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_market(NEW.id); END IF;
    ELSIF TG_TABLE_NAME='pokemon_ownedpokemon' THEN
        PERFORM pf2_check_market(id) FROM pokemon_marketlisting WHERE owned_id=NEW.unique_id AND state='active';
    ELSIF TG_TABLE_NAME='pokemon_pokemonplacement' THEN
        IF TG_OP<>'INSERT' THEN
            PERFORM pf2_check_market(id) FROM pokemon_marketlisting WHERE owned_id=OLD.pokemon_id AND state='active';
        END IF;
        IF TG_OP<>'DELETE' THEN
            PERFORM pf2_check_market(id) FROM pokemon_marketlisting WHERE owned_id=NEW.pokemon_id AND state='active';
        END IF;
    ELSIF TG_TABLE_NAME='pokemon_userstorage' THEN
        PERFORM pf2_check_market(l.id) FROM pokemon_marketlisting l
          JOIN pokemon_pokemonplacement p ON p.pokemon_id=l.owned_id WHERE p.storage_id=NEW.id AND l.state='active';
    ELSIF TG_TABLE_NAME='pokemon_trainer' THEN
        PERFORM pf2_check_market(l.id) FROM pokemon_marketlisting l
          JOIN pokemon_ownedpokemon o ON o.unique_id=l.owned_id WHERE o.trainer_id=NEW.id AND l.state='active';
    ELSE
        IF TG_OP<>'INSERT' AND OLD.kind='market' THEN PERFORM pf2_check_market(OLD.token); END IF;
        IF TG_OP<>'DELETE' AND NEW.kind='market' THEN PERFORM pf2_check_market(NEW.token); END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER pf2_market_listing AFTER INSERT OR UPDATE ON pokemon_marketlisting
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();
CREATE CONSTRAINT TRIGGER pf2_market_claim AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonreservation
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();
CREATE CONSTRAINT TRIGGER pf2_market_owned AFTER UPDATE ON pokemon_ownedpokemon
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();
CREATE CONSTRAINT TRIGGER pf2_market_placement AFTER INSERT OR UPDATE OR DELETE ON pokemon_pokemonplacement
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();
CREATE CONSTRAINT TRIGGER pf2_market_storage AFTER UPDATE ON pokemon_userstorage
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();
CREATE CONSTRAINT TRIGGER pf2_market_trainer AFTER UPDATE ON pokemon_trainer
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_market_guard();

CREATE FUNCTION pf2_market_seal() RETURNS trigger AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Market listings retain durable outcomes; cancel active listings' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.seller_character_id IS DISTINCT FROM OLD.seller_character_id
          OR NEW.seller_name IS DISTINCT FROM OLD.seller_name OR NEW.owned_id IS DISTINCT FROM OLD.owned_id
          OR NEW.snapshot IS DISTINCT FROM OLD.snapshot OR NEW.price IS DISTINCT FROM OLD.price
          OR NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
          OR NEW.request_selector IS DISTINCT FROM OLD.request_selector
          OR (OLD.state<>'active' AND (to_jsonb(NEW)-ARRAY['seller_id','buyer_id','pokemon_id'])
                                     IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['seller_id','buyer_id','pokemon_id']))
          OR (OLD.state<>'active' AND ((NEW.seller_id IS NOT NULL AND NEW.seller_id IS DISTINCT FROM OLD.seller_id)
            OR (NEW.buyer_id IS NOT NULL AND NEW.buyer_id IS DISTINCT FROM OLD.buyer_id)
            OR (NEW.pokemon_id IS NOT NULL AND NEW.pokemon_id IS DISTINCT FROM OLD.pokemon_id))) THEN
            RAISE EXCEPTION 'Market terms and terminal receipts are immutable' USING ERRCODE='23514';
        END IF;
    END IF;
    IF NEW.state='sold' AND (jsonb_typeof(NEW.receipt) IS DISTINCT FROM 'object'
      OR NEW.receipt->>'purchase' IS DISTINCT FROM NEW.purchase_id::text
      OR NEW.receipt->>'listing' IS DISTINCT FROM NEW.id::text
      OR NEW.receipt->>'buyer' IS DISTINCT FROM NEW.buyer_character_id::text
      OR NEW.receipt->>'seller' IS DISTINCT FROM NEW.seller_character_id::text
      OR NEW.receipt->>'price' IS DISTINCT FROM NEW.price::text) THEN
        RAISE EXCEPTION 'Invalid market payment receipt' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_market_sealed BEFORE INSERT OR UPDATE OR DELETE ON pokemon_marketlisting
 FOR EACH ROW EXECUTE FUNCTION pf2_market_seal();
"""


def install(apps, schema_editor):
    """Audit existing listings without inventing ownership, funds or consent."""
    if schema_editor.connection.vendor != "postgresql":
        return
    from pokemon.services.market_audit import audit_market_v1

    schema_editor.execute("LOCK TABLE pokemon_marketlisting, pokemon_pokemonreservation, "
                          "pokemon_ownedpokemon, pokemon_pokemonplacement, pokemon_userstorage, "
                          "pokemon_trainer IN SHARE ROW EXCLUSIVE MODE")
    problems = list(audit_market_v1(apps, schema_editor.connection.alias))
    if problems:
        raise RuntimeError("Market audit failed; no automatic repairs: " + "; ".join(map(str, problems[:20])))
    schema_editor.execute(NEW_SEAL + SQL, params=None)


def uninstall(apps, schema_editor):
    """Restore the earlier transfer seal and remove only market guarantees."""
    if schema_editor.connection.vendor != "postgresql":
        return
    for trigger, table in (("pf2_market_sealed", "pokemon_marketlisting"),
            ("pf2_market_listing", "pokemon_marketlisting"), ("pf2_market_claim", "pokemon_pokemonreservation"),
            ("pf2_market_owned", "pokemon_ownedpokemon"), ("pf2_market_placement", "pokemon_pokemonplacement"),
            ("pf2_market_storage", "pokemon_userstorage"), ("pf2_market_trainer", "pokemon_trainer")):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS pf2_market_seal(), pf2_market_guard(), pf2_check_market(uuid)")
    schema_editor.execute(OLD_SEAL, params=None)


class Migration(migrations.Migration):
    """Validate fixed-price custody while retaining the generic claim boundary."""

    dependencies = [("pokemon", "0049_marketplace")]
    operations = [migrations.RunPython(install, uninstall)]
