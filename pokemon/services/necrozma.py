"""Atomic, free native Necrozma combination over two real owned sources."""

from copy import copy
from datetime import timedelta
import json
from uuid import UUID, uuid4

from django.db import connection, transaction
from django.utils import timezone

from pokemon.names import normalize_name
from pokemon.services.battle_rewards import BattleRewards
from pokemon.services.necrozma_audit import PAIRS
from pokemon.services.necrozma_guards import NecrozmaError, assert_human, current_pair
from pokemon.services.ownership import (
    acting_character, assert_character_free, assert_transferable, fresh_owned, locked_owners,
)
from pokemon.services.placement import PlacementService


def json_state(value):
    """Give SQL UUID/date/array values a stable JSON representation for exact terms."""
    return json.loads(json.dumps(value, default=str, sort_keys=True))


class NecrozmaService:
    """Lock character → storage → trainer → UUID-ordered sources before writes."""

    def __init__(self, actor):
        """Never grant an account or same-account alt authority over a source."""
        self.character = acting_character(actor)
        self.actor_id = self.character.pk

    @staticmethod
    def _wrote(stage):
        """Named fault boundary for checking complete rollback after durable writes."""

    def _environment(self, character):
        """Use fresh SQL location and saved human/battle state inside the lock."""
        from evennia.objects.models import ObjectDB

        assert_character_free(character)
        assert_human(character)
        location = ObjectDB.objects.filter(pk=self.actor_id).values_list("db_location_id", flat=True).get()
        room = ObjectDB.objects.filter(pk=location).first()
        if room is None or BattleRewards.stored_attribute(room, "is_pokemon_center") is not True:
            raise NecrozmaError("Combine or separate at a Pokemon Center.")

    @staticmethod
    def resolve(storage, selector):
        """Keep gapped canonical slots; boxed selectors require a complete owned UUID."""
        from pokemon.models.storage import PokemonPlacement

        text = str(selector or "").strip()
        if text.isdigit():
            if int(text) not in range(1, 7):
                raise NecrozmaError("Choose a party slot from 1 to 6, or a full owned UUID.")
            identifier = PokemonPlacement.objects.filter(storage=storage, location_type="party", slot=int(text)).values_list(
                "pokemon_id", flat=True).first()
            if identifier is None:
                raise NecrozmaError("No Pokemon is in that canonical party slot.")
            return identifier
        try:
            identifier = UUID(text)
        except (ValueError, TypeError, AttributeError) as error:
            raise NecrozmaError("Use a canonical party slot or full owned UUID; names are not selectors.") from error
        if str(identifier) != text.lower() or not PokemonPlacement.objects.filter(storage=storage, pokemon_id=identifier).exists():
            raise NecrozmaError("Choose a Pokemon owned by this character using its full UUID.")
        return identifier

    @staticmethod
    def _sources(storage, trainer, identifiers):
        """Read fresh rows in UUID order and work on detached model instances."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        identifiers = sorted(set(identifiers), key=str)
        rows = list(OwnedPokemon.objects.select_for_update().filter(pk__in=identifiers).order_by("pk").values())
        if len(rows) != len(identifiers) or any(row["trainer_id"] != trainer.pk for row in rows):
            raise NecrozmaError("Both sources must still belong to this character.")
        result = {}
        for row in rows:
            # Avoid publishing an uncommitted form through Evennia's identity map.
            pokemon = copy(fresh_owned(row["unique_id"]))
            pokemon._state = copy(pokemon._state)
            result[pokemon.pk] = pokemon
        placements = {row.pokemon_id: row for row in PokemonPlacement.objects.select_for_update().filter(
            storage=storage, pokemon_id__in=identifiers).order_by("pokemon_id")}
        if len(placements) != len(identifiers):
            raise NecrozmaError("A source has no valid canonical placement; ask staff to inspect it.")
        for placement in placements.values():
            placement.full_clean()
        return result, placements

    @staticmethod
    def _snapshot(sources, placements):
        """Bind review to current sources, moves, PP, boosts, hints and resources."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.necrozma import NecrozmaResource
        from pokemon.models.storage import PokemonPlacement

        ids = list(sources)
        return json_state({
            "sources": list(OwnedPokemon.objects.filter(pk__in=ids).order_by("pk").values()),
            "placements": list(PokemonPlacement.objects.filter(pk__in=[p.pk for p in placements.values()]).order_by("pokemon_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon_id__in=ids).order_by("pokemon_id", "slot").values(
                "id", "pokemon_id", "slot", "move_id", "move__name", "current_pp")),
            "saved": list(MovesetSlot.objects.filter(moveset__pokemon_id__in=ids).order_by("moveset_id", "slot").values()),
            "learned": list(PokemonLearnedMove.objects.filter(pokemon_id__in=ids).order_by("pokemon_id", "move_id").values()),
            "boosts": list(MovePPBoost.objects.filter(pokemon_id__in=ids).order_by("pokemon_id", "move_id").values()),
            "resources": list(NecrozmaResource.objects.select_for_update().filter(host_id__in=ids).order_by("host_id", "source").values()),
        })

    def _terms(self, action, host, companion, slot, storage, trainer, *, lifecycle):
        """Recreate current authoritative terms; never accept a client snapshot."""
        from pokemon.models.moves import ActiveMoveslot, Moveset, MovesetSlot
        from pokemon.models.necrozma import NecrozmaOperation, NecrozmaResource
        from pokemon.services.pp_capacity import PPCapacity

        sources, placements = self._sources(storage, trainer, (host, companion))
        pokemon, partner = sources[host], sources[companion]
        if host == companion:
            raise NecrozmaError("Choose two distinct owned sources.")
        if action == "separate":
            pair = current_pair(host)
            if not pair or str(pair["id"]) != str(lifecycle) or pair["host_id"] != host or pair["companion_id"] != companion:
                raise NecrozmaError("That lifecycle is no longer active. Inspect the current pair.")
            source, target, slot = PAIRS[pair["target_species"]][1], pair["target_species"], pair["move_slot"]
        else:
            for mon in (pokemon, partner):
                if current_pair(mon.pk):
                    raise NecrozmaError("Separate the existing pair before choosing another companion.")
                _, place = PlacementService(storage)._pokemon(mon, storage)
                assert_transferable(self.character, mon, place)
                if mon.is_egg or mon.current_hp <= 0 or mon.current_hp > mon.get_max_hp():
                    raise NecrozmaError("Both native non-egg sources must be conscious with valid HP.")
            if pokemon.species != "Necrozma" or pokemon.ability != "Prism Armor":
                raise NecrozmaError("Choose actual base Necrozma with its native Prism Armor.")
            matches = [(target, spec) for target, spec in PAIRS.items() if spec[0] == partner.species and spec[2] == partner.ability]
            if len(matches) != 1:
                raise NecrozmaError("Choose actual native Solgaleo or Lunala as the companion.")
            target, spec = matches[0]
            source = spec[1]
            if type(slot) is not int or slot not in range(1, 5):
                raise NecrozmaError("Select the real source move slot from 1 to 4.")
            if not pokemon.active_moveset_id or not Moveset.objects.filter(pk=pokemon.active_moveset_id, pokemon_id=host).exists():
                raise NecrozmaError("Necrozma needs its own valid active moveset before combining.")
            active_rows = list(ActiveMoveslot.objects.filter(pokemon_id=host).select_related("move").order_by("slot"))
            saved_rows = dict(MovesetSlot.objects.filter(moveset_id=pokemon.active_moveset_id).values_list("slot", "move_id"))
            learned_ids = set(pokemon.learned_moves.values_list("pk", flat=True))
            if ({row.slot: row.move_id for row in active_rows} != saved_rows
                    or len({normalize_name(row.move.name) for row in active_rows}) != len(active_rows)
                    or any(row.slot not in range(1, 5) or row.move_id not in learned_ids
                        or row.current_pp is None or not 0 <= row.current_pp <= pokemon.get_max_pp(row.move.name)
                        for row in active_rows)):
                raise NecrozmaError("The active/saved/learned moves and PP must be consistent before combining.")
            for row in [*pokemon.learned_moves.all(), *(s.move for s in pokemon.activemoveslot_set.select_related("move")),
                        *(s.move for s in MovesetSlot.objects.filter(moveset__pokemon_id=host).select_related("move"))]:
                if normalize_name(row.name) in {"sunsteelstrike", "moongeistbeam"}:
                    raise NecrozmaError("Unexpected existing form-source knowledge needs staff review.")
            active = ActiveMoveslot.objects.filter(pokemon_id=host, slot=slot).select_related("move").first()
            saved = MovesetSlot.objects.filter(moveset_id=pokemon.active_moveset_id, slot=slot).first()
            if bool(active) != bool(saved) or active and active.move_id != saved.move_id:
                raise NecrozmaError("The selected active/saved move slot is inconsistent.")
            if active and (active.current_pp is None or not 0 <= active.current_pp <= pokemon.get_max_pp(active.move.name)):
                raise NecrozmaError("The displaced move's saved PP needs staff review.")
            resource = NecrozmaResource.objects.select_for_update().filter(host_id=host, source=source).first()
            used = NecrozmaOperation.objects.filter(action="combine", state="completed", terms__host=str(host), terms__source=source).exists()
            bonus = next((row.bonus_pp for row in pokemon.pp_boosts.select_related("move") if normalize_name(row.move.name) == normalize_name(source)), 0)
            if bool(resource) != used or (not resource and bonus):
                raise NecrozmaError("Missing or contradictory form-source PP history needs staff review; no refill was made.")
            if resource and (resource.policy_version != 1 or not 0 <= resource.current_pp <= PPCapacity.for_move(source).base + bonus):
                raise NecrozmaError("Invalid saved form-source PP resource.")
        return ({"host": str(host), "companion": str(companion), "slot": slot, "source": source,
                 "target": target, "lifecycle": str(lifecycle), "version": 1,
                 "snapshot": self._snapshot(sources, placements)}, sources, placements)

    def prepare(self, action, host_selector, companion_selector=None, slot=None, *, request_id=None):
        """Create a five-minute exact-terms review without changing either source."""
        from pokemon.models.necrozma import NecrozmaOperation

        if action not in {"combine", "separate"}:
            raise NecrozmaError("Choose combine or separate.")
        request_id = UUID(str(request_id)) if request_id else uuid4()
        with locked_owners((self.actor_id,)) as (characters, storages, trainers):
            character, storage, trainer = characters[self.actor_id], storages[self.actor_id], trainers[self.actor_id]
            self._environment(character)
            host = self.resolve(storage, host_selector)
            if action == "separate":
                pair = current_pair(host)
                if not pair or pair["host_id"] != host:
                    raise NecrozmaError("Choose the actual host of an active native Necrozma pair.")
                companion, lifecycle, slot = pair["companion_id"], pair["id"], pair["move_slot"]
            else:
                companion, lifecycle = self.resolve(storage, companion_selector), uuid4()
            old = NecrozmaOperation.objects.select_for_update().filter(pk=request_id).first()
            if old:
                if old.storage_id != storage.pk or old.action != action or old.terms["host"] != str(host) or old.terms["companion"] != str(companion) or old.terms["slot"] != slot:
                    raise NecrozmaError("That request belongs to different terms.")
                return old
            terms, _, _ = self._terms(action, host, companion, slot, storage, trainer, lifecycle=lifecycle)
            return NecrozmaOperation.objects.create(id=request_id, storage=storage, action=action,
                terms=terms, expires_at=timezone.now() + timedelta(minutes=5))

    def commit(self, request_id):
        """Commit the reviewed lifecycle once, or return its immutable prior result."""
        from pokemon.models.necrozma import NecrozmaOperation

        identifiers = set()
        try:
            with locked_owners((self.actor_id,)) as (characters, storages, trainers):
                character, storage, trainer = characters[self.actor_id], storages[self.actor_id], trainers[self.actor_id]
                operation = NecrozmaOperation.objects.select_for_update().filter(pk=request_id, storage=storage).first()
                if operation is None:
                    raise NecrozmaError("That native-pair request does not belong to this character.")
                if operation.state == "completed":
                    return operation.result, False
                if operation.state != "pending":
                    raise NecrozmaError("That native-pair review is no longer pending.")
                if operation.expires_at <= timezone.now():
                    operation.state = "expired"
                    operation.save(update_fields=["state"])
                    return {"error": "That review expired. Inspect the sources and start again."}, False
                self._environment(character)
                old = operation.terms
                host, companion = UUID(old["host"]), UUID(old["companion"])
                identifiers = {host, companion}
                terms, sources, placements = self._terms(operation.action, host, companion, old["slot"],
                    storage, trainer, lifecycle=old["lifecycle"])
                if terms != old:
                    raise NecrozmaError("That review is stale. Inspect the current sources and start again.")
                if operation.action == "combine":
                    result = self._combine(storage, terms, sources, placements)
                else:
                    result = self._separate(storage, terms, sources, placements)
                operation.state, operation.completed_at, operation.result = "completed", timezone.now(), result
                operation.save(update_fields=["state", "completed_at", "result"])
                self._wrote("receipt")
                return result, True
        finally:
            self._resync(identifiers)

    def cancel(self, request_id):
        """Cancel only this character's pending review; retain completed history."""
        from pokemon.models.necrozma import NecrozmaOperation

        with locked_owners((self.actor_id,)) as (_, storages, __):
            operation = NecrozmaOperation.objects.select_for_update().filter(pk=request_id,
                storage=storages[self.actor_id]).first()
            if operation is None:
                raise NecrozmaError("That review does not belong to this character.")
            if operation.state == "pending":
                operation.state = "cancelled"
                operation.save(update_fields=["state"])
                return True
            return False

    def _combine(self, storage, terms, sources, placements):
        """Persist the host, source, companion custody and live link in one commit."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.models.moves import ActiveMoveslot, Move, MovesetSlot, PokemonLearnedMove
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import PokemonPlacement, _sync_legacy_storage_relations

        host, partner = sources[UUID(terms["host"])], sources[UUID(terms["companion"])]
        place = placements[partner.pk]
        displaced = ActiveMoveslot.objects.filter(pokemon=host, slot=terms["slot"]).first()
        old_name, old_hp, old_max = host.name, host.current_hp, get_max_hp(host)
        host.species, host.ability = terms["target"], "Prism Armor"
        host.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(host)["hp"]
        host.current_hp = max(1, min(new_max, old_hp + new_max - old_max))
        host.save(update_fields=["species", "ability", "current_hp"])
        self._wrote("host_form")
        resource, _ = NecrozmaResource.objects.get_or_create(host=host, source=terms["source"], defaults={"current_pp": 5})
        self._wrote("resource")
        move, _ = Move.objects.get_or_create(name=terms["source"])
        PokemonLearnedMove.objects.create(pokemon=host, move=move)
        self._wrote("learned_source")
        pair = NecrozmaCombination(id=UUID(terms["lifecycle"]), storage=storage, host=host, companion=partner,
            target_species=terms["target"], resource=resource, moveset_id=host.active_moveset_id, move_slot=terms["slot"],
            displaced_move_id=displaced.move_id if displaced else None,
            displaced_pp=displaced.current_pp if displaced else None, return_type=place.location_type,
            return_slot=place.slot, return_box_id=place.box_id)
        ActiveMoveslot.objects.update_or_create(pokemon=host, slot=pair.move_slot, defaults={"move": move, "current_pp": resource.current_pp})
        self._wrote("active_source")
        MovesetSlot.objects.update_or_create(moveset_id=pair.moveset_id, slot=pair.move_slot, defaults={"move": move})
        self._wrote("saved_source")
        # The FK is deferred: install the live pair last, after its complete
        # source binding, so the same DB freeze guards apply to every later writer.
        PokemonPlacement.objects.filter(pk=place.pk).update(location_type="combined", slot=None,
            box=None, box_position=None, combination_id=pair.pk)
        self._wrote("companion_placement")
        _sync_legacy_storage_relations(storage, partner)
        self._wrote("companion_mirrors")
        pair.save()
        self._wrote("pair")
        return {"action": "combine", "host": str(host.pk), "companion": str(partner.pk),
                "lifecycle": str(pair.pk), "old_name": old_name,
                "target": host.species, "source": terms["source"], "slot": pair.move_slot,
                "pp": resource.current_pp, "host_name": host.name}

    def _separate(self, storage, terms, sources, placements):
        """Restore one displaced slot and current host health, then release the link."""
        from pokemon.helpers.pokemon_helpers import get_max_hp, refresh_stats
        from pokemon.models.moves import ActiveMoveslot, MovesetSlot, PokemonLearnedMove
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import StorageBox

        host, partner = sources[UUID(terms["host"])], sources[UUID(terms["companion"])]
        pair = NecrozmaCombination.objects.select_for_update().get(pk=terms["lifecycle"])
        active = ActiveMoveslot.objects.select_for_update().get(pokemon=host, slot=pair.move_slot)
        NecrozmaResource.objects.filter(pk=pair.resource_id).update(current_pp=active.current_pp)
        self._wrote("resource")
        service, current = PlacementService(storage), placements[partner.pk]
        box = StorageBox.objects.filter(pk=pair.return_box_id, storage=storage).first() if pair.return_box_id else None
        occupied = set(storage.placements.filter(location_type="party").values_list("slot", flat=True))
        if pair.return_type == "box" and box:
            returned = service._box(partner, storage, current, box, allow_combined=True)
        elif len(occupied) < 6:
            slot = pair.return_slot if pair.return_slot not in occupied else None
            returned = service._party(partner, storage, current, slot, allow_combined=True)
        else:
            returned = service._box(partner, storage, current, allow_combined=True)
        self._wrote("companion_return")
        # Placement no longer references this pair. Remove its live FK protection
        # before restoring the host; the outer transaction still owns every lock.
        lifecycle = str(pair.pk)
        pair.delete()
        self._wrote("pair_removed")
        source_move_id = active.move_id
        if pair.displaced_move_id is None:
            active.delete()
            MovesetSlot.objects.filter(moveset_id=pair.moveset_id, slot=pair.move_slot).delete()
        else:
            active.move_id, active.current_pp = pair.displaced_move_id, pair.displaced_pp
            active.save(update_fields=["move", "current_pp"])
            MovesetSlot.objects.filter(moveset_id=pair.moveset_id, slot=pair.move_slot).update(move_id=pair.displaced_move_id)
        self._wrote("source_removed")
        PokemonLearnedMove.objects.filter(pokemon=host, move_id=source_move_id).delete()
        self._wrote("learned_source_removed")
        old_name, old_hp, old_max = host.name, host.current_hp, get_max_hp(host)
        host.species, host.ability = "Necrozma", "Prism Armor"
        host.__dict__.pop("_cached_stats", None)
        new_max = refresh_stats(host)["hp"]
        host.current_hp = 0 if old_hp <= 0 else max(1, min(new_max, old_hp + new_max - old_max))
        host.save(update_fields=["species", "ability", "current_hp"])
        self._wrote("host_form")
        return {"action": "separate", "host": str(host.pk), "companion": str(partner.pk),
                "lifecycle": lifecycle, "old_name": old_name, "host_name": host.name,
                "target": host.species, "return": {"location": returned.location_type, "slot": returned.slot,
                    "box": returned.box.name if returned.box_id else None, "position": returned.box_position}}

    @staticmethod
    def _resync(identifiers):
        """Never publish intermediate forms or resurrect an already released source."""
        from pokemon.models.core import OwnedPokemon

        def refresh():
            for identifier in identifiers:
                if OwnedPokemon.objects.filter(pk=identifier).exists():
                    fresh_owned(identifier)

        for identifier in identifiers:
            cached = OwnedPokemon.get_cached_instance(identifier)
            if cached is not None:
                OwnedPokemon.flush_cached_instance(cached)
        if connection.in_atomic_block:
            transaction.on_commit(refresh, robust=True)
        else:
            refresh()
