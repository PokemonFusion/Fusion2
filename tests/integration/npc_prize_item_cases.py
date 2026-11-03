"""Real NPC wins and once-only money receipts for physical Coin/Incense participation."""

from dataclasses import replace
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch
from uuid import uuid4

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE
from isolated_postgres import IsolatedPostgres


class NPCPrizeCases(BattlePlayerFixture):
    """Drive actual ordinary battle commands; never force a winner or a reward amount."""

    def setUp(self):
        """Prepare native owners and a deliberately weaker legal NPC opponent."""
        super().setUp()
        from pokemon.models.trainer import NPCTrainer, NPCPokemonTemplate

        self.mon = self.add(0, "Mew", ["Pound", "Trick", "Agility"], slot=3)
        self.bench = self.add(0, "Mew", ["Pound", "Trick"], slot=6)
        self.npc = NPCTrainer.objects.create(name="Prize acceptance " + uuid4().hex)
        NPCPokemonTemplate.objects.create(npc_trainer=self.npc, species="Magikarp", level=5,
            template_key="prize-peer", sort_order=1, ivs=[0] * 6, evs=[0] * 6,
            nature="Hardy", move_names=["Splash"])

    def snapshot(self):
        """Keep ended-session command evidence readable after ordinary cleanup clears its logic."""
        if getattr(self, "session", None) and self.session.data is None:
            self.session = None
        return super().snapshot()

    def money(self):
        """Read the current SQL wallet, not a reused character.trainer property instance."""
        from pokemon.models.trainer import Trainer

        return Trainer.objects.values_list("money", flat=True).get(pk=self.players[0].trainer.pk)

    def equip(self, item, slot=3, *, give=True):
        """A real bag copy is equipped through the shipped ordinary parser."""
        from commands.player.cmd_party import CmdSetHoldItem

        if item and give:
            self.players[0].trainer.add_item(item, 1)
        command = CmdSetHoldItem()
        command.caller, command.args = self.players[0], f"{slot}={item}"
        command.parse()
        command.func()

    def start(self, *, source="static", injured=False):
        """Use the production static encounter adapter with labelled disposable templates."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.trainer_encounters import generate_static_trainer_encounter

        for mon in (self.mon, self.bench):
            OwnedPokemon.flush_cached_instance(mon)
            OwnedPokemon.objects.get(pk=mon.pk).heal()
        if injured:
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=1)
        self.session = BattleSession(self.players[0], rng=random.Random(853))
        encounter = replace(generate_static_trainer_encounter(self.npc), source_type=source)
        self.session.start_trainer_encounter(encounter)
        self.reward_id = self.session.state.reward_id
        return self.session.battle

    def attack(self, move="Pound", *, target="B1"):
        """Run one normal selected move and retain authoritative reward and resource state."""
        from commands.player.cmd_battle_attack import CmdBattleAttack

        before, offset = self.snapshot(), len(self.players[0].messages)
        command = CmdBattleAttack()
        command.caller, command.args = self.players[0], "A1 " + move + " " + target
        command.parse()
        command.func()
        EVIDENCE.append({"label": "ordinary-npc-prize-battle", "command": "+attack " + command.args,
                         "before": before, "after": self.snapshot(), "wallet": self.money(),
                         "messages": self.players[0].messages[offset:]})

    def receipt(self):
        """Read the immutable reward payload independently of room snapshots or final gear."""
        from pokemon.services.battle_rewards import BattleRewards, CATEGORY

        return BattleRewards.stored_attribute(self.players[0].character,
            BattleRewards(self.reward_id).key("prize"), category=CATEGORY)

    def test_baseline_coin_incense_real_wins_and_exact_money(self):
        """Both names double the unchanged actual NPC formula, then duplicate receipt claims do nothing."""
        from pokemon.services.battle_rewards import BattleRewards

        base = None
        for item in ("", "Amulet Coin", "Luck Incense"):
            self.equip(item)
            before = self.money()
            self.start()
            self.attack()
            receipt = self.receipt()
            self.assertTrue(receipt["claimed"])
            actual = self.money() - before
            if base is None:
                base = actual
                self.assertGreater(base, 0)
            self.assertEqual(actual, base * (2 if item else 1))
            self.assertEqual(receipt["payload"]["npc_prize"]["base"], base)
            self.assertEqual(receipt["payload"]["npc_prize"]["multiplier"], 2 if item else 1)
            self.assertFalse(BattleRewards(self.reward_id).claim(self.players[0],
                BattleRewards(self.reward_id).key("prize")))
            self.assertEqual(self.money(), before + actual)

    def test_benched_only_holder_does_not_qualify(self):
        """Ownership alone never counts as entry or action participation."""
        self.equip("Amulet Coin", slot=6)
        self.start()
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 1)

    def test_initial_qualification_survives_rebuild_and_does_not_stack(self):
        """The saved entry evidence survives a checkpoint; a second equipped holder adds no multiplier."""
        self.equip("Amulet Coin")
        self.equip("Luck Incense", slot=6)
        battle = self.start()
        self.assertEqual(len(battle.npc_prize_qualifications), 1)
        self.rebuild()
        self.assertEqual(len(self.session.battle.npc_prize_qualifications), 1)
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)

    def test_trick_acquisition_needs_a_later_action_and_restore_grants_nothing(self):
        """Receiving the item during one's own Trick does not count as prior participation."""
        self.npc.pokemon_templates.update(held_item="Amulet Coin")
        battle = self.start()
        self.assertEqual(battle.npc_prize_qualifications, {})
        self.attack("Trick")
        self.assertEqual(battle.npc_prize_qualifications, {})
        self.rebuild()
        self.assertEqual(self.session.battle.npc_prize_qualifications, {})
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["qualification"]["phase"], "action")

    def test_late_transfer_without_a_later_action_keeps_base_prize(self):
        """A genuine NPC self-KO after Trick proves final held equipment is insufficient."""
        self.npc.pokemon_templates.update(species="Drifblim", level=50,
                                         move_names=["Explosion"], held_item="Amulet Coin")
        battle = self.start()
        self.attack("Trick")
        receipt = self.receipt()
        self.assertTrue(receipt["claimed"])
        self.assertEqual(receipt["payload"]["npc_prize"]["multiplier"], 1)
        self.assertEqual(battle.npc_prize_qualifications, {})
        from pokemon.models.core import OwnedPokemon
        from pokemon.names import normalize_name

        held = OwnedPokemon.objects.values_list("held_item", flat=True).get(pk=self.mon.pk)
        self.assertEqual(normalize_name(held), "amuletcoin")

    def test_giving_away_an_earned_item_keeps_prior_qualification(self):
        """A later transfer away cannot erase an already earned, persisted entry condition."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.names import normalize_name

        self.equip("Amulet Coin")
        self.start()
        self.attack("Trick")
        held = OwnedPokemon.objects.values_list("held_item", flat=True).get(pk=self.mon.pk)
        self.assertEqual(normalize_name(held), "")
        self.rebuild()
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)

    def test_nonstandard_encounter_sources_do_not_change_money(self):
        """Scripted, gym and Adventure sources keep the original unmultiplied formula."""
        self.equip("Amulet Coin")
        for source in ("scripted", "gym_leader", "adventure"):
            self.start(source=source)
            self.attack()
            receipt = self.receipt()
            self.assertNotIn("npc_prize", receipt["payload"])
            self.assertGreater(receipt["payload"]["money"], 0)

    def test_fainted_qualifier_retains_bonus_when_ordinary_bench_wins(self):
        """A legal attack faints the injured entry holder; the replacement earns its own real win."""
        from pokemon.models.core import OwnedPokemon

        self.equip("Amulet Coin")
        self.npc.pokemon_templates.update(species="Caterpie", move_names=["Tackle"])
        self.start(injured=True)
        self.attack("Agility", target="A1")
        self.assertEqual(OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=self.mon.pk), 0)
        self.command("switch", "6")
        self.attack()
        proof = self.receipt()["payload"]["npc_prize"]
        self.assertEqual(proof["multiplier"], 2)
        self.assertEqual(proof["qualification"]["pokemon"], "owned:" + str(self.mon.pk))

    def test_wallet_post_write_fault_retains_sealed_bonus_for_normal_retry(self):
        """SQL rollback preserves the exact pending prize; reconnect/retry cannot pay twice."""
        from django.db import connection
        from commands.player.cmd_battle_retry import CmdBattleRetry
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import Trainer

        self.equip("Luck Incense")
        self.start()
        before, original = self.money(), Trainer.add_money

        def fail_after_money(trainer, amount):
            original(trainer, amount)
            raise RuntimeError("prize wallet post-write fixture refusal")

        with patch.object(Trainer, "add_money", fail_after_money):
            self.attack()
        pending = self.receipt()
        self.assertFalse(pending["claimed"])
        self.assertEqual(self.money(), before)
        self.assertEqual(pending["payload"]["npc_prize"]["multiplier"], 2)
        # An after-outcome gear edit cannot create or erase the sealed earned payload.
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="")
        connection.close()
        for _ in range(2):
            command = CmdBattleRetry()
            command.caller, command.args = self.players[0], ""
            command.parse()
            command.func()
        self.assertTrue(self.receipt()["claimed"])
        self.assertEqual(self.receipt()["payload"], pending["payload"])
        self.assertEqual(self.money(), before + pending["payload"]["money"])

    def test_foreign_owner_or_boxed_qualifier_refuses_current_outcome_plan(self):
        """Uncommitted stale custody cannot turn a former holder into a valid prize owner."""
        from pokemon.battle.npc_prize_items import NPCPrizeItems
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.placement import PlacementService

        self.equip("Amulet Coin")
        battle = self.start()
        winner, before = battle.participants[0], self.money()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(trainer_id=self.players[1].trainer.pk)
        with self.assertRaises(ValueError):
            NPCPrizeItems.payload(battle, winner, 40)
        self.assertEqual(self.money(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(trainer_id=self.players[0].trainer.pk)
        PlacementService(self.players[0].storage).to_box(self.mon)
        with self.assertRaises(ValueError):
            NPCPrizeItems.payload(battle, winner, 40)
        self.assertEqual(self.money(), before)
        PlacementService(self.players[0].storage).to_party(self.mon, slot=3)

    def test_loss_wild_and_pvp_award_no_bonus_money(self):
        """Actual concession, wild knockout and disposable PvP knockout retain their existing policies."""
        from pokemon.battle.battleinstance import BattleSession

        self.equip("Amulet Coin")
        before = self.money()
        self.start()
        self.command("concede", "yes")
        self.assertEqual(self.money(), before)
        self.assertIsNone(self.receipt())
        self.session = BattleSession(self.players[0], rng=random.Random(853))
        self.session.start_test_battle(species="Magikarp", level=5, opponent_kind="wild")
        self.reward_id = self.session.state.reward_id
        self.attack()
        self.assertEqual(self.money(), before)
        self.assertIsNone(self.receipt())
        self.add(1, "Magikarp", ["Splash"], slot=3, level=5)
        self.launch()
        self.reward_id = self.session.state.reward_id
        self.attack()
        self.command("attack", "B1 Splash B1", 1)
        self.assertEqual(self.money(), before)
        self.assertIsNone(self.receipt())

    def test_competing_claims_on_pending_bonus_credit_wallet_once(self):
        """Independent SQL connections serialize the same sealed outcome after a real failed credit."""
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from threading import Barrier
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards

        self.equip("Amulet Coin")
        self.start()
        before, original = self.money(), Trainer.add_money

        def fail_after_credit(trainer, amount):
            original(trainer, amount)
            raise RuntimeError("concurrent prize post-credit fixture refusal")

        with patch.object(Trainer, "add_money", fail_after_credit):
            self.attack()
        pending = self.receipt()
        self.assertFalse(pending["claimed"])
        self.assertEqual(self.money(), before)
        delivery, barrier = BattleRewards(self.reward_id), Barrier(2)

        def claim():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return delivery.claim(self.players[0], delivery.key("prize"))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(lambda _: claim(), range(2)))
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(self.money(), before + pending["payload"]["money"])
        self.assertTrue(self.receipt()["claimed"])

    def test_finite_source_purchase_equipment_and_useful_prize(self):
        """Buy each one-copy offer, retain paid stock on authoring retry, then win with a purchased holder."""
        from django.contrib.contenttypes.models import ContentType
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from evennia.utils.evmenu import CmdEvMenuNode
        from commands.player.cmd_store import CmdStore
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_rewards import BattleRewards
        from pokemon.services.item_counter import ItemCounter

        ContentType.objects.get_for_model(ObjectDB)
        hub = create_object("typeclasses.rooms.FusionRoom", key="Prize source fixture", nohome=True)
        counter = ItemCounter("world/npc_prize_item_counter.json")
        room = counter.install(hub)
        owner = self.players[0].character
        owner.move_to(hub, quiet=True)
        entrance = ObjectDB.objects.get(db_location=hub, db_destination=room)
        entrance.at_traverse(owner, room)
        self.players[0].location = room
        self.players[0].check_permstring = owner.check_permstring
        Trainer.objects.filter(pk=self.players[0].trainer.pk).update(money=20000)
        command = CmdStore()
        command.caller, command.args = self.players[0], ""
        command.parse()
        command.func()
        for text in ("1", "Amulet Coin 1", "Luck Incense 1", "q"):
            reply = CmdEvMenuNode()
            reply.caller, reply.raw_string, reply.session = self.players[0], text, None
            reply.func()
        self.assertEqual(self.money(), 0)
        self.assertEqual(counter.install(hub).pk, room.pk)
        stock = BattleRewards.stored_attribute(room, "store_inventory")
        self.assertEqual([stock[item]["quantity"] for item in ("Amulet Coin", "Luck Incense")], [0, 0])
        self.equip("Amulet Coin", give=False)
        owner.move_to(ObjectDB.objects.get(pk=self.room.pk), quiet=True)
        self.players[0].location = self.room
        self.start()
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)
        self.assertEqual(self.money(), self.receipt()["payload"]["money"])
        self.assertEqual(self.players[0].trainer.get_item_quantity("Luck Incense"), 1)

    def test_zero_base_and_native_klutz_field_condition(self):
        """An inert held field condition remains reusable under Klutz and multiplies zero to zero."""
        from pokemon.battle.npc_prize_items import NPCPrizeItems
        from pokemon.models.core import OwnedPokemon
        from pokemon.names import normalize_name
        from pokemon.services.placement import PlacementService

        PlacementService(self.players[0].storage).to_box(self.mon)
        self.mon = self.add(0, "Buneary", ["Pound"], ability="Klutz", slot=3)
        self.equip("Luck Incense")
        battle = self.start()
        self.assertEqual(NPCPrizeItems.payload(battle, battle.participants[0], 0)["money"], 0)
        self.attack()
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)
        held = OwnedPokemon.objects.values_list("held_item", flat=True).get(pk=self.mon.pk)
        self.assertEqual(normalize_name(held), "luckincense")

    def test_post_qualification_turn_fault_rewinds_ledger_money_and_pp_before_retry(self):
        """A real failed final sync removes tentative participation and payout with the whole turn."""
        from commands.player.cmd_battle_retry import CmdBattleRetry
        from pokemon.models.core import OwnedPokemon

        self.npc.pokemon_templates.update(held_item="Amulet Coin")
        self.start()
        self.attack("Trick")
        self.assertEqual(self.session.battle.npc_prize_qualifications, {})
        before, wallet, original = self.snapshot(), self.money(), OwnedPokemon.save

        def fail_after_sync(mon, *args, **kwargs):
            value = original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and "current_hp" in kwargs.get("update_fields", []):
                raise RuntimeError("NPC prize post-sync fixture refusal")
            return value

        with patch.object(OwnedPokemon, "save", fail_after_sync):
            self.attack()
        self.assertEqual(self.money(), wallet)
        self.assertIsNone(self.receipt())
        self.assertEqual(self.snapshot()["owned"], before["owned"])
        self.assertEqual(self.snapshot()["moves"], before["moves"])
        self.assertEqual(self.session.battle.npc_prize_qualifications, {})
        self.assertTrue(self.session.turn_state.get("error"))
        command = CmdBattleRetry()
        command.caller, command.args = self.players[0], ""
        command.parse()
        command.func()
        self.assertTrue(self.receipt()["claimed"])
        self.assertEqual(self.receipt()["payload"]["npc_prize"]["multiplier"], 2)
        self.assertEqual(self.money(), wallet + self.receipt()["payload"]["money"])


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs
    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("npc-prize-items"), IsolatedBattleLogs():
                result = unittest.TextTestRunner(verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(NPCPrizeCases))
    finally:
        if os.environ.get("PF2_NPC_PRIZE_EVIDENCE"):
            Path(os.environ["PF2_NPC_PRIZE_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
