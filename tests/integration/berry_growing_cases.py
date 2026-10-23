"""Durable Oran growing and independent Razz snacks through real commands/SQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
import json
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class BerryGrowingCases(unittest.TestCase):
    """Controlled server time and captured transport never replace crop/inventory writes."""

    native = acquisition.AcquisitionCases.native
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Separate authored source, wallet and native target setup from player actions."""
        acquisition.AcquisitionCases.setUp(self)
        self.installed_objects = []
        self.now = datetime(2026, 10, 22, 12, tzinfo=dt_timezone.utc)
        self.room.db.berry_nursery = True
        self.room.db.store_buy_only = True
        self.room.db.store_inventory = {
            "Oran Berry": {"price": 100, "quantity": 5},
            "Razz Berry": {"price": 100, "quantity": 5},
        }
        for player in self.players:
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.room.pk)
        self.clock_patch = patch("pokemon.services.berry_growing.timezone.now", lambda: self.now)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)

    def tearDown(self):
        """Close only menus belonging to these disposable identities."""
        acquisition.AcquisitionCases.tearDown(self)
        ObjectDB.objects.filter(pk__in=self.installed_objects).delete()

    def growing(self):
        """Use the same server service with an explicitly controlled test clock."""
        return BerryGrowing(self.player, clock=lambda: self.now)

    def state(self):
        """Read independent rows rather than shared crop/Pokemon instances."""
        result = acquisition.AcquisitionCases.state(self)
        result["bed"] = BerryBed.objects.filter(trainer=self.player.trainer).values().first()
        return result

    def record(self, args):
        """Retain normal input, fixture clock, messages and SQL before/after."""
        before, start = self.state(), len(self.player.messages)
        result = self.command("berry", args)
        EVIDENCE.append({"command": "+berry " + args, "controlled_server_utc": self.now.isoformat(),
                         "before": before, "after": self.state(),
                         "messages": list(map(str, self.player.messages[start:]))})
        return result

    def buy(self, item, amount=1):
        """Purchase existing finite source stock, never replace bag acquisition with grants."""
        before = self.state()
        self.command("store")
        for text in ("1", f"{item} {amount}", "back", "q"):
            self.reply(text)
        after = self.state()
        self.assertEqual(after["wallet"], before["wallet"] - 100 * amount)
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - amount)
        self.assertIn(item, self.command("inventory"))
        EVIDENCE.append({"command": f"+store -> Buy -> {item} {amount} -> +inventory",
                         "before": before, "after": after})

    def plant(self):
        """Start one ordinary cycle with one real purchased seed."""
        self.buy("Oran Berry")
        self.record("plant Oran Berry")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 0)
        return self.growing().cycle()

    def test_schema_file_matches_registered_model_without_running_migrations(self):
        """Read the complete migration graph's state; never apply any migration."""
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.state import ModelState

        state = MigrationLoader(None).project_state().models[("pokemon", "berrybed")]
        self.assertEqual(state, ModelState.from_model(BerryBed))

    def mask_flow(self, mask):
        """Every watering mask has its exact one-seed debit and 1-5 berry yield."""
        cycle = self.plant()
        planted = self.now
        for stage in range(4):
            self.now = planted + timedelta(hours=stage)
            if mask & (1 << stage):
                self.record("water")
                before = self.state()
                self.record("water")
                self.assertEqual(self.state(), before)
        self.now = planted + timedelta(seconds=14400)
        self.record("status")
        self.assertIn("ready to harvest", self.player.messages[-1])
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1 + mask.bit_count())
        bed = self.state()["bed"]
        self.assertIsNone(bed["cycle_id"])
        self.assertEqual((bed["last_harvest_cycle"], bed["last_harvest_yield"]), (cycle, 1 + mask.bit_count()))
        before = self.state()
        self.record("harvest")
        self.assertEqual(self.state(), before)

    def boundary(self, seconds, stage):
        """Persisted UTC determines the exact boundary, including after disconnecting SQL."""
        from django.db import connections

        cycle = self.plant()
        self.now += timedelta(seconds=seconds)
        connections.close_all()
        self.assertEqual((self.growing().status()["stage"], self.growing().cycle()), (stage, cycle))
        self.record("status")
        before = self.state()
        self.record("harvest")
        if stage < 4:
            self.assertEqual(self.state(), before)
        else:
            self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)

    def test_ready_crop_does_not_decay_or_accept_late_water(self):
        """Offline time can reach readiness but cannot add missed waterings."""
        self.plant()
        self.now += timedelta(days=30)
        before = self.state()
        self.record("water")
        self.assertEqual(self.state(), before)
        self.record("harvest")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)

    def test_wrong_room_stale_location_battle_and_other_owner_are_safe(self):
        """Current SQL access wins over an old transport/Attribute cache."""
        cycle = self.plant()
        other = ObjectDB.objects.create(db_key="unconfigured nursery control")
        before = self.state()
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=other.pk)
        self.record("water")
        self.assertEqual(self.state(), before)
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.room.pk)
        for lock_value in (True, 0, "stale-battle-id"):
            self.player.db.battle_lock = lock_value
            self.record("water")
            self.assertEqual(self.state(), before)
        self.player.db.battle_lock = False
        with self.assertRaises(BerryGrowingError):
            BerryGrowing(self.players[1], clock=lambda: self.now).operate("water", cycle=cycle)
        self.assertEqual(self.state(), before)

    def test_held_only_seed_and_invalid_plant_names_are_not_paid(self):
        """A held berry and catalog suffix cannot create a crop or free inventory."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Oran Berry")
        before = self.state()
        for text in ("plant Oran Berry", "plant Razz Berry", "plant Oran Berry 0", "water", "harvest"):
            self.record(text)
            self.assertEqual(self.state(), before)

    def test_corrupt_future_clock_or_saved_timestamp_rejected(self):
        """Clock/ready-time/mask corruption is never converted into an early harvest."""
        self.plant()
        original = self.now
        self.now -= timedelta(seconds=1)
        before = self.state()
        self.record("water")
        self.assertEqual(self.state(), before)
        self.now = original
        BerryBed.objects.filter(trainer=self.player.trainer).update(ready_at=original)
        before = self.state()
        self.record("harvest")
        self.assertEqual(self.state(), before)

    def test_stale_harvest_cannot_claim_or_reset_the_next_cycle(self):
        """Completed callbacks stay bound even after explicit replanting."""
        old = self.plant()
        self.now += timedelta(hours=4)
        self.record("harvest")
        self.record("plant Oran Berry")
        new = self.growing().cycle()
        self.assertNotEqual(new, old)
        self.now += timedelta(hours=4)
        before = self.state()
        with self.assertRaises(BerryGrowingError):
            self.growing().operate("harvest", cycle=old)
        with self.assertRaises(BerryGrowingError):
            self.growing().operate("water", cycle=old)
        self.assertEqual(self.state(), before)

    def test_partial_seed_debit_and_post_save_failures_roll_back(self):
        """Real writes before failure leave neither a phantom crop nor a lost seed."""
        self.buy("Oran Berry")
        before = self.state()
        original = Trainer.remove_item

        def partial(trainer, *args, **kwargs):
            original(trainer, *args, **kwargs)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.record("plant Oran Berry")
        self.assertEqual(self.state(), before)
        original_save = BerryBed.save

        def failed_save(bed, *args, **kwargs):
            original_save(bed, *args, **kwargs)
            raise RuntimeError("garden post-save fixture")

        with patch.object(BerryBed, "save", failed_save):
            self.record("plant Oran Berry")
        self.assertEqual(self.state(), before)

    def test_harvest_post_credit_failure_and_outer_rollback_are_atomic(self):
        """Inventory credit, receipt and crop reset share the containing transaction."""
        from django.db import transaction

        cycle = self.plant()
        self.now += timedelta(hours=4)
        before = self.state()
        original = BerryBed.save

        def fail(bed, *args, **kwargs):
            original(bed, *args, **kwargs)
            raise RuntimeError("garden post-credit fixture")

        with patch.object(BerryBed, "save", fail):
            self.record("harvest")
        self.assertEqual(self.state(), before)
        start = len(self.player.messages)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.growing().operate("harvest", cycle=cycle)
                self.assertFalse(any("Harvested" in str(m) for m in self.player.messages[start:]))
                raise RuntimeError("garden parent rollback")
        self.assertEqual(self.state(), before)

    def race(self, *actions):
        """Use independent SQL connections, synchronized before actual service locks."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def worker(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action()
                except ValueError as error:
                    return {"rejected": str(error), "changed": False}
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(worker, actions))

    def test_two_final_seed_plants_pay_once(self):
        """The final bag seed cannot pay for two simultaneous plant requests."""
        self.buy("Oran Berry")
        results = self.race(*(lambda: self.growing().operate("plant", cycle=None) for _ in range(2)))
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 0)
        self.assertEqual(BerryBed.objects.filter(trainer=self.player.trainer).count(), 1)

    def test_two_harvests_and_same_stage_water_are_exactly_once(self):
        """Competing requests share one watering bit and one durable credit."""
        cycle = self.plant()
        results = self.race(*(lambda: self.growing().operate("water", cycle=cycle) for _ in range(2)))
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.now += timedelta(hours=4)
        results = self.race(*(lambda: self.growing().operate("harvest", cycle=cycle) for _ in range(2)))
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 2)

    def test_ready_water_vs_harvest_does_not_add_a_missed_stage(self):
        """A boundary race cannot water a ready or already harvested crop."""
        cycle = self.plant()
        self.now += timedelta(hours=4)
        results = self.race(lambda: self.growing().operate("water", cycle=cycle),
                            lambda: self.growing().operate("harvest", cycle=cycle))
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)

    def test_harvest_water_and_replant_requests_cannot_cross_cycle_boundaries(self):
        """A three-way race finishes exactly the observed crop and never a new one."""
        cycle = self.plant()
        self.now += timedelta(hours=4)
        results = self.race(lambda: self.growing().operate("harvest", cycle=cycle),
                            lambda: self.growing().operate("water", cycle=cycle),
                            lambda: self.growing().operate("plant", cycle=cycle))
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)
        self.assertIsNone(self.growing().cycle())
        self.record("plant Oran Berry")
        self.assertNotEqual(self.growing().cycle(), cycle)

    def test_razz_purchase_snack_preserves_other_state_and_use_alias_is_excluded(self):
        """A purchased Razz has precisely the independent named snack effect."""
        self.buy("Razz Berry")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, status="brn", held_item="Razz Berry")
        before = self.state()
        self.command("use", "Razz Berry=3")
        self.assertEqual(self.state(), before)
        self.record("help")
        self.assertIn("PF2 equivalent", self.player.messages[-1])
        self.record("snack Razz Berry=3")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)
        self.assertEqual(self.player.trainer.get_item_quantity("Razz Berry"), 0)
        after = self.state()
        old = next(m for m in before["owned"] if m["pk"] == self.mon.pk)
        new = next(m for m in after["owned"] if m["pk"] == self.mon.pk)
        self.assertEqual({k:v for k,v in old.items() if k != "current_hp"},
                         {k:v for k,v in new.items() if k != "current_hp"})
        from django.db import connections
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(OwnedPokemon.objects.get(pk=self.mon.pk).current_hp, 11)

    def test_razz_no_effect_and_target_guards_preserve_stock(self):
        """No-effect, eggs and boxed targets cannot spend the snack."""
        self.buy("Razz Berry")
        maximum = get_max_hp(self.mon)
        for updates in ({"current_hp": maximum}, {"current_hp": 0}, {"current_hp": 1, "is_egg": True}):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
            before = self.state()
            self.record("snack Razz Berry=3")
            self.assertEqual(self.state(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, is_egg=False)
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.state()
        self.record("snack Razz Berry=" + str(self.mon.pk))
        self.assertEqual(self.state(), before)

    def test_razz_current_fusion_and_clamped_heal(self):
        """The actual current Fusion can receive a clamped shared medicine heal."""
        self.buy("Razz Berry")
        maximum = get_max_hp(self.mon)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=maximum - 3)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.db.fusion_id = str(self.mon.pk)
        self.record("snack Razz Berry=fusion")
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), maximum)
        self.assertEqual(self.player.trainer.get_item_quantity("Razz Berry"), 0)

    def test_razz_partial_debit_post_save_and_parent_rollback(self):
        """Every failure boundary keeps HP and bag stock together."""
        from django.db import transaction

        self.buy("Razz Berry")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        before = self.state()
        original = Trainer.remove_item

        def partial(trainer, *args, **kwargs):
            original(trainer, *args, **kwargs)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.record("snack Razz Berry=3")
        self.assertEqual(self.state(), before)
        original_save = OwnedPokemon.save

        def fail(mon, *args, **kwargs):
            original_save(mon, *args, **kwargs)
            raise RuntimeError("razz post-save fixture")

        with patch.object(OwnedPokemon, "save", fail):
            self.record("snack Razz Berry=3")
        self.assertEqual(self.state(), before)
        start = len(self.player.messages)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.record("snack Razz Berry=3")
                raise RuntimeError("razz parent rollback")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("Used Razz" in str(m) for m in self.player.messages[start:]))

    def test_nursery_install_traversal_purchase_harvest_feed_and_reinstall(self):
        """Use the real reviewed recipe, Exit commands and persisted movement."""
        from evennia.utils.create import create_object

        hub = create_object("typeclasses.rooms.FusionRoom", key="Disposable berry hub", nohome=True)
        nursery = BerryNursery.install(hub)
        self.installed_objects.extend([hub.pk, *self.source_ids(hub)])
        self.room = nursery
        self.player.location = hub
        self.player.character.location = hub

        def move(destination, **kwargs):
            moved = self.player.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = destination
            return moved

        self.player.move_to = move
        entrance = ObjectDB.objects.get(db_location=hub, db_key="nursery")
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.assertEqual(ObjectDB.objects.filter(pk=self.player.pk).values_list("db_location_id", flat=True).get(), nursery.pk)
        self.assertIn("four real hours", nursery.db.desc)
        self.buy("Oran Berry")
        before = self.state()
        self.assertEqual(BerryNursery.install(hub).pk, nursery.pk)
        self.assertEqual(self.state(), before)
        self.record("plant Oran Berry")
        self.record("water")
        self.now += timedelta(hours=4)
        self.record("harvest")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        self.command("use", "Oran Berry=3")
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 1)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)
        EVIDENCE.append({"event": "reviewed_nursery_exit_shop_growing_and_field_use",
                         "after": self.state(), "actual_socket": False, "move_hooks": False})

    @staticmethod
    def source_ids(hub):
        """Name only the exact objects recorded by this authorized fixture installer."""
        receipt = hub.attributes.get("counter_oran-razz-nursery-v1")
        return [receipt["room"], receipt["entrance"], receipt["return_exit"]]

    def test_snack_is_independent_of_nursery_and_held_stock(self):
        """No crop/room is required, and held-only Razz cannot fund a bag snack."""
        outside = ObjectDB.objects.create(db_key="outside nursery fixture")
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=outside.pk)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, held_item="Razz Berry")
        before = self.state()
        self.record("snack Razz Berry=3")
        self.assertEqual(self.state(), before)
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=self.room.pk)
        self.buy("Razz Berry")
        ObjectDB.objects.filter(pk=self.player.pk).update(db_location_id=outside.pk)
        self.record("snack Razz Berry=3")
        self.assertIsNone(self.state()["bed"])
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)

    def test_snack_ambiguity_foreign_owner_inactive_fusion_and_battle_guards(self):
        """Only a fresh, current eligible owned target can receive a snack."""
        self.buy("Razz Berry")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1, nickname="Snack Buddy")
        other = self.native("Pikachu", 4)
        OwnedPokemon.objects.filter(pk=other.pk).update(nickname="Snack Buddy")
        before = self.state()
        self.record("snack Razz Berry=Snack Buddy")
        self.assertEqual(self.state(), before)
        start = len(self.players[1].messages)
        self.command("berry", "snack Razz Berry=" + str(self.mon.pk), side=1)
        self.assertEqual(self.state(), before)
        self.assertTrue(self.players[1].messages[start:])
        self.player.db.battle_lock = True
        self.record("snack Razz Berry=3")
        self.assertEqual(self.state(), before)
        self.player.db.battle_lock = False
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        before = self.state()
        self.record("snack Razz Berry=fusion")
        self.assertEqual(self.state(), before)

    def test_snack_final_copy_and_overheal_contention(self):
        """Racing useful heals spend one final copy or one clamped copy exactly."""
        from pokemon.services.berry_snack import BerrySnack

        self.buy("Razz Berry")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        action = lambda: {"changed": bool(BerrySnack(self.player).use("Razz Berry", "3"))}
        results = self.race(action, action)
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Razz Berry"), 0)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 11)
        self.buy("Razz Berry", 2)
        maximum = get_max_hp(self.mon)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=maximum - 1)
        results = self.race(action, action)
        self.assertEqual(sum(r["changed"] for r in results), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Razz Berry"), 1)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), maximum)

    def test_parent_plant_and_water_rollbacks_leave_no_success(self):
        """Seed debit, crop creation and watering bit follow an outer transaction."""
        from django.db import transaction

        self.buy("Oran Berry")
        before, start = self.state(), len(self.player.messages)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.record("plant Oran Berry")
                raise RuntimeError("plant rollback fixture")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("Planted" in str(m) for m in self.player.messages[start:]))
        self.record("plant Oran Berry")
        before, start = self.state(), len(self.player.messages)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.record("water")
                raise RuntimeError("water rollback fixture")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("Watered" in str(m) for m in self.player.messages[start:]))

    def test_counter_disabled_funds_stock_conflicts_and_setup_failure(self):
        """Real shop and installer failures neither grant bags nor duplicate sources."""
        from evennia.utils.create import create_object

        before = self.state()
        self.room.db.is_item_shop = False
        self.command("store")
        self.assertEqual(self.state(), before)
        self.room.db.is_item_shop = True
        self.command("store")
        for text in ("1", "Oran Berry 6", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state(), before)
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=0)
        before = self.state()
        self.command("store")
        for text in ("1", "Oran Berry 1", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state(), before)
        hub = create_object("typeclasses.rooms.FusionRoom", key="failed nursery hub", nohome=True)
        self.installed_objects.append(hub.pk)
        original = create_object
        count = ObjectDB.objects.count()

        def fail_after_create(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("nursery setup fixture")

        with patch("evennia.utils.create.create_object", fail_after_create):
            with self.assertRaises(RuntimeError):
                BerryNursery.install(hub)
        self.assertEqual(ObjectDB.objects.count(), count)
        room = BerryNursery.install(hub)
        self.installed_objects.extend(self.source_ids(hub))
        other = create_object("typeclasses.rooms.FusionRoom", key="conflicting nursery hub", nohome=True)
        self.installed_objects.append(other.pk)
        count = ObjectDB.objects.count()
        with self.assertRaises(ValueError):
            BerryNursery.install(other)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.assertEqual(BerryNursery.install(hub).pk, room.pk)

    def test_concurrent_install_creates_one_source_without_restocking(self):
        """Two installers share the advisory lock and keep one durable receipt."""
        from evennia.utils.create import create_object

        hub = create_object("typeclasses.rooms.FusionRoom", key="racing nursery hub", nohome=True)
        self.installed_objects.append(hub.pk)
        results = self.race(*(lambda: {"room": BerryNursery.install(hub).pk} for _ in range(2)))
        self.assertEqual(results[0]["room"], results[1]["room"])
        self.installed_objects.extend(self.source_ids(hub))
        self.assertEqual(ObjectDB.objects.filter(db_location=hub, db_key="nursery").count(), 1)
        room = ObjectDB.objects.get(pk=results[0]["room"])
        self.assertEqual(room.db.store_inventory["Oran Berry"]["quantity"], 5)


def add_mask(mask):
    """Retain each distinct watering mask as a separately counted SQL case."""
    def test(self):
        self.mask_flow(mask)
    setattr(BerryGrowingCases, "test_watering_mask_" + str(mask), test)


def add_boundary(seconds, stage):
    """Retain exact UTC stage edges as separately counted SQL cases."""
    def test(self):
        self.boundary(seconds, stage)
    setattr(BerryGrowingCases, "test_clock_boundary_" + str(seconds), test)


for mask in range(16):
    add_mask(mask)
for seconds, stage in [(0, 0), (3599, 0), (3600, 1), (14399, 3), (14400, 4)]:
    add_boundary(seconds, stage)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        with patch.object(evennia, "Command", Command):
            from commands.player import cmd_berry
        acquisition.COMMANDS["berry"] = (cmd_berry, cmd_berry.CmdBerry)
        from evennia.objects.models import ObjectDB
        from django.contrib.contenttypes.models import ContentType
        ContentType.objects.get_for_model(ObjectDB)
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.berries import BerryBed
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer
        from pokemon.services.berry_growing import BerryGrowing, BerryGrowingError
        from pokemon.services.item_counter import BerryNursery
        from pokemon.services.placement import PlacementService
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BerryGrowingCases))
        finally:
            if os.environ.get("PF2_BERRY_GROWING_EVIDENCE"):
                Path(os.environ["PF2_BERRY_GROWING_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
