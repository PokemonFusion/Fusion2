"""Real Bell equip, bounded field friendship, native evolution and SQL conservation."""

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


class SootheBellCases(unittest.TestCase):
    """Use production parsers, owners, actual held copies and fresh database reads."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    state = acquisition.AcquisitionCases.state
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Label ordinary native/wallet/berry prerequisites independently of source proof."""
        acquisition.AcquisitionCases.setUp(self)
        self.player.trainer.add_item("Soothe Bell", 1)
        self.command("hold", "3=Soothe Bell")
        self.assertEqual(self.row()["held_item"], "Soothe Bell")
        self.assertEqual(self.player.trainer.get_item_quantity("Soothe Bell"), 0)

    def row(self):
        """Bypass the Evennia identity cache for exact current effects."""
        return OwnedPokemon.objects.values().get(pk=self.mon.pk)

    def prepare(self, **updates):
        """Set only private preconditions, deliberately retaining stale instances."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)

    def feed(self, item="Pomeg Berry", target="3"):
        """A labelled real bag berry is spent only by the production +use command."""
        self.player.trainer.add_item(item, 1)
        before = self.state()
        output = self.command("use", item + "=" + target)
        EVIDENCE.append({"label": "ordinary-bell-field-use", "command": "+use " + item + "=" + target,
                         "before": before, "after": self.state(), "output": output})
        return output

    def test_six_berries_exact_tiers_cap_and_no_effect(self):
        """All six useful positive events floor before the cap without consuming the Bell."""
        from pokemon.services.field_berries import FieldBerryUse

        for item, index in FieldBerryUse.ev_stats.items():
            for friendship, expected in ((0, 15), (99, 114), (100, 107), (199, 206),
                                         (200, 203), (253, 255), (254, 255), (255, 255)):
                with self.subTest(item=item, friendship=friendship):
                    evs = [0] * 6
                    evs[index] = 10
                    self.prepare(evs=evs, friendship=friendship, current_hp=1)
                    before = self.row()
                    self.feed(item)
                    after = self.row()
                    self.assertEqual(after["friendship"], expected)
                    self.assertEqual(after["evs"], [0] * 6)
                    self.assertEqual(after["held_item"], "Soothe Bell")
                    self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
                    for key in before:
                        if key not in {"friendship", "evs", "current_hp"}:
                            self.assertEqual(after[key], before[key], key)
            self.prepare(evs=[0] * 6, friendship=255)
            before = self.row()
            self.feed(item)
            self.assertEqual(self.row(), before)
            self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
            self.player.trainer.remove_item(item)

    def test_stale_held_bag_only_and_foreign_owner(self):
        """A bag Bell or stale remembered held field never substitutes for current physical ownership."""
        self.prepare(friendship=100, evs=[10, 0, 0, 0, 0, 0], held_item="")
        self.player.trainer.add_item("Soothe Bell", 1)
        self.feed()
        self.assertEqual(self.row()["friendship"], 105)
        self.prepare(friendship=100, evs=[10, 0, 0, 0, 0, 0], held_item="Soothe Bell")
        self.feed()
        self.assertEqual(self.row()["friendship"], 107)
        self.prepare(trainer_id=self.players[1].trainer.pk, friendship=100)
        before = self.row()
        self.feed()
        self.assertEqual(self.row(), before)
        self.assertEqual(self.player.trainer.get_item_quantity("Pomeg Berry"), 1)

    def test_current_fusion_battle_egg_box_and_reservation_guards(self):
        """The Bell reuses every authoritative field target guard, including current Fusion."""
        from pokemon.services.ownership import PokemonReservations

        self.prepare(friendship=100, evs=[20, 0, 0, 0, 0, 0])
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        before = self.row()
        self.feed(target="fusion")
        self.assertEqual(self.row(), before)
        self.player.trainer.remove_item("Pomeg Berry")
        self.player.character.db.fusion_id = str(self.mon.pk)
        self.feed(target="fusion")
        self.assertEqual(self.row()["friendship"], 107)
        PlacementService(self.player.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.player.character.db.fusion_id = None
        for key, value in (("is_egg", True), ("trainer_id", self.players[1].trainer.pk)):
            previous = self.row()[key]
            self.prepare(**{key: value})
            before = self.row()
            self.feed()
            self.assertEqual(self.row(), before)
            self.player.trainer.remove_item("Pomeg Berry")
            self.prepare(**{key: previous})
        self.player.character.db.battle_lock = "private-bell-battle"
        before = self.row()
        self.feed()
        self.assertEqual(self.row(), before)
        self.player.character.db.battle_lock = None
        self.player.trainer.remove_item("Pomeg Berry")
        token = uuid4()
        reservations = PokemonReservations(self.player)
        reservations.claim("market", [self.mon.pk], token)
        before = self.row()
        self.feed()
        self.assertEqual(self.row(), before)
        reservations.release("market", token)
        self.player.trainer.remove_item("Pomeg Berry")
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.row()
        self.feed(target=str(self.mon.pk))
        self.assertEqual(self.row(), before)

    def test_post_write_fault_and_competing_last_berry(self):
        """A real SQL write aborts atomically, then two fresh connections can spend once."""
        from django.db import connections

        self.prepare(friendship=100, evs=[20, 0, 0, 0, 0, 0])
        self.player.trainer.add_item("Pomeg Berry", 1)
        before, original = self.state(), OwnedPokemon.save

        def fail_after_write(mon, *args, **kwargs):
            value = original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and "friendship" in kwargs.get("update_fields", []):
                raise RuntimeError("Bell post-write fixture refusal")
            return value

        with patch.object(OwnedPokemon, "save", fail_after_write), self.assertRaises(RuntimeError):
            self.command("use", "Pomeg Berry=3")
        self.assertEqual(self.state(), before)
        barrier = Barrier(2)

        def claim():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return self.command("use", "Pomeg Berry=3")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(self.row()["friendship"], 107)
        self.assertEqual(self.row()["evs"][0], 10)
        self.assertEqual(self.row()["held_item"], "Soothe Bell")
        self.assertEqual(self.player.trainer.get_item_quantity("Pomeg Berry"), 0)

    def test_counter_purchase_equip_inspect_native_crobat_and_reconnect(self):
        """Pay for the explicit finite source, then use a genuine Bell to reach native evolution."""
        from django.contrib.contenttypes.models import ContentType
        from django.db import connection
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter

        self.command("hold", "3=")
        self.player.trainer.remove_item("Soothe Bell")
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Golbat", 3)
        self.prepare(friendship=153)
        ContentType.objects.get_for_model(ObjectDB)
        hub = create_object("typeclasses.rooms.FusionRoom", key="Bell source fixture", nohome=True)
        counter = ItemCounter("world/soothe_bell_counter.json")
        room = counter.install(hub)
        self.player.character.move_to(hub, quiet=True)
        entrance = ObjectDB.objects.get(db_location=hub, db_destination=room)
        entrance.at_traverse(self.player.character, room)
        self.player.location = room
        self.room = room
        before = self.state()
        self.command("store")
        self.reply("1")
        self.reply("Soothe Bell 1")
        self.reply("q")
        self.assertEqual(self.state()["wallet"], before["wallet"] - 4000)
        self.assertEqual(counter.install(hub).pk, room.pk)
        self.assertEqual(self.state()["stock"]["Soothe Bell"]["quantity"], 1)
        self.command("hold", "3=Soothe Bell")
        self.feed()
        self.assertEqual(self.row()["friendship"], 160)
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row()["species"], "Crobat")
        self.assertEqual(self.row()["held_item"], "Soothe Bell")
        connection.close()
        self.assertEqual(self.row()["friendship"], 160)
        self.assertEqual(self.row()["species"], "Crobat")
        EVIDENCE.append({"label": "finite-bell-to-native-crobat", "after": self.state(),
                         "messages": list(map(str, self.player.messages)), "captured_transport": True})

    def test_herbal_losses_and_native_klutz_field_context(self):
        """This field bonus does not alter negative herbal events or borrow battle suppression."""
        self.prepare(friendship=150, current_hp=1)
        self.feed("Energy Root")
        self.assertEqual(self.row()["friendship"], 140)
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Buneary", 3)
        self.player.trainer.add_item("Soothe Bell")
        self.command("hold", "3=Soothe Bell")
        self.prepare(friendship=100, ability="Klutz")
        self.feed()
        self.assertEqual(self.row()["friendship"], 107)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.placement import PlacementService
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(SootheBellCases))
        finally:
            if os.environ.get("PF2_SOOTHE_BELL_EVIDENCE"):
                Path(os.environ["PF2_SOOTHE_BELL_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
