"""Ordinary breeding commands, elapsed-time fixtures, same-UUID hatches and rollback."""

import importlib
import json
import os
import random
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres

TRANSCRIPT = []


class BreedingCases(unittest.TestCase):
    """Use real account/character/assets; keep controlled elapsed time explicit."""

    def setUp(self):
        """Create only tagged disposable ordinary players and native eligible parents."""
        from django.utils import timezone

        accounts = [AccountDB.objects.create(username="breeding-qa-" + uuid4().hex) for _ in range(2)]
        self.player, self.other, self.alt = [ObjectDB.objects.create(db_key="Breeding QA " + uuid4().hex[:12],
            db_typeclass_path="pokemon.user.User", db_account=account) for account in (*accounts, accounts[0])]
        self.players = (self.player, self.other, self.alt)
        self.messages, self.steps, self.transports = {}, [], []
        self.now = timezone.now()
        for player in self.players:
            player.permissions.add("Player")
            player.tags.add("october-breeding-qa")
            Trainer.objects.get_or_create(user=player, defaults={"trainer_number": Trainer.objects.count() + 1})
            UserStorage.objects.get_or_create(user=player)
            Trainer.objects.filter(user=player).update(money=5000)
            self.messages[player.pk] = []
            transport = patch.object(player, "msg", side_effect=self.messages[player.pk].append)
            transport.start()
            self.transports.append(transport)
        self.parents = [create_owned_pokemon("Squirtle", self.player.trainer, 20, gender=gender, nature=nature,
            ability=ability, ivs=ivs, evs=[0] * 6, active_move_names=["Tackle", "Mirror Coat"], held_item=item)
            for gender, nature, ability, ivs, item in (("F", "Modest", "Rain Dish", [1, 2, 3, 4, 5, 6], "Everstone"),
                ("M", "Hardy", "Torrent", [20, 21, 22, 23, 24, 25], "Destiny Knot"))]
        for slot, source in zip((3, 4), self.parents):
            PlacementService(self.player.userstorage).to_party(source, slot)
            self.command(self.player, f"+daycare deposit {slot}")

    def tearDown(self):
        """Reject silent canonical custody errors and retain labelled command evidence."""
        for transport in self.transports:
            transport.stop()
        self.assertEqual(list(audit_ownership_v2(apps)), [])
        self.assertEqual(list(audit_breeding_v1(apps)), [])
        TRANSCRIPT.append({"case": self._testMethodName, "commands": self.steps,
            "transport": "captured; no socket", "time": "explicit clock-controlled elapsed-time fixture",
            "permissions": [list(player.permissions.all()) for player in self.players]})

    def service(self, player=None):
        """Control only the service clock/random seam, not player authority or persistence."""
        return Breeding(player or self.player, clock=lambda: self.now, rng=random.Random(7))

    def money(self):
        """Read the current saved wallet, including fees committed by another connection."""
        return Trainer.objects.values_list("money", flat=True).get(user_id=self.player.pk)

    def command(self, player, text):
        """Execute actual ordinary command code; capture only outbound transport."""
        start = len(self.messages[player.pk])
        if text.startswith("+daycare"):
            command, prefix = CmdDaycare(), "+daycare"
        else:
            command, prefix = CmdBreed(), "+breed"
        command.caller, command.args = player, text.removeprefix(prefix).strip()
        with patch("pokemon.services.breeding.Breeding", side_effect=lambda actor: self.service(actor)):
            command.func()
        self.steps.append({"character": player.pk, "input": text, "output": self.messages[player.pk][start:]})
        return self.messages[player.pk][-1]

    def cycle(self):
        """Start through the player route, then discover the durable identity."""
        self.command(self.player, "+breed start")
        return BreedingCycle.objects.get(origin_character_id=self.player.pk, state="producing")

    def collect(self, cycle):
        """Advance the explicit test clock, then use ordinary collection."""
        self.now = cycle.ready_at + timedelta(seconds=1)
        self.command(self.player, f"+breed collect {cycle.pk}")
        return BreedingEgg.objects.get(cycle=cycle)

    def race(self, *actions):
        """Run concurrent retries on distinct guarded PostgreSQL connections."""
        from django.db import connections

        barrier = Barrier(len(actions))
        def worker(action):
            """Keep expected refusals distinct from SQL/deadlock/programming failures."""
            try:
                barrier.wait(timeout=10)
                return action()
            except PlacementError as error:
                return error
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(worker, actions))

    def test_player_check_start_reconnect_collect_and_hatch_same_pokemon(self):
        self.assertIn("Supported offspring: Squirtle", self.command(self.player, "+breed check"))
        cycle = self.cycle()
        plan = dict(cycle.plan)
        self.assertEqual(self.money(), 4300)
        self.player.attributes.reset_cache()
        self.assertIn(str(cycle.pk), self.command(self.player, "+breed"))
        self.command(self.player, "+breed start")
        self.assertEqual(self.money(), 4300)
        self.assertIn("not ready", self.command(self.player, f"+breed collect {cycle.pk}"))
        egg = self.collect(cycle)
        self.assertEqual(egg.pk, cycle.egg_uuid)
        self.assertTrue(fresh_owned(egg.pk).is_egg)
        self.assertFalse(has_usable_pokemon(self.player))
        self.assertIn("can hatch after", self.command(self.player, f"+breed hatch {egg.pk}"))
        self.now = egg.hatch_ready_at + timedelta(seconds=1)
        self.assertIn("Hatch receipt", self.command(self.player, f"+breed hatch {egg.pk}"))
        source = fresh_owned(egg.pk)
        self.assertFalse(source.is_egg)
        for field in ("species", "gender", "nature", "ability", "ivs", "evs", "is_shiny"):
            self.assertEqual(getattr(source, field), plan[field])
        self.assertEqual(source.original_trainer_id, self.player.trainer.pk)
        self.assertEqual(source.current_hp, get_max_hp(source))
        self.assertTrue(has_usable_pokemon(self.player))
        self.assertEqual(self.money(), 4300)

    def test_concurrent_start_collection_and_hatch_have_one_charge_and_one_egg(self):
        started = self.race(lambda: self.service().start(), lambda: self.service().start())
        self.assertEqual(started[0].pk, started[1].pk)
        cycle = started[0]
        self.assertEqual(self.money(), 4300)
        self.now = cycle.ready_at + timedelta(seconds=1)
        receipts = self.race(lambda: self.service().collect(cycle.pk), lambda: self.service().collect(cycle.pk))
        self.assertEqual(receipts[0], receipts[1])
        egg = BreedingEgg.objects.get(cycle=cycle)
        self.now = egg.hatch_ready_at + timedelta(seconds=1)
        receipts = self.race(lambda: self.service().hatch(egg.pk), lambda: self.service().hatch(egg.pk))
        self.assertEqual(receipts[0], receipts[1])
        self.assertEqual(OwnedPokemon.objects.filter(pk=cycle.egg_uuid).count(), 1)

    def test_cancel_releases_parents_but_preserves_fee_outcome_and_uuid_cooldown(self):
        cycle = self.cycle()
        plan = dict(cycle.plan)
        self.command(self.player, f"+breed cancel {cycle.pk}")
        self.command(self.player, f"+breed cancel {cycle.pk}")
        self.assertEqual(self.money(), 4300)
        self.assertFalse(OwnedPokemon.objects.filter(pk=cycle.egg_uuid).exists())
        self.assertIn("cancelled", self.command(self.player, f"+breed collect {cycle.pk}"))
        for entry in DaycareEntry.objects.filter(storage=self.player.userstorage, state="active"):
            self.command(self.player, f"+daycare retrieve {entry.pk}")
        for source in self.parents:
            self.command(self.player, f"+daycare deposit {source.pk}")
        self.assertIn("cooling down", self.command(self.player, "+breed start"))
        self.assertEqual(self.money(), 4100)
        cycle.refresh_from_db()
        self.assertEqual(cycle.plan, plan)

    def test_active_cycle_blocks_parent_retrieval_and_foreign_alt_operations(self):
        cycle = self.cycle()
        entry = DaycareEntry.objects.get(pk=cycle.parent_a_id)
        self.assertIn("active breeding", self.command(self.player, f"+daycare retrieve {entry.pk}"))
        for actor in (self.other, self.alt):
            for action in ("collect", "cancel"):
                self.assertIn("does not belong", self.command(actor, f"+breed {action} {cycle.pk}"))
        self.assertEqual(self.money(), 4300)

    def test_invalid_pair_and_insufficient_money_have_no_cycle_fee(self):
        OwnedPokemon.objects.filter(pk=self.parents[1].pk).update(gender="F")
        self.assertIn("opposite genders", self.command(self.player, "+breed start"))
        self.assertEqual(self.money(), 4800)
        self.assertFalse(BreedingCycle.objects.filter(origin_character_id=self.player.pk).exists())
        OwnedPokemon.objects.filter(pk=self.parents[1].pk).update(gender="M")
        Trainer.objects.filter(user=self.player).update(money=499)
        self.assertIn("costs 500", self.command(self.player, "+breed start"))
        self.assertEqual(self.money(), 499)

    def test_creation_fault_after_fee_rolls_back_cooldown_and_parent_references(self):
        from django.db.models.query import QuerySet

        original = QuerySet.update
        def fail_fee(query, **values):
            """Fail after the actual fee, following durable plan and parent writes."""
            result = original(query, **values)
            if query.model is Trainer and "money" in values:
                raise RuntimeError("breeding fee fault")
            return result
        with patch.object(QuerySet, "update", fail_fee), self.assertRaisesRegex(RuntimeError, "fee"):
            self.service().start()
        self.assertEqual(self.money(), 4800)
        self.assertFalse(BreedingCycle.objects.filter(origin_character_id=self.player.pk).exists())
        self.assertFalse(DaycareEntry.objects.filter(storage=self.player.userstorage, active_cycle__isnull=False).exists())
        self.assertEqual(self.service().start().fee, 500)

    def test_collection_and_hatch_faults_restore_prior_state_and_retry_same_identity(self):
        cycle = self.cycle()
        self.now = cycle.ready_at + timedelta(seconds=1)
        with patch.object(BreedingCycle, "save", side_effect=RuntimeError("collection receipt fault")), self.assertRaises(RuntimeError):
            self.service().collect(cycle.pk)
        self.assertFalse(OwnedPokemon.objects.filter(pk=cycle.egg_uuid).exists())
        self.assertFalse(BreedingEgg.objects.filter(cycle=cycle).exists())
        cycle.refresh_from_db()
        self.assertEqual(cycle.state, "producing")
        self.service().collect(cycle.pk)
        egg = BreedingEgg.objects.get(cycle=cycle)
        self.now = egg.hatch_ready_at + timedelta(seconds=1)
        with patch.object(BreedingEgg, "save", side_effect=RuntimeError("hatch receipt fault")), self.assertRaises(RuntimeError):
            self.service().hatch(egg.pk)
        self.assertTrue(fresh_owned(egg.pk).is_egg)
        egg.refresh_from_db()
        self.assertIsNone(egg.hatched_at)
        self.service().hatch(egg.pk)
        self.assertFalse(fresh_owned(egg.pk).is_egg)

    def test_traded_egg_uses_current_owner_and_hatcher_as_original_trainer(self):
        cycle = self.cycle()
        egg = self.collect(cycle)
        offer = TradeOffers(self.player).propose(self.other.key, str(egg.pk))
        TradeOffers(self.other).inspect(offer.pk)
        TradeOffers(self.other).accept(offer.pk)
        self.now = egg.hatch_ready_at + timedelta(seconds=1)
        self.assertIn("does not belong", self.command(self.player, f"+breed hatch {egg.pk}"))
        self.assertIn(str(egg.pk), self.command(self.other, "+breed"))
        self.assertIn("Hatch receipt", self.command(self.other, f"+breed hatch {egg.pk}"))
        self.assertEqual(fresh_owned(egg.pk).original_trainer_id, self.other.trainer.pk)

    def test_full_party_collection_uses_box_and_replay_never_recreates_released_egg(self):
        for slot in range(1, 7):
            source = create_owned_pokemon("Pikachu", self.player.trainer, 5, active_move_names=["Tackle"])
            PlacementService(self.player.userstorage).to_party(source, slot)
        cycle = self.cycle()
        egg = self.collect(cycle)
        self.assertEqual(PokemonPlacement.objects.get(pokemon_id=egg.pk).location_type, "box")
        receipt = self.service().collect(cycle.pk)
        PlacementService(self.player.userstorage).release(fresh_owned(egg.pk))
        self.assertEqual(self.service().collect(cycle.pk), receipt)
        self.assertFalse(OwnedPokemon.objects.filter(pk=egg.pk).exists())
        with self.assertRaises(PlacementError):
            self.service().hatch(egg.pk)

    def test_database_seals_traits_cooldowns_and_active_parent_links(self):
        from django.db import IntegrityError, transaction

        cycle = self.cycle()
        for mutation in (lambda: BreedingCycle.objects.filter(pk=cycle.pk).update(plan={}),
                lambda: BreedingCycle.objects.filter(pk=cycle.pk).update(next_ready_at=self.now),
                lambda: DaycareEntry.objects.filter(pk=cycle.parent_a_id).update(active_cycle=None),
                lambda: BreedingCycle.objects.filter(pk=cycle.pk).delete()):
            with self.assertRaises(IntegrityError), transaction.atomic():
                mutation()

    def test_database_requires_matching_egg_flag_and_retains_hatch_receipt(self):
        from django.db import IntegrityError, transaction

        cycle = self.cycle()
        egg = self.collect(cycle)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnedPokemon.objects.filter(pk=egg.pk).update(is_egg=False)
        self.now = egg.hatch_ready_at + timedelta(seconds=1)
        self.service().hatch(egg.pk)
        for mutation in (lambda: BreedingEgg.objects.filter(pk=egg.pk).update(hatch_receipt={}),
                lambda: BreedingEgg.objects.filter(pk=egg.pk).delete()):
            with self.assertRaises(IntegrityError), transaction.atomic():
                mutation()

    def test_staff_inspection_is_read_only_and_preserves_the_recorded_outcome(self):
        import io
        from django.core.management import call_command

        cycle = self.cycle()
        before = (self.money(), list(BreedingCycle.objects.filter(pk=cycle.pk).values()))
        output = io.StringIO()
        call_command("audit_pokemon_breeding", cycle=str(cycle.pk), stdout=output)
        self.assertIn(str(cycle.egg_uuid), output.getvalue())
        self.assertIn("No data was changed", output.getvalue())
        self.assertEqual(before, (self.money(), list(BreedingCycle.objects.filter(pk=cycle.pk).values())))

    def test_ordinary_egg_battle_and_field_item_routes_refuse_before_spending(self):
        cycle = self.cycle()
        egg = self.collect(cycle)
        start = len(self.messages[self.player.pk])
        command = CmdPvpCreate()
        command.caller, command.args = self.player, "single"
        command.func()
        self.assertIn("able to battle", self.messages[self.player.pk][-1])
        self.assertFalse(self.player.db.pvp_locked)
        self.steps.append({"character": self.player.pk, "input": "+pvp/create single",
                           "output": self.messages[self.player.pk][start:]})
        self.player.trainer.add_item("Potion", 1)
        slot = PokemonPlacement.objects.get(pokemon_id=egg.pk).slot
        start = len(self.messages[self.player.pk])
        command = CmdUseItem()
        command.caller, command.args = self.player, f"Potion={slot}"
        command.func()
        self.assertIn("egg", self.messages[self.player.pk][-1].lower())
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        self.steps.append({"character": self.player.pk, "input": f"+use Potion={slot}",
                           "output": self.messages[self.player.pk][start:]})


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from django.db import connection
        from evennia.accounts.models import AccountDB
        from evennia.objects.models import ObjectDB
        ContentType.objects.get_for_models(*apps.get_models(), for_concrete_models=False)
        with connection.schema_editor() as editor:
            for name in ("0041_placement_integrity_triggers", "0048_ownership_integrity", "0050_market_integrity", "0052_daycare_integrity", "0054_breeding_integrity"):
                importlib.import_module("pokemon.migrations." + name).install(apps, editor)
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_breed import CmdBreed
            from commands.player.cmd_daycare import CmdDaycare
            from commands.player.cmd_pvp import CmdPvpCreate
            from commands.player.cmd_inventory import CmdUseItem
        from pokemon.helpers.party_helpers import has_usable_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.breeding import BreedingCycle, BreedingEgg
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.daycare import DaycareEntry
        from pokemon.models.storage import PokemonPlacement, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.breeding import Breeding
        from pokemon.services.breeding_audit import audit_breeding_v1
        from pokemon.services.ownership import fresh_owned
        from pokemon.services.ownership_audit import audit_ownership_v2
        from pokemon.services.placement import PlacementError, PlacementService
        from pokemon.services.trading import TradeOffers
        try:
            unittest.main(verbosity=2)
        finally:
            if os.environ.get("PF2_BREEDING_PLAYER_EVIDENCE"):
                Path(os.environ["PF2_BREEDING_PLAYER_EVIDENCE"]).write_text(json.dumps(TRANSCRIPT, indent=2, default=str), encoding="utf-8")
