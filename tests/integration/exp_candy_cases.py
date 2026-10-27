"""Paid EXP Candy, durable learning and actual choice commands in disposable SQL."""

import json
import os
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []
AMOUNTS = {
    "Exp. Candy XS": 100,
    "Exp. Candy S": 800,
    "Exp. Candy M": 3000,
    "Exp. Candy L": 10000,
    "Exp. Candy XL": 30000,
}


class ExpCandyCases(unittest.TestCase):
    """Use production purchases, field writes, queue records and +learn input."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply

    def setUp(self):
        """Create a real native learner with an ordinary gapped party and finite stock."""
        acquisition.AcquisitionCases.setUp(self)
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = create_owned_pokemon(
            "Bulbasaur",
            self.player.trainer,
            5,
            nature="Hardy",
            ability="Overgrow",
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Tackle", "Growl"],
        )
        PlacementService(self.player.storage).to_party(self.mon, slot=3)
        self.mons.append(self.mon)
        for player in self.players:
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.room.pk)
        self.room.db.store_buy_only = True
        self.room.db.store_inventory = {
            item: {"price": amount, "quantity": 2} for item, amount in AMOUNTS.items()
        }
        self.queue = ItemLearning(self.player)
        self.prepare()

    def state(self):
        """Read current SQL without trusting an old level, bag, moveset or prompt."""
        state = acquisition.AcquisitionCases.state(self)
        state["learner"] = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        state["knowledge"] = list(self.mon.learned_moves.order_by("pk").values("pk", "name"))
        state["stored"] = list(
            MovesetSlot.objects.filter(moveset__pokemon=self.mon)
            .order_by("moveset_id", "slot")
            .values()
        )
        state["boosts"] = list(
            MovePPBoost.objects.filter(pokemon=self.mon).order_by("move_id").values()
        )
        state["learning"] = self.queue.read()
        return state

    def prepare(self, level=5, *, total=None, hp=None):
        """Label legal level/EXP/stat and useful HP prerequisites separately."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            level=level,
            total_exp=level**3 if total is None else total,
            status="psn",
            friendship=203,
        )
        FieldMedicineUse._refresh(
            self.mon, OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        )
        maximum = get_max_hp(self.mon)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            current_hp=max(1, maximum - 7) if hp is None else hp
        )

    def buy(self, item):
        """Use actual +store/EvMenu, with no bag grant replacing acquisition."""
        before, quantity = self.state(), self.player.trainer.get_item_quantity(item)
        self.command("store")
        for text in ("1", item + " 1", "back", "q"):
            self.reply(text)
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), quantity + 1)
        self.assertEqual(after["wallet"], before["wallet"] - AMOUNTS[item])
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - 1)
        self.assertIn(item, self.command("inventory"))

    def use(self, item, target="3"):
        """Record actual field input and independent saved before/after state."""
        before, offset = self.state(), len(self.player.messages)
        self.command("use", item + "=" + target)
        after = self.state()
        EVIDENCE.append(
            {
                "case": self.id(),
                "command": "+use " + item + "=" + target,
                "before": before,
                "after": after,
                "messages": self.player.messages[offset:],
            }
        )
        return before, after

    def flow(self, item, mode="normal"):
        """Each size pays once for same/multi-level or final partial progression."""
        if mode == "same":
            self.prepare(90)
        elif mode == "cap":
            self.prepare(99, total=999999)
        elif mode == "fainted":
            self.prepare(hp=0)
        self.buy(item)
        before, after = self.use(item)
        old, new = before["learner"], after["learner"]
        gain = min(AMOUNTS[item], 1000000 - old["total_exp"])
        self.assertEqual(new["total_exp"], old["total_exp"] + gain, self.player.messages[-5:])
        self.assertEqual(new["level"], level_for_exp(new["total_exp"]))
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        FieldMedicineUse._refresh(self.mon, new)
        expected_hp = 0 if old["current_hp"] == 0 else get_max_hp(self.mon) - 7
        self.assertEqual(new["current_hp"], expected_hp)
        for key, value in old.items():
            if key not in {"level", "total_exp", "current_hp"}:
                self.assertEqual(new[key], value, key)
        self.assertEqual(before["pp"], after["pp"])
        self.assertEqual(before["stored"], after["stored"])
        self.assertEqual(before["boosts"], after["boosts"])
        self.assertEqual(before["wallet"], after["wallet"])
        self.assertEqual(before["stock"], after["stock"])

    def learned(self):
        """Earn several real native moves, then expose current explicit choices."""
        self.buy("Exp. Candy XL")
        self.use("Exp. Candy XL")
        entries = self.queue.read()["entries"]
        self.assertGreater(len(entries), 2)
        self.assertEqual([row["level"] for row in entries], sorted(row["level"] for row in entries))
        self.command("learn", "pending")
        entries = self.queue.read()["entries"]
        self.assertTrue(all(row["token"] for row in entries), self.player.messages[-3:])
        return entries

    def reconnect(self):
        """Open a new SQL connection and rebuild the ordinary captured transport."""
        from django.db import connection
        from pokemon.services.ownership import fresh_owned
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer

        character = self.player.character
        identity = character.pk
        character.attributes.reset_cache()
        ObjectDB.flush_cached_instance(character)
        OwnedPokemon.flush_cached_instance(self.mon)
        connection.close()
        character = ObjectDB.objects.get(pk=identity)
        self.player = acquisition.AcquisitionPlayer(
            character,
            Trainer.objects.get(user_id=identity),
            UserStorage.objects.get(user_id=identity),
        )
        self.player.pk, self.player.location = identity, self.room
        self.players[0] = self.player
        self.mon = fresh_owned(self.mon.pk)
        self.queue = ItemLearning(self.player)

    def race(self, *actions):
        """Start actual competing writers on distinct PostgreSQL connections."""
        from django.db import close_old_connections

        barrier = Barrier(len(actions))

        def run(action):
            """Keep every worker connection lifetime private to its writer."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_reconnect_resumes_knowledge_and_later_battle_evolution(self):
        """Paid level and selected moves persist into a later battle and separate evolution."""
        entries = self.learned()
        before = self.state()
        self.reconnect()
        self.assertEqual(self.state(), before)
        self.command("learn", "pending")
        entry = self.queue.read()["entries"][0]
        self.command("learn", "pending " + entry["token"] + "=3")
        self.reconnect()
        after = self.state()
        self.assertEqual(after["learner"], before["learner"])
        self.assertEqual(after["knowledge"], before["knowledge"])
        self.assertEqual(after["pp"][-1]["move__name"], entry["name"])
        expected = get_stats(self.mon)
        self.session = acquisition.BattleSession(self.player)
        foe = acquisition.create_battle_pokemon(
            "Magikarp", 100, is_wild=True, move_names=["Splash"]
        )
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (
            foe,
            "Fixture Magikarp",
            acquisition.BattleType.WILD,
            "EXP stats",
        )
        self.session.start()
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual({key: getattr(holder.base_stats, key) for key in expected}, expected)
        turn = self.session.battle.turn_count
        self.command("attack", "Tackle")
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        self.session.end()
        self.session = None
        self.command("evolve", str(self.mon.pk))
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(),
            "Ivysaur",
        )
        EVIDENCE.append(
            {
                "case": self.id(),
                "kind": "rebuilt-context-later-battle-evolution",
                "learned": entry["name"],
                "level": before["learner"]["level"],
                "battle_stats": expected,
                "evolved": "Ivysaur",
                "socket": False,
            }
        )

    def test_busy_menu_and_disconnected_transport_keep_pending_choices(self):
        """Learning never replaces an unrelated store menu or requires a live session."""
        self.buy("Exp. Candy XL")
        self.command("store")
        menu = self.player.ndb._evmenu
        self.use("Exp. Candy XL")
        self.assertIs(self.player.ndb._evmenu, menu)
        entries = self.queue.read()["entries"]
        self.assertGreater(len(entries), 2)
        self.assertTrue(all(row["token"] is None for row in entries))
        self.reply("q")
        self.reconnect()
        self.assertEqual(self.queue.read()["entries"], entries)
        self.command("learn", "pending")
        self.assertTrue(all(row["token"] for row in self.queue.read()["entries"]))

    def test_learning_partial_and_outer_rollback_are_quiet_and_retryable(self):
        """A chosen slot and its queue retirement commit together, after the outer scope."""
        from django.db import transaction

        token = self.learned()[0]["token"]
        before, offset = self.state(), len(self.player.messages)
        original = ItemLearning.write

        def fail(queue, state):
            """Fail only after the real selected-slot and queue SQL writes."""
            original(queue, state)
            raise RuntimeError("post-choice fixture")

        with patch.object(ItemLearning, "write", fail):
            with self.assertRaisesRegex(RuntimeError, "post-choice"):
                self.command("learn", "pending " + token + "=3")
        self.assertEqual(self.state(), before)
        with self.assertRaisesRegex(RuntimeError, "outer choice"):
            with transaction.atomic():
                self.command("learn", "pending " + token + "=3")
                self.assertFalse(
                    any("activated" in str(message) for message in self.player.messages[offset:])
                )
                raise RuntimeError("outer choice")
        self.assertEqual(self.state(), before)
        self.reconnect()
        self.command("learn", "pending " + token + "=3")
        self.assertEqual(len(self.state()["pp"]), 3)

    def test_competing_choice_replies_apply_at_most_one(self):
        """The character lock serializes two different slot replies to the same token."""
        token = self.learned()[0]["token"]
        before = self.state()
        self.race(
            lambda: self.command("learn", "pending " + token + "=3"),
            lambda: self.command("learn", "pending " + token + "=4"),
        )
        after = self.state()
        self.assertEqual(len(after["pp"]), 3)
        self.assertEqual(len(after["learning"]["entries"]), len(before["learning"]["entries"]) - 1)
        self.assertEqual(after["learner"], before["learner"])
        self.assertEqual(after["knowledge"], before["knowledge"])

    def test_post_debit_and_post_stat_failures_roll_back_each_size(self):
        """Keep inventory/EXP/HP/cache unchanged after each real partial write."""
        from pokemon.models.trainer import Trainer

        original_debit, original_save = Trainer.remove_item, OwnedPokemon.save

        def debit(trainer, *args):
            """Execute the real debit before reporting failure."""
            original_debit(trainer, *args)
            return False

        def save(pokemon, *args, **kwargs):
            """Execute the real progression/stat SQL before failing."""
            original_save(pokemon, *args, **kwargs)
            raise RuntimeError("post-stat fixture")

        for item in AMOUNTS:
            self.buy(item)
            before = self.state()
            with patch.object(Trainer, "remove_item", debit):
                self.use(item)
            self.assertEqual(self.state(), before)
            with patch.object(OwnedPokemon, "save", save):
                with self.assertRaisesRegex(RuntimeError, "post-stat"):
                    self.use(item)
            self.assertEqual(self.state(), before)

    def test_field_and_pending_guards_revalidate_current_fusion_and_battle(self):
        """Current SQL identity, battle locks, eggs, and stale owners cannot use a prompt."""
        self.buy("Exp. Candy XS")
        for updates in ({"is_egg": True}, {"trainer_id": self.players[1].trainer.pk}):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**updates)
            before, after = self.use("Exp. Candy XS")
            self.assertEqual(after, before)
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                is_egg=False, trainer_id=self.player.trainer.pk
            )
        for attribute in ("battle_lock", "battle_id", "pvp_locked"):
            self.player.character.attributes.add(attribute, "EXP fixture")
            before, after = self.use("Exp. Candy XS")
            self.assertEqual(after, before)
            self.player.character.attributes.remove(attribute)
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        before, after = self.use("Exp. Candy XS", "fusion")
        self.assertEqual(after, before)
        self.player.character.db.fusion_id = str(self.mon.pk)
        self.use("Exp. Candy XS", "fusion")
        self.assertEqual(self.player.trainer.get_item_quantity("Exp. Candy XS"), 0)
        PlacementService(self.player.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.player.character.db.fusion_id = None
        token = self.learned()[0]["token"]
        self.player.character.db.battle_lock = "EXP fixture"
        before = self.state()
        self.command("learn", "pending " + token + "=3")
        self.assertEqual(self.state(), before)
        self.player.character.db.battle_lock = None

    def test_malformed_pending_state_rejects_without_spending_or_discarding(self):
        """Never silently fix ambiguous saved paid-learning records."""
        self.buy("Exp. Candy XS")
        for malformed in ({"schema": True, "entries": []}, {"schema": 1, "entries": [{}]}):
            self.player.character.attributes.add(ItemLearning.attribute, malformed)
            before = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
            self.command("use", "Exp. Candy XS=3")
            self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values().get(), before)
            self.assertEqual(self.player.trainer.get_item_quantity("Exp. Candy XS"), 1)
        self.player.character.attributes.remove(ItemLearning.attribute)

    def test_stale_fusion_attribute_cache_cannot_spend_a_candy_or_activate(self):
        """Authoritative current-Fusion SQL overrides a previously read handler value."""
        from evennia.utils.dbserialize import to_pickle

        token = self.learned()[0]["token"]
        self.buy("Exp. Candy XS")
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.character.db.fusion_id = str(self.mon.pk)
        self.assertEqual(str(self.player.db.fusion_id), str(self.mon.pk))
        self.player.character.db_attributes.filter(db_key="fusion_id").update(
            db_value=to_pickle(None)
        )
        self.assertEqual(str(self.player.db.fusion_id), str(self.mon.pk))
        before, after = self.use("Exp. Candy XS", "fusion")
        self.assertEqual(after, before)
        self.command("learn", "pending " + token + "=3")
        self.assertEqual(self.state(), before)

    def test_gapped_active_slots_use_explicit_slot_and_preserve_boosted_pp(self):
        """Slot identity survives holes and an existing boosted move is never refilled."""
        token = self.learned()[0]["token"]
        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=2).update(slot=4, current_pp=1)
        MovesetSlot.objects.filter(moveset__pokemon=self.mon, slot=2).update(slot=4)
        first = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1)
        MovePPBoost.objects.create(pokemon=self.mon, move=first.move, bonus_pp=3)
        ActiveMoveslot.objects.filter(pk=first.pk).update(current_pp=2)
        self.command("learn", "pending")
        token = self.queue.read()["entries"][0]["token"]
        preserved = list(ActiveMoveslot.objects.filter(pokemon=self.mon).order_by("slot").values())
        boosts = self.state()["boosts"]
        self.command("learn", "pending " + token + "=2")
        self.assertEqual(
            list(
                ActiveMoveslot.objects.filter(pokemon=self.mon)
                .exclude(slot=2)
                .order_by("slot")
                .values()
            ),
            preserved,
        )
        self.assertEqual(self.state()["boosts"], boosts)
        self.assertEqual([row["slot"] for row in self.state()["pp"]], [1, 2, 4])

    def test_free_and_full_slot_choices_preserve_other_current_pp(self):
        """The current token selects a real slot without refilling other moves."""
        entries = self.learned()
        ActiveMoveslot.objects.filter(pokemon=self.mon).update(current_pp=1)
        self.command("learn", "pending")
        entries = self.queue.read()["entries"]
        before = self.state()
        self.command("learn", "pending " + entries[0]["token"] + "=3")
        after = self.state()
        self.assertEqual(len(after["pp"]), 3, self.player.messages[-4:])
        self.assertEqual([row["current_pp"] for row in after["pp"][:2]], [1, 1])
        self.command("learn", "pending")
        second = self.queue.read()["entries"][0]
        self.command("learn", "pending " + second["token"] + "=4")
        self.assertEqual(len(self.state()["pp"]), 4)
        self.command("learn", "pending")
        third = self.queue.read()["entries"][0]
        unchanged = list(
            ActiveMoveslot.objects.filter(pokemon=self.mon)
            .exclude(slot=2)
            .order_by("slot")
            .values()
        )
        self.command("learn", "pending " + third["token"] + "=2")
        self.assertEqual(
            list(
                ActiveMoveslot.objects.filter(pokemon=self.mon)
                .exclude(slot=2)
                .order_by("slot")
                .values()
            ),
            unchanged,
        )
        self.assertEqual(self.state()["learner"]["total_exp"], before["learner"]["total_exp"])

    def test_cancel_replay_and_stale_delivery_do_not_repeat_paid_exp(self):
        """Stored cancellation and re-listing retire old replies without resource changes."""
        entries = self.learned()
        token = entries[0]["token"]
        self.command("learn", "pending")
        before = self.state()
        self.command("learn", "pending " + token + "=1")
        self.assertEqual(self.state(), before)
        token = self.queue.read()["entries"][0]["token"]
        knowledge = self.state()["knowledge"]
        self.command("learn", "pending " + token + "=store")
        self.assertEqual(self.state()["knowledge"], knowledge)
        after = self.state()
        self.command("learn", "pending " + token + "=1")
        self.assertEqual(self.state(), after)
        self.assertEqual(after["learner"]["total_exp"], before["learner"]["total_exp"])

    def test_stale_pp_or_current_target_refuses_a_learning_write(self):
        """A changed active slot, box or owner cannot use an old displayed choice."""
        entries = self.learned()
        ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=1)
        before = self.state()
        self.command("learn", "pending " + entries[0]["token"] + "=1")
        self.assertEqual(self.state(), before)
        self.command("learn", "pending")
        token = self.queue.read()["entries"][0]["token"]
        PlacementService(self.player.storage).to_box(self.mon)
        before = self.state()
        self.command("learn", "pending " + token + "=1")
        self.assertEqual(self.state(), before)

    def test_post_knowledge_failure_and_outer_rollback_preserve_every_resource(self):
        """Real learned-move/queue writes remain inside the paid field transaction."""
        self.buy("Exp. Candy XL")
        before, offset = self.state(), len(self.player.messages)
        original = ItemLearning.add_locked

        def fail_after_queue(queue, *args):
            """Fail only after actual progression, knowledge and durable queue SQL."""
            original(queue, *args)
            raise RuntimeError("post-learning fixture")

        with patch.object(ItemLearning, "add_locked", fail_after_queue):
            with self.assertRaisesRegex(RuntimeError, "post-learning"):
                self.use("Exp. Candy XL")
        self.assertEqual(self.state(), before)
        self.assertFalse(any("gained" in str(message) for message in self.player.messages[offset:]))
        from django.db import transaction

        with self.assertRaisesRegex(RuntimeError, "outer EXP fixture"):
            with transaction.atomic():
                self.use("Exp. Candy XL")
                self.assertFalse(
                    any("gained" in str(message) for message in self.player.messages[offset:])
                )
                raise RuntimeError("outer EXP fixture")
        self.assertEqual(self.state(), before)

    def test_all_candies_reject_invalid_or_capped_targets_without_debit(self):
        """Level100, contradictions, foreign/gapped slots and move selectors are safe."""
        for item in AMOUNTS:
            self.buy(item)
            self.prepare(100)
            before, after = self.use(item)
            self.assertEqual(after, before)
            self.prepare(5, total=124)
            before, after = self.use(item)
            self.assertEqual(after, before)
            self.prepare()
            for target in ("1", "99", "party", "3/1"):
                before, after = self.use(item, target)
                self.assertEqual(after, before)


class ExpCandySourceCases(unittest.TestCase):
    """Opt-in recipe travel/purchase/effect without any public-stock claim."""

    state = ExpCandyCases.state
    native = ExpCandyCases.native
    command = ExpCandyCases.command
    reply = ExpCandyCases.reply
    use = ExpCandyCases.use
    flow = ExpCandyCases.flow
    prepare = ExpCandyCases.prepare

    def tearDown(self):
        """Remove only this test's tagged counter before the next installer case."""
        from pokemon.services.battle_rewards import BattleRewards

        ExpCandyCases.tearDown(self)
        marker = "counter_" + self.counter.recipe()["key"]
        receipt = BattleRewards.stored_attribute(self.hub, marker)
        if receipt:
            ObjectDB.objects.filter(
                pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
            ).delete()
            self.hub.attributes.remove(marker)

    def setUp(self):
        """Prove installer outer rollback/retry before creating this one private source."""
        from django.db import transaction
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter
        from pokemon.services.battle_rewards import BattleRewards

        ExpCandyCases.setUp(self)
        self.counter = ItemCounter("world/exp_candy_counter.json")
        self.hub = create_object(
            "typeclasses.rooms.FusionRoom", key="exp-candy-private-hub", nohome=True
        )
        before = ObjectDB.objects.count()
        with self.assertRaisesRegex(RuntimeError, "outer source"):
            with transaction.atomic():
                self.counter.install(self.hub)
                raise RuntimeError("outer source")
        marker = "counter_" + self.counter.recipe()["key"]
        self.assertEqual(ObjectDB.objects.count(), before)
        self.assertIsNone(BattleRewards.stored_attribute(self.hub, marker))
        self.assertIsNone(self.hub.attributes.get(marker))
        self.room = self.counter.install(self.hub)
        for player in self.players:
            player.location = self.hub
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.hub.pk)
            player.move_to = lambda destination, *args, _player=player, **kwargs: self.move(
                _player, destination
            )
        self.assertEqual(
            dict(self.room.db.store_inventory),
            {
                "Exp. Candy XS": {"price": 100, "quantity": 10},
                "Exp. Candy S": {"price": 800, "quantity": 10},
                "Exp. Candy M": {"price": 3000, "quantity": 5},
                "Exp. Candy L": {"price": 10000, "quantity": 2},
                "Exp. Candy XL": {"price": 30000, "quantity": 1},
            },
        )

    def move(self, player, destination):
        """Use the real character's movement with transport location adaptation."""
        moved = player.character.move_to(destination, quiet=True, move_hooks=False)
        if moved:
            player.location = destination
        return moved

    def travel(self, key):
        """Invoke the actual authored public Exit including its normal traverse lock."""
        exit_object = ObjectDB.objects.get(db_location_id=self.player.location.pk, db_key=key)
        command = exit_object.exit_command()
        command.caller, command.obj, command.args = self.player, exit_object, ""
        command.func()
        self.assertEqual(
            ObjectDB.objects.filter(pk=self.player.pk)
            .values_list("db_location_id", flat=True)
            .get(),
            exit_object.db_destination_id,
        )

    def buy(self, item):
        """Travel to finite authored offers before using the ordinary store menu."""
        if self.player.location.pk == self.hub.pk:
            self.travel("expcandy")
        ExpCandyCases.buy(self, item)

    def test_retry_does_not_refill_or_duplicate_sold_stock(self):
        """Reinstallation preserves exact remaining offers, object identities and back exit."""
        self.buy("Exp. Candy XL")
        before, count = self.state(), ObjectDB.objects.count()
        self.assertEqual(self.counter.install(self.hub).pk, self.room.pk)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.travel("back")
        self.assertEqual(self.player.location.pk, self.hub.pk)

    def test_no_funds_exhausted_stock_and_buy_only_source(self):
        """Invalid purchase/no funds/resale never changes wallet, bag or finite offers."""
        from menus import item_store

        self.buy("Exp. Candy XL")
        for text in ("Exp. Candy XL 1", "Exp. Candy XS 0", "Exp. Candy S -1"):
            before = self.state()
            self.command("store")
            self.reply("1")
            self.reply(text)
            self.reply("back")
            self.reply("q")
            self.assertEqual(self.state(), before)
        from pokemon.models.trainer import Trainer

        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=0)
        before = self.state()
        self.command("store")
        self.reply("1")
        self.reply("Exp. Candy XS 1")
        self.reply("back")
        self.reply("q")
        self.assertEqual(self.state(), before)
        item_store.node_sell(self.player, "Exp. Candy XL 1")
        self.assertEqual(self.state(), before)

    def test_source_drift_refuses_without_overwriting_or_restocking(self):
        """A changed price is an operator review, never implicit recipe reconciliation."""
        stock = dict(self.room.db.store_inventory)
        stock["Exp. Candy XS"]["price"] = 1
        self.room.db.store_inventory = stock
        before, count = self.state(), ObjectDB.objects.count()
        with self.assertRaises(ValueError):
            self.counter.install(self.hub)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)


def add_flow(item, mode):
    """Count every size and useful boundary independently."""

    def test(self):
        """Pay for this exact size/mode through actual player commands and SQL."""
        self.flow(item, mode)

    setattr(ExpCandyCases, "test_" + item.split()[-1] + "_" + mode, test)


def add_contention(item):
    """Qualify every final-copy amount on two distinct SQL writers."""

    def test(self):
        """One bag copy produces exactly one paid gain and duplicate-free knowledge."""
        self.buy(item)
        self.race(
            lambda: self.command("use", item + "=3"), lambda: self.command("use", item + "=3")
        )
        after = self.state()
        self.assertEqual(after["learner"]["total_exp"], 125 + AMOUNTS[item])
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        knowledge = after["knowledge"]
        self.assertEqual(len(knowledge), len({row["pk"] for row in knowledge}))

    setattr(ExpCandyCases, "test_final_copy_" + item.split()[-1], test)


for item in AMOUNTS:
    add_contention(item)
    for mode in ("normal", "same", "cap", "fainted"):
        add_flow(item, mode)

    def source_test(self, selected=item):
        """A real opt-in finite counter funds this exact candy's useful progression."""
        self.flow(selected)
        self.travel("back")

    setattr(ExpCandySourceCases, "test_authored_" + item.split()[-1], source_test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_or_create(app_label="objects", model="objectdb")
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot
        from pokemon.models.stats import level_for_exp
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.item_learning import ItemLearning
        from pokemon.services.placement import PlacementService

        module, _ = acquisition.COMMANDS["evolve"]
        acquisition.COMMANDS["learn"] = (module, module.CmdLearn)
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.TestSuite(
                    [
                        unittest.defaultTestLoader.loadTestsFromTestCase(ExpCandyCases),
                        unittest.defaultTestLoader.loadTestsFromTestCase(ExpCandySourceCases),
                    ]
                )
            )
        finally:
            if os.environ.get("PF2_EXP_CANDY_EVIDENCE"):
                Path(os.environ["PF2_EXP_CANDY_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
