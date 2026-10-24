"""Seal paid breeding outcomes and defer parent/egg agreement until commit."""

from django.db import migrations


SQL = r"""
CREATE FUNCTION pf2_check_breeding(cycle_uuid uuid) RETURNS void AS $$
DECLARE c record; e record; live_egg boolean;
BEGIN
 SELECT * INTO c FROM pokemon_breedingcycle WHERE id=cycle_uuid;
 IF NOT FOUND THEN RETURN; END IF;
 IF c.storage_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM pokemon_userstorage s
       WHERE s.id=c.storage_id AND s.user_id=c.origin_character_id) THEN
   RAISE EXCEPTION 'Breeding origin/storage mismatch: %', cycle_uuid USING ERRCODE='23514';
 END IF;
 IF c.state='producing' THEN
   IF (SELECT count(*) FROM pokemon_daycareentry WHERE active_cycle_id=c.id)<>2
      OR NOT EXISTS(SELECT 1 FROM pokemon_daycareentry WHERE id=c.parent_a_id AND owned_id=c.parent_a_uuid
        AND storage_id=c.storage_id AND state='active' AND active_cycle_id=c.id)
      OR NOT EXISTS(SELECT 1 FROM pokemon_daycareentry WHERE id=c.parent_b_id AND owned_id=c.parent_b_uuid
        AND storage_id=c.storage_id AND state='active' AND active_cycle_id=c.id) THEN
     RAISE EXCEPTION 'Breeding parent/cycle mismatch: %', cycle_uuid USING ERRCODE='23514';
   END IF;
 ELSIF EXISTS(SELECT 1 FROM pokemon_daycareentry WHERE active_cycle_id=c.id) THEN
   RAISE EXCEPTION 'Closed breeding cycle retains parents: %', cycle_uuid USING ERRCODE='23514';
 END IF;
 SELECT * INTO e FROM pokemon_breedingegg WHERE cycle_id=c.id;
 IF c.state='collected' THEN
   IF e.id IS NULL OR e.id<>c.egg_uuid THEN
     RAISE EXCEPTION 'Collected cycle requires its exact egg receipt: %', cycle_uuid USING ERRCODE='23514';
   END IF;
   IF e.pokemon_id IS NOT NULL THEN
     SELECT is_egg INTO live_egg FROM pokemon_ownedpokemon WHERE unique_id=e.pokemon_id;
     IF NOT FOUND OR e.pokemon_id<>e.id OR live_egg IS DISTINCT FROM (e.hatched_at IS NULL) THEN
       RAISE EXCEPTION 'Egg/hatch state mismatch: %', e.id USING ERRCODE='23514';
     END IF;
   ELSIF EXISTS(SELECT 1 FROM pokemon_ownedpokemon WHERE unique_id=e.id) THEN
     RAISE EXCEPTION 'Released egg identity must not be resurrected: %', e.id USING ERRCODE='23514';
   END IF;
 ELSIF e.id IS NOT NULL THEN
   RAISE EXCEPTION 'Uncollected cycle has an egg receipt: %', cycle_uuid USING ERRCODE='23514';
 END IF;
END;
$$ LANGUAGE plpgsql;
CREATE FUNCTION pf2_breeding_guard() RETURNS trigger AS $$
BEGIN
 IF TG_TABLE_NAME='pokemon_breedingcycle' THEN
   IF TG_OP<>'DELETE' THEN PERFORM pf2_check_breeding(NEW.id); END IF;
 ELSIF TG_TABLE_NAME='pokemon_daycareentry' THEN
   IF TG_OP<>'INSERT' AND OLD.active_cycle_id IS NOT NULL THEN PERFORM pf2_check_breeding(OLD.active_cycle_id); END IF;
   IF TG_OP<>'DELETE' AND NEW.active_cycle_id IS NOT NULL THEN PERFORM pf2_check_breeding(NEW.active_cycle_id); END IF;
 ELSIF TG_TABLE_NAME='pokemon_breedingegg' THEN
   IF TG_OP<>'INSERT' THEN PERFORM pf2_check_breeding(OLD.cycle_id); END IF;
   IF TG_OP<>'DELETE' THEN PERFORM pf2_check_breeding(NEW.cycle_id); END IF;
 ELSIF TG_TABLE_NAME='pokemon_userstorage' THEN
   PERFORM pf2_check_breeding(id) FROM pokemon_breedingcycle WHERE storage_id=NEW.id;
 ELSE
   IF TG_OP<>'INSERT' THEN PERFORM pf2_check_breeding(cycle_id) FROM pokemon_breedingegg WHERE id=OLD.unique_id; END IF;
   IF TG_OP<>'DELETE' THEN PERFORM pf2_check_breeding(cycle_id) FROM pokemon_breedingegg WHERE id=NEW.unique_id; END IF;
 END IF;
 RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER pf2_breeding_cycle AFTER INSERT OR UPDATE ON pokemon_breedingcycle
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_breeding_guard();
CREATE CONSTRAINT TRIGGER pf2_breeding_parent AFTER INSERT OR UPDATE OR DELETE ON pokemon_daycareentry
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_breeding_guard();
CREATE CONSTRAINT TRIGGER pf2_breeding_egg AFTER INSERT OR UPDATE OR DELETE ON pokemon_breedingegg
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_breeding_guard();
CREATE CONSTRAINT TRIGGER pf2_breeding_owned AFTER INSERT OR UPDATE OR DELETE ON pokemon_ownedpokemon
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_breeding_guard();
CREATE CONSTRAINT TRIGGER pf2_breeding_storage AFTER UPDATE ON pokemon_userstorage
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pf2_breeding_guard();

CREATE FUNCTION pf2_breeding_seal() RETURNS trigger AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Breeding outcomes and cooldown history must be retained' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (
   NEW.id IS DISTINCT FROM OLD.id OR NEW.origin_character_id IS DISTINCT FROM OLD.origin_character_id
   OR NEW.parent_a_uuid IS DISTINCT FROM OLD.parent_a_uuid OR NEW.parent_b_uuid IS DISTINCT FROM OLD.parent_b_uuid
   OR NEW.egg_uuid IS DISTINCT FROM OLD.egg_uuid OR NEW.plan IS DISTINCT FROM OLD.plan
   OR NEW.fee IS DISTINCT FROM OLD.fee OR NEW.started_at IS DISTINCT FROM OLD.started_at
   OR NEW.ready_at IS DISTINCT FROM OLD.ready_at OR NEW.next_ready_at IS DISTINCT FROM OLD.next_ready_at
   OR (NEW.storage_id IS NOT NULL AND NEW.storage_id IS DISTINCT FROM OLD.storage_id)
   OR (NEW.parent_a_id IS NOT NULL AND NEW.parent_a_id IS DISTINCT FROM OLD.parent_a_id)
   OR (NEW.parent_b_id IS NOT NULL AND NEW.parent_b_id IS DISTINCT FROM OLD.parent_b_id)
   OR (OLD.state<>'producing' AND (to_jsonb(NEW)-ARRAY['storage_id','parent_a_id','parent_b_id'])
       IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['storage_id','parent_a_id','parent_b_id']))) THEN
   RAISE EXCEPTION 'Breeding outcome, cooldown and terminal receipts are immutable' USING ERRCODE='23514';
 END IF;
 IF jsonb_typeof(NEW.plan) IS DISTINCT FROM 'object' OR NEW.plan->>'rule_version' IS DISTINCT FROM '1'
    OR jsonb_typeof(NEW.plan->'is_shiny') IS DISTINCT FROM 'boolean' THEN
   RAISE EXCEPTION 'Invalid breeding trait plan' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_breeding_sealed BEFORE INSERT OR UPDATE OR DELETE ON pokemon_breedingcycle
 FOR EACH ROW EXECUTE FUNCTION pf2_breeding_seal();

CREATE FUNCTION pf2_egg_seal() RETURNS trigger AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Egg and hatch receipts must be retained' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id OR NEW.cycle_id IS DISTINCT FROM OLD.cycle_id
   OR NEW.collected_at IS DISTINCT FROM OLD.collected_at OR NEW.hatch_ready_at IS DISTINCT FROM OLD.hatch_ready_at
   OR (NEW.pokemon_id IS NOT NULL AND NEW.pokemon_id IS DISTINCT FROM OLD.pokemon_id)
   OR (OLD.hatched_at IS NOT NULL AND (to_jsonb(NEW)-'pokemon_id') IS DISTINCT FROM (to_jsonb(OLD)-'pokemon_id'))) THEN
   RAISE EXCEPTION 'Egg identity, readiness and hatch receipts are immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_egg_sealed BEFORE INSERT OR UPDATE OR DELETE ON pokemon_breedingegg
 FOR EACH ROW EXECUTE FUNCTION pf2_egg_seal();
"""


def install(apps, schema_editor):
    """Audit exact identities before installing guarantees; never reroll or repair."""
    if schema_editor.connection.vendor != "postgresql":
        return
    from pokemon.services.breeding_audit import audit_breeding_v1

    schema_editor.execute("LOCK TABLE pokemon_breedingcycle, pokemon_breedingegg, pokemon_daycareentry, "
                          "pokemon_ownedpokemon, pokemon_userstorage IN SHARE ROW EXCLUSIVE MODE")
    problems = list(audit_breeding_v1(apps, schema_editor.connection.alias))
    if problems:
        raise RuntimeError("Breeding audit failed; no automatic repairs: " + "; ".join(map(str, problems[:20])))
    schema_editor.execute(SQL, params=None)


def uninstall(apps, schema_editor):
    """Remove only this migration's checks without changing assets or outcomes."""
    if schema_editor.connection.vendor != "postgresql":
        return
    for trigger, table in (("pf2_breeding_cycle", "pokemon_breedingcycle"), ("pf2_breeding_parent", "pokemon_daycareentry"),
            ("pf2_breeding_egg", "pokemon_breedingegg"), ("pf2_breeding_owned", "pokemon_ownedpokemon"),
            ("pf2_breeding_storage", "pokemon_userstorage"), ("pf2_breeding_sealed", "pokemon_breedingcycle"),
            ("pf2_egg_sealed", "pokemon_breedingegg")):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS pf2_breeding_guard(), pf2_check_breeding(uuid), pf2_breeding_seal(), pf2_egg_seal()")


class Migration(migrations.Migration):
    """Enforce one durable outcome and consistent parent/egg state at commit."""

    dependencies = [("pokemon", "0053_breeding")]
    operations = [migrations.RunPython(install, uninstall)]
