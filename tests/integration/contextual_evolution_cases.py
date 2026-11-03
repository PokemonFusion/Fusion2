"""Public day/night authoring, actual travel, finite purchase and current native evolutions."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []
MAPPINGS = (("Happiny", "Chansey", "Oval Stone", "day"),
            ("Sneasel", "Weavile", "Razor Claw", "night"),
            ("Gligar", "Gliscor", "Razor Fang", "night"))


class ContextualEvolutionCases(unittest.TestCase):
    """Use production owner/item/context transactions with captured transport."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Explicitly author a disposable hub/counter/groves, never existing world rooms."""
        from django.contrib.contenttypes.models import ContentType
        from evennia.utils.create import create_object
        from pokemon.services.item_activity_routes import DAY_GROVE, NIGHT_GROVE
        from pokemon.services.item_counter import ItemCounter

        acquisition.AcquisitionCases.setUp(self)
        ContentType.objects.get_for_model(ObjectDB)
        self.hub = create_object("typeclasses.rooms.FusionRoom", key="Context source fixture", nohome=True)
        made = [self.hub.pk]
        self.addCleanup(lambda: ObjectDB.objects.filter(pk__in=made).delete())
        self.counter = ItemCounter("world/contextual_evolution_counter.json")
        self.counter_room = self.counter.install(self.hub)
        self.groves = {"day": DAY_GROVE.install(self.hub), "night": NIGHT_GROVE.install(self.hub)}
        for room in (self.counter_room, *self.groves.values()):
            made.extend([room.pk, *ObjectDB.objects.filter(db_destination=room).values_list("pk", flat=True),
                         *ObjectDB.objects.filter(db_location=room).values_list("pk", flat=True)])
        self.player.character.move_to(self.hub, quiet=True)
        self.player.location = self.room = self.hub

    def travel(self, name):
        """Run an actual exit command; only captured-client movement transport is adapted."""
        entrance = ObjectDB.objects.get(db_location=self.room, db_key=name)
        self.assertTrue(entrance.access(self.player.character, "call", no_superuser_bypass=True))

        def move(destination, **kwargs):
            moved = self.player.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = self.room = destination
            return moved

        self.player.move_to = move
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.assertEqual(ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=self.player.pk), entrance.db_destination_id)
        EVIDENCE.append({"label": "ordinary-context-travel", "exit": name, "room": self.room.pk})

    def prepare(self, species, level=50, *, item=None):
        """Prepare only native owned prerequisites, retaining current canonical slot 3."""
        from pokemon.dex import POKEDEX
        from pokemon.names import resolve_dex_entry

        PlacementService(self.player.storage).to_box(self.mon)
        data = resolve_dex_entry(POKEDEX, species).raw
        self.mon = create_owned_pokemon(species, self.player.trainer, level,
            nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            ability=data["abilities"]["0"], gender=data.get("gender", "M"))
        self.mons.append(self.mon)
        PlacementService(self.player.storage).to_party(self.mon, slot=3)
        if item:
            self.player.trainer.add_item(item, 1)
            self.command("hold", "3=" + item)
            self.assertEqual(self.row()["held_item"], item)

    def row(self):
        """Read current species/item/owner directly from SQL."""
        return OwnedPokemon.objects.values().get(pk=self.mon.pk)

    def evolve(self):
        """Exercise the ordinary parser and retain exact refusal or committed results."""
        before = self.row()
        output = self.command("evolve", str(self.mon.pk))
        EVIDENCE.append({"label": "ordinary-context-evolution", "command": "+evolve " + str(self.mon.pk),
                         "before": before, "after": self.row(), "output": output})
        return output

    def test_actual_buy_hold_travel_evolve_retry_and_reload(self):
        """All three finite offers reach their exact native targets and spend only the held copy."""
        from django.db import connection
        from pokemon.services.battle_rewards import BattleRewards

        self.travel("evolutionitems")
        self.command("store")
        self.reply("1")
        for _, _, item, _ in MAPPINGS:
            self.reply(item + " 1")
            self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        self.reply("q")
        self.assertEqual(self.state()["wallet"], 188000)
        paid = BattleRewards.stored_attribute(self.counter_room, "store_inventory")
        self.assertEqual(self.counter.install(self.hub).pk, self.counter_room.pk)
        self.assertEqual(BattleRewards.stored_attribute(self.counter_room, "store_inventory"), paid)
        self.travel("back")
        for species, target, item, context in MAPPINGS:
            self.prepare(species)
            self.command("hold", "3=" + item)
            self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
            self.travel("daygrove" if context == "day" else "nightgrove")
            before = self.row()
            self.evolve()
            self.assertEqual((self.row()["species"], self.row()["held_item"]), (target, ""))
            for field in ("trainer_id", "level", "total_exp", "ivs", "evs", "nature"):
                self.assertEqual(self.row()[field], before[field])
            after = self.row()
            self.evolve()
            self.assertEqual(self.row(), after)
            connection.close()
            self.assertEqual(self.row(), after)
            self.travel("back")

    def test_valid_level_boundaries_and_wrong_time_preserve_real_copy(self):
        """These dex entries require context, not an invented species-specific minimum level."""
        for species, target, item, context in MAPPINGS:
            for level in (1, 50, 100):
                self.prepare(species, level, item=item)
                wrong = "night" if context == "day" else "day"
                self.travel(wrong + "grove")
                before = self.row()
                self.evolve()
                self.assertEqual(self.row(), before)
                self.travel("back")
                self.travel(context + "grove")
                self.evolve()
                self.assertEqual(self.row()["species"], target)
                self.assertEqual(self.row()["level"], level)
                self.assertEqual(self.row()["held_item"], "")
                self.travel("back")

    def test_actual_position_overrides_stale_caller_room_and_flag_cache(self):
        """A stale night pointer cannot authorize a Pokemon now standing in Day Grove."""
        from pokemon.services.battle_rewards import BattleRewards

        self.prepare("Gligar", item="Razor Fang")
        self.travel("nightgrove")
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.groves["day"].pk)
        before = self.row()
        self.evolve()
        self.assertEqual(self.row(), before)
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.groves["night"].pk)
        self.groves["night"].db.time_of_day = "day"
        self.evolve()
        self.assertEqual(self.row(), before)
        self.groves["night"].db.time_of_day = "night"
        self.evolve()
        self.assertEqual(self.row()["species"], "Gliscor")

    def test_wrong_native_held_level_owner_egg_fusion_and_reservation_guards(self):
        """No refused request consumes the genuine held item or writes another branch."""
        from pokemon.services.ownership import PokemonReservations

        self.travel("nightgrove")
        self.prepare("Gligar", item="Razor Fang")
        for field, invalid in (("level", 0), ("level", 101), ("is_egg", True),
                               ("held_item", "Razor Claw"), ("species", "Mew"),
                               ("trainer_id", self.players[1].trainer.pk)):
            previous = self.row()[field]
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: invalid})
            before = self.row()
            self.evolve()
            self.assertEqual(self.row(), before)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: previous})
        self.player.character.db.battle_lock = "context-fixture-battle"
        before = self.row()
        self.evolve()
        self.assertEqual(self.row(), before)
        self.player.character.db.battle_lock = None
        token = uuid4()
        reservations = PokemonReservations(self.player)
        reservations.claim("market", [self.mon.pk], token)
        self.evolve()
        self.assertEqual(self.row(), before)
        reservations.release("market", token)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.character.db.fusion_id = str(self.mon.pk)
        self.evolve()
        self.assertEqual(self.row(), before)
        self.player.character.db.fusion_id = None

    def test_post_save_rollback_and_two_concurrent_requests(self):
        """Failure restores native item/species; competing successes consume exactly one held copy."""
        from django.db import connections
        from pokemon.services.evolution import EvolutionService

        self.prepare("Gligar", item="Razor Fang")
        self.travel("nightgrove")
        before, original = self.row(), OwnedPokemon.save

        def fail_after_write(mon, *args, **kwargs):
            value = original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and mon.species == "Gliscor":
                raise RuntimeError("context post-write fixture refusal")
            return value

        with patch.object(OwnedPokemon, "save", fail_after_write):
            self.evolve()
        self.assertEqual(self.row(), before)
        barrier = Barrier(2)

        def claim():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return EvolutionService(self.player).evolve(self.mon)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            result = list(workers.map(lambda _: claim(), range(2)))
        self.assertEqual(result.count("Gliscor"), 1)
        self.assertEqual((self.row()["species"], self.row()["held_item"]), ("Gliscor", ""))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.services.placement import PlacementService
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ContextualEvolutionCases))
        finally:
            if os.environ.get("PF2_CONTEXT_EVOLUTION_EVIDENCE"):
                Path(os.environ["PF2_CONTEXT_EVOLUTION_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
