"""Commit-time native-pair provenance, slot, PP and receipt integrity."""

from django.db import migrations


SQL = r"""
CREATE FUNCTION pf2_check_necrozma(pid uuid) RETURNS void AS $$
DECLARE p record; c record; hp record; cp record; r record;
        expected_companion text; expected_source text; expected_ability text;
        owner_user bigint; memberships integer; source_move bigint; bonus integer;
BEGIN
    SELECT * INTO p FROM pokemon_ownedpokemon WHERE unique_id=pid;
    IF NOT FOUND THEN RETURN; END IF;
    SELECT count(*) INTO memberships FROM pokemon_necrozmacombination WHERE host_id=pid OR companion_id=pid;
    IF memberships>1 THEN
        RAISE EXCEPTION 'Necrozma source has multiple roles: %',pid USING ERRCODE='23514';
    END IF;
    SELECT * INTO c FROM pokemon_necrozmacombination WHERE host_id=pid;
    IF c.id IS NULL THEN
        IF regexp_replace(lower(p.species),'[^a-z0-9]','','g') IN ('necrozmaduskmane','necrozmadawnwings') THEN
            RAISE EXCEPTION 'Owned fused Necrozma requires a live pair: %',pid USING ERRCODE='23514';
        END IF;
        IF EXISTS(SELECT 1 FROM pokemon_pokemonplacement x WHERE x.pokemon_id=pid AND x.location_type='combined'
          AND NOT EXISTS(SELECT 1 FROM pokemon_necrozmacombination a WHERE a.id=x.combination_id AND a.companion_id=pid)) THEN
            RAISE EXCEPTION 'Orphan combined companion: %',pid USING ERRCODE='23514';
        END IF;
    ELSE
        IF c.target_species='Necrozma-Dusk-Mane' THEN
            expected_companion:='Solgaleo'; expected_source:='Sunsteel Strike'; expected_ability:='Full Metal Body';
        ELSE
            expected_companion:='Lunala'; expected_source:='Moongeist Beam'; expected_ability:='Shadow Shield';
        END IF;
        SELECT user_id INTO owner_user FROM pokemon_userstorage WHERE id=c.storage_id;
        SELECT * INTO hp FROM pokemon_pokemonplacement WHERE pokemon_id=pid;
        SELECT * INTO cp FROM pokemon_pokemonplacement WHERE pokemon_id=c.companion_id;
        IF p.species<>c.target_species OR p.ability<>'Prism Armor' OR p.is_egg
          OR NOT EXISTS(SELECT 1 FROM pokemon_trainer WHERE id=p.trainer_id AND user_id=owner_user)
          OR NOT EXISTS(SELECT 1 FROM pokemon_ownedpokemon o WHERE o.unique_id=c.companion_id
            AND o.species=expected_companion AND o.ability=expected_ability AND NOT o.is_egg AND o.trainer_id=p.trainer_id)
          OR hp.id IS NULL OR hp.storage_id<>c.storage_id OR hp.location_type NOT IN ('party','box')
          OR cp.id IS NULL OR cp.storage_id<>c.storage_id OR cp.location_type<>'combined' OR cp.combination_id IS DISTINCT FROM c.id
          OR EXISTS(SELECT 1 FROM pokemon_necrozmacombination a WHERE a.id<>c.id
            AND (a.host_id IN (pid,c.companion_id) OR a.companion_id IN (pid,c.companion_id)))
          OR EXISTS(SELECT 1 FROM pokemon_pokemonreservation WHERE pokemon_id IN (pid,c.companion_id))
          OR EXISTS(SELECT 1 FROM pokemon_activepokemonslot WHERE pokemon_id=c.companion_id)
          OR EXISTS(SELECT 1 FROM pokemon_userstorage_stored_pokemon WHERE ownedpokemon_id=c.companion_id)
          OR EXISTS(SELECT 1 FROM pokemon_storagebox_pokemon WHERE ownedpokemon_id=c.companion_id) THEN
            RAISE EXCEPTION 'Invalid Necrozma pair custody: %',pid USING ERRCODE='23514';
        END IF;
        IF (hp.location_type='party' AND (
             (SELECT count(*) FROM pokemon_activepokemonslot WHERE pokemon_id=pid)<>1
             OR NOT EXISTS(SELECT 1 FROM pokemon_activepokemonslot WHERE pokemon_id=pid AND storage_id=c.storage_id AND slot=hp.slot)
             OR EXISTS(SELECT 1 FROM pokemon_userstorage_stored_pokemon WHERE ownedpokemon_id=pid)
             OR EXISTS(SELECT 1 FROM pokemon_storagebox_pokemon WHERE ownedpokemon_id=pid)))
          OR (hp.location_type='box' AND (
             EXISTS(SELECT 1 FROM pokemon_activepokemonslot WHERE pokemon_id=pid)
             OR (SELECT count(*) FROM pokemon_userstorage_stored_pokemon WHERE ownedpokemon_id=pid)<>1
             OR NOT EXISTS(SELECT 1 FROM pokemon_userstorage_stored_pokemon WHERE ownedpokemon_id=pid AND userstorage_id=c.storage_id)
             OR (SELECT count(*) FROM pokemon_storagebox_pokemon WHERE ownedpokemon_id=pid)<>1
             OR NOT EXISTS(SELECT 1 FROM pokemon_storagebox_pokemon WHERE ownedpokemon_id=pid AND storagebox_id=hp.box_id))) THEN
            RAISE EXCEPTION 'Native host legacy mirrors conflict: %',pid USING ERRCODE='23514';
        END IF;
        SELECT * INTO r FROM pokemon_necrozmaresource WHERE id=c.resource_id;
        SELECT id INTO source_move FROM pokemon_move WHERE name=expected_source;
        IF r.id IS NULL OR r.host_id<>pid OR r.source<>expected_source OR p.active_moveset_id IS DISTINCT FROM c.moveset_id
          OR NOT EXISTS(SELECT 1 FROM pokemon_moveset WHERE id=c.moveset_id AND pokemon_id=pid)
          OR NOT EXISTS(SELECT 1 FROM pokemon_activemoveslot WHERE pokemon_id=pid AND slot=c.move_slot
            AND move_id=source_move AND current_pp=r.current_pp)
          OR NOT EXISTS(SELECT 1 FROM pokemon_movesetslot WHERE moveset_id=c.moveset_id AND slot=c.move_slot AND move_id=source_move)
          OR NOT EXISTS(SELECT 1 FROM pokemon_pokemonlearnedmove WHERE pokemon_id=pid AND move_id=source_move)
          OR EXISTS(SELECT 1 FROM pokemon_activemoveslot WHERE pokemon_id=pid AND move_id=source_move AND slot<>c.move_slot)
          OR EXISTS(SELECT 1 FROM pokemon_movesetslot s JOIN pokemon_moveset m ON m.id=s.moveset_id
            WHERE m.pokemon_id=pid AND s.move_id=source_move AND (s.moveset_id<>c.moveset_id OR s.slot<>c.move_slot)) THEN
            RAISE EXCEPTION 'Invalid Necrozma source binding: %',pid USING ERRCODE='23514';
        END IF;
    END IF;
    IF regexp_replace(lower(p.species),'[^a-z0-9]','','g')='necrozma' OR c.id IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM pokemon_move m WHERE regexp_replace(lower(m.name),'[^a-z0-9]','','g') IN ('sunsteelstrike','moongeistbeam')
          AND m.name IS DISTINCT FROM expected_source AND (
            EXISTS(SELECT 1 FROM pokemon_pokemonlearnedmove WHERE pokemon_id=pid AND move_id=m.id)
            OR EXISTS(SELECT 1 FROM pokemon_activemoveslot WHERE pokemon_id=pid AND move_id=m.id)
            OR EXISTS(SELECT 1 FROM pokemon_movesetslot s JOIN pokemon_moveset ms ON ms.id=s.moveset_id
               WHERE ms.pokemon_id=pid AND s.move_id=m.id))) THEN
            RAISE EXCEPTION 'Unbound Necrozma source move: %',pid USING ERRCODE='23514';
        END IF;
    END IF;
    FOR r IN SELECT * FROM pokemon_necrozmaresource WHERE host_id=pid LOOP
        SELECT coalesce(max(b.bonus_pp),0) INTO bonus FROM pokemon_move m
          LEFT JOIN pokemon_moveppboost b ON b.move_id=m.id AND b.pokemon_id=pid WHERE m.name=r.source;
        IF p.species NOT IN ('Necrozma','Necrozma-Dusk-Mane','Necrozma-Dawn-Wings')
          OR bonus NOT BETWEEN 0 AND 3 OR r.current_pp>5+bonus THEN
            RAISE EXCEPTION 'Invalid Necrozma PP resource: %',pid USING ERRCODE='23514';
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION pf2_necrozma_guard() RETURNS trigger AS $$
DECLARE pid uuid;
BEGIN
    IF TG_TABLE_NAME='pokemon_necrozmacombination' THEN
        IF TG_OP<>'INSERT' THEN PERFORM pf2_check_necrozma(OLD.host_id); PERFORM pf2_check_necrozma(OLD.companion_id); END IF;
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_necrozma(NEW.host_id); PERFORM pf2_check_necrozma(NEW.companion_id); END IF;
    ELSIF TG_TABLE_NAME='pokemon_ownedpokemon' THEN
        IF TG_OP<>'DELETE' THEN
            PERFORM pf2_check_necrozma(NEW.unique_id);
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE companion_id=NEW.unique_id;
        END IF;
    ELSIF TG_TABLE_NAME='pokemon_necrozmaresource' THEN
        IF TG_OP<>'INSERT' THEN PERFORM pf2_check_necrozma(OLD.host_id); END IF;
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_necrozma(NEW.host_id); END IF;
    ELSIF TG_TABLE_NAME='pokemon_move' THEN
        FOR pid IN SELECT host_id FROM pokemon_necrozmaresource LOOP
            PERFORM pf2_check_necrozma(pid);
        END LOOP;
    ELSIF TG_TABLE_NAME IN ('pokemon_userstorage','pokemon_trainer') THEN
        IF TG_OP='DELETE' THEN RETURN NULL; END IF;
        FOR pid IN SELECT o.unique_id FROM pokemon_ownedpokemon o JOIN pokemon_trainer t ON t.id=o.trainer_id
          WHERE (TG_TABLE_NAME='pokemon_trainer' AND t.id=NEW.id) OR
            (TG_TABLE_NAME='pokemon_userstorage' AND t.user_id=NEW.user_id) LOOP
            PERFORM pf2_check_necrozma(pid);
        END LOOP;
        -- Include pairs whose storage was reassigned away from their owner.
        IF TG_TABLE_NAME='pokemon_userstorage' THEN
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE storage_id=NEW.id;
        END IF;
    ELSIF TG_TABLE_NAME='pokemon_movesetslot' THEN
        IF TG_OP<>'INSERT' THEN PERFORM pf2_check_necrozma(pokemon_id) FROM pokemon_moveset WHERE id=OLD.moveset_id; END IF;
        IF TG_OP<>'DELETE' THEN PERFORM pf2_check_necrozma(pokemon_id) FROM pokemon_moveset WHERE id=NEW.moveset_id; END IF;
    ELSIF TG_TABLE_NAME IN ('pokemon_userstorage_stored_pokemon','pokemon_storagebox_pokemon') THEN
        IF TG_OP<>'INSERT' THEN
            PERFORM pf2_check_necrozma(OLD.ownedpokemon_id);
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE companion_id=OLD.ownedpokemon_id;
        END IF;
        IF TG_OP<>'DELETE' THEN
            PERFORM pf2_check_necrozma(NEW.ownedpokemon_id);
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE companion_id=NEW.ownedpokemon_id;
        END IF;
    ELSE
        IF TG_OP<>'INSERT' THEN
            PERFORM pf2_check_necrozma(OLD.pokemon_id);
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE companion_id=OLD.pokemon_id;
        END IF;
        IF TG_OP<>'DELETE' THEN
            PERFORM pf2_check_necrozma(NEW.pokemon_id);
            PERFORM pf2_check_necrozma(host_id) FROM pokemon_necrozmacombination WHERE companion_id=NEW.pokemon_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION pf2_necrozma_operation_seal() RETURNS trigger AS $$
BEGIN
    IF TG_OP='UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id OR NEW.storage_id IS DISTINCT FROM OLD.storage_id
      OR NEW.action IS DISTINCT FROM OLD.action OR NEW.terms IS DISTINCT FROM OLD.terms
      OR NEW.expires_at IS DISTINCT FROM OLD.expires_at OR NEW.created_at IS DISTINCT FROM OLD.created_at
      OR (OLD.state<>'pending' AND NEW IS DISTINCT FROM OLD)) THEN
        RAISE EXCEPTION 'Necrozma terms and terminal receipts are immutable' USING ERRCODE='23514';
    END IF;
    IF jsonb_typeof(NEW.terms)<>'object' OR jsonb_typeof(NEW.result)<>'object'
      OR (NEW.state='completed' AND NEW.result='{}'::jsonb) THEN
        RAISE EXCEPTION 'Invalid Necrozma request or receipt' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_necrozma_operation_sealed BEFORE INSERT OR UPDATE ON pokemon_necrozmaoperation
 FOR EACH ROW EXECUTE FUNCTION pf2_necrozma_operation_seal();

CREATE FUNCTION pf2_necrozma_pair_seal() RETURNS trigger AS $$
BEGIN
    IF (to_jsonb(NEW)-'return_box_id') IS DISTINCT FROM (to_jsonb(OLD)-'return_box_id')
      OR (NEW.return_box_id IS DISTINCT FROM OLD.return_box_id AND NEW.return_box_id IS NOT NULL) THEN
        RAISE EXCEPTION 'Active Necrozma lifecycle terms are immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_necrozma_pair_sealed BEFORE UPDATE ON pokemon_necrozmacombination
 FOR EACH ROW EXECUTE FUNCTION pf2_necrozma_pair_seal();

CREATE FUNCTION pf2_necrozma_pp_mirror() RETURNS trigger AS $$
BEGIN
    -- The canonical active slot is the only live PP writer. This transactional
    -- mirror also covers bulk updates, battle drains, medicine and PP capacity.
    UPDATE pokemon_necrozmaresource r SET current_pp=NEW.current_pp
      FROM pokemon_necrozmacombination c
      WHERE c.host_id=NEW.pokemon_id AND c.move_slot=NEW.slot AND c.resource_id=r.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pf2_necrozma_active_pp AFTER UPDATE OF current_pp ON pokemon_activemoveslot
 FOR EACH ROW EXECUTE FUNCTION pf2_necrozma_pp_mirror();

CREATE FUNCTION pf2_necrozma_source_freeze() RETURNS trigger AS $$
DECLARE old_pid uuid; new_pid uuid; member uuid; role_host boolean;
BEGIN
    IF TG_TABLE_NAME='pokemon_ownedpokemon' THEN
        IF TG_OP='UPDATE' AND NEW IS DISTINCT FROM OLD AND EXISTS(
          SELECT 1 FROM pokemon_necrozmacombination WHERE companion_id=OLD.unique_id) THEN
            RAISE EXCEPTION 'Combined companion fields are frozen' USING ERRCODE='23514';
        END IF;
    ELSE
        IF TG_TABLE_NAME='pokemon_movesetslot' THEN
            IF TG_OP<>'INSERT' THEN SELECT pokemon_id INTO old_pid FROM pokemon_moveset WHERE id=OLD.moveset_id; END IF;
            IF TG_OP<>'DELETE' THEN SELECT pokemon_id INTO new_pid FROM pokemon_moveset WHERE id=NEW.moveset_id; END IF;
        ELSE
            IF TG_OP<>'INSERT' THEN old_pid:=OLD.pokemon_id; END IF;
            IF TG_OP<>'DELETE' THEN new_pid:=NEW.pokemon_id; END IF;
        END IF;
        FOR member, role_host IN SELECT host_id,true FROM pokemon_necrozmacombination WHERE host_id IN (old_pid,new_pid)
          UNION ALL SELECT companion_id,false FROM pokemon_necrozmacombination WHERE companion_id IN (old_pid,new_pid) LOOP
            IF NOT role_host THEN
                RAISE EXCEPTION 'Combined companion moves and PP are frozen' USING ERRCODE='23514';
            END IF;
            IF TG_TABLE_NAME IN ('pokemon_moveset','pokemon_movesetslot') THEN
                RAISE EXCEPTION 'Linked Necrozma movesets and source slots are locked' USING ERRCODE='23514';
            ELSIF TG_TABLE_NAME='pokemon_activemoveslot' THEN
                IF TG_OP<>'UPDATE' THEN
                    RAISE EXCEPTION 'Linked Necrozma active slots are locked' USING ERRCODE='23514';
                ELSIF NEW.pokemon_id IS DISTINCT FROM OLD.pokemon_id OR NEW.move_id IS DISTINCT FROM OLD.move_id
                  OR NEW.slot IS DISTINCT FROM OLD.slot THEN
                    RAISE EXCEPTION 'Linked Necrozma active slots are locked' USING ERRCODE='23514';
                END IF;
            END IF;
        END LOOP;
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$ LANGUAGE plpgsql;
"""

TABLES = ("necrozmacombination", "ownedpokemon", "pokemonplacement", "necrozmaresource", "moveset",
          "movesetslot", "activemoveslot", "pokemonlearnedmove", "moveppboost", "pokemonreservation",
          "activepokemonslot", "userstorage_stored_pokemon", "storagebox_pokemon", "trainer", "userstorage", "move")
FROZEN_TABLES = ("ownedpokemon", "moveset", "movesetslot", "activemoveslot", "pokemonlearnedmove", "moveppboost")


def install(apps, schema_editor):
    """Audit under table locks, then install actual deferred production checks."""
    if schema_editor.connection.vendor != "postgresql":
        return
    from pokemon.services.placement_audit import audit_placements_v3

    schema_editor.execute("LOCK TABLE " + ", ".join("pokemon_" + name for name in TABLES)
                          + " IN SHARE ROW EXCLUSIVE MODE")
    problems = list(audit_placements_v3(apps, schema_editor.connection.alias))
    if problems:
        raise RuntimeError("Necrozma integrity audit failed; no automatic repairs: " + str(problems[:20]))
    schema_editor.execute(SQL, params=None)
    for index, table in enumerate(FROZEN_TABLES):
        schema_editor.execute(f"CREATE TRIGGER pf2_necrozma_freeze_{index} BEFORE INSERT OR UPDATE OR DELETE "
            f"ON pokemon_{table} FOR EACH ROW EXECUTE FUNCTION pf2_necrozma_source_freeze()")
    for index, table in enumerate(TABLES):
        schema_editor.execute(f"CREATE CONSTRAINT TRIGGER pf2_necrozma_{index} "
            f"AFTER INSERT OR UPDATE OR DELETE ON pokemon_{table} DEFERRABLE INITIALLY DEFERRED "
            "FOR EACH ROW EXECUTE FUNCTION pf2_necrozma_guard()")


def uninstall(apps, schema_editor):
    """Remove this version's checks, without guessing a repair for active pairs."""
    if schema_editor.connection.vendor != "postgresql":
        return
    if (apps.get_model("pokemon", "NecrozmaCombination").objects.using(schema_editor.connection.alias).exists()
            or apps.get_model("pokemon", "NecrozmaResource").objects.using(schema_editor.connection.alias).exists()
            or apps.get_model("pokemon", "NecrozmaOperation").objects.using(schema_editor.connection.alias).filter(state="completed").exists()):
        raise RuntimeError("Native Necrozma data exists; rollback requires a separately reviewed data-preserving plan. No checks were removed.")
    for index, table in enumerate(TABLES):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS pf2_necrozma_{index} ON pokemon_{table}")
    for index, table in enumerate(FROZEN_TABLES):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS pf2_necrozma_freeze_{index} ON pokemon_{table}")
    schema_editor.execute("DROP TRIGGER IF EXISTS pf2_necrozma_operation_sealed ON pokemon_necrozmaoperation")
    schema_editor.execute("DROP TRIGGER IF EXISTS pf2_necrozma_pair_sealed ON pokemon_necrozmacombination")
    schema_editor.execute("DROP TRIGGER IF EXISTS pf2_necrozma_active_pp ON pokemon_activemoveslot")
    schema_editor.execute("DROP FUNCTION IF EXISTS pf2_necrozma_source_freeze(), pf2_necrozma_pair_seal(), "
                          "pf2_necrozma_pp_mirror(), pf2_necrozma_operation_seal(), pf2_necrozma_guard(), pf2_check_necrozma(uuid)")


class Migration(migrations.Migration):
    """Guard the same final canonical state across all supported writer routes."""

    dependencies = [("pokemon", "0057_necrozma_pairs")]
    operations = [migrations.RunPython(install, uninstall)]
