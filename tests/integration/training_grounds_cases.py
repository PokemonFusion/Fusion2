"""Useful training/retraining commands, real owned SQL and session concurrency."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import random
import time
from threading import Barrier
import unittest
from unittest.mock import patch

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE
from isolated_postgres import IsolatedPostgres


class TrainingCases(BattlePlayerFixture):
    """Label clock/owner prerequisites without replacing progression or item writes."""

    def setUp(self):
        """Prepare ordinary native owners and one authorized training location."""
        super().setUp()
        from django.utils import timezone
        from evennia.objects.models import ObjectDB

        self.now = timezone.now()
        self.room.db.training_ground = True
        for player in self.players:
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.room.pk)
        self.mon = self.add(0, "Mew", ["Pound", "Rain Dance"], slot=3, level=50)
        self.foe = self.add(1, "Mew", ["Pound", "Rain Dance"], slot=3, level=55)
        if "real_elapsed" not in self._testMethodName:
            clock = patch("pokemon.services.training_grounds.timezone.now", lambda: self.now)
            clock.start()
            self.addCleanup(clock.stop)

    def cmd(self, args):
        """Use the actual +train parser with captured transport and SQL evidence."""
        from commands.player.cmd_train import CmdTrain

        before, offset = self.snapshot(), len(self.players[0].messages)
        command = CmdTrain()
        command.caller, command.args, command.cmdstring = self.players[0], args, "+train"
        command.parse()
        command.func()
        messages = self.players[0].messages[offset:]
        EVIDENCE.append({"case": self.id(), "label": "ordinary-training-command",
                         "command": "+train " + args, "controlled_server_utc": self.now.isoformat(),
                         "before": before, "after": self.snapshot(), "messages": messages})
        return "\n".join(map(str, messages))

    def service(self):
        """Use the unmodified service, with only the labelled server clock controlled."""
        from pokemon.services.training_grounds import TrainingGrounds

        return TrainingGrounds(self.players[0])

    def row(self):
        """Read owned fields independently of cached trainer/Pokemon instances."""
        from pokemon.models.core import OwnedPokemon

        return OwnedPokemon.objects.values().get(pk=self.mon.pk)

    def profile(self):
        """Read the durable receipt instead of a reused caller Attribute cache."""
        from evennia.objects.models import ObjectDB
        from pokemon.services.training_grounds import TrainingGrounds

        return TrainingGrounds._profile(ObjectDB.objects.get(pk=self.players[0].pk))

    def finish(self, stat="Attack"):
        """Spend all ordinary inputs; a completed step alone never invents elapsed time."""
        self.cmd("3=" + stat)
        self.assertEqual(self.profile()["pending"]["kind"], "session_review")
        self.cmd("confirm")
        for approach in ("technique", "pace", "recovery"):
            self.now += timedelta(seconds=30)
            self.cmd("continue " + approach)
        self.assertIsNone(self.profile()["pending"])

    def test_six_stats_useful_caps_and_unchanged_resources(self):
        """Each canonical stat changes real calculated stats without EXP/PP/genetic grants."""
        from pokemon.helpers.pokemon_helpers import get_stats
        from pokemon.models.core import OwnedPokemon

        before = self.row()
        for index, stat in enumerate(self.service().stats):
            with self.subTest(stat=stat):
                self.finish(stat)
                self.assertEqual(self.row()["evs"][index], 64)
        for key in ("ivs", "nature", "trained_stat_nature", "level", "total_exp", "held_item", "status"):
            self.assertEqual(self.row()[key], before[key])
        stats = get_stats(OwnedPokemon.objects.get(pk=self.mon.pk))
        self.assertEqual(stats["attack"], 113)
        self.assertEqual(self.row()["current_hp"], stats["hp"])
        self.assertEqual(self.profile()["completed"], 6)
        self.assertEqual(self.players[0].trainer.get_item_quantity("Rare Candy"), 1)

    def test_partial_stat_and_total_caps_no_effect_preserves_state(self):
        """Useful clipped EVs count; stat/total exhaustion never starts another session."""
        from pokemon.models.core import OwnedPokemon

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[0, 250, 0, 0, 0, 0])
        self.finish("Attack")
        self.assertEqual(self.row()["evs"][1], 252)
        before = self.snapshot()
        self.assertIn("no useful", self.cmd("3=Attack"))
        self.assertEqual(self.snapshot(), before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[252, 252, 5, 0, 0, 0])
        self.finish("SpA")
        self.assertEqual(self.row()["evs"], [252, 252, 5, 1, 0, 0])
        before = self.snapshot()
        self.cmd("3=Speed")
        self.assertEqual(self.snapshot(), before)

    def test_clock_steps_reconnect_duplicate_confirm_and_cancel(self):
        """Offline time opens one step, not all steps; confirmation cannot restart time."""
        from django.db import connection

        self.cmd("3=Attack")
        self.cmd("confirm")
        pending = dict(self.profile()["pending"])
        self.cmd("confirm")
        self.assertEqual(self.profile()["pending"], pending)
        self.assertIn("opens in", self.cmd("continue technique"))
        self.assertEqual(self.profile()["pending"], pending)
        self.now += timedelta(hours=2)
        connection.close()
        self.players[0].attributes.reset_cache()
        self.cmd("status")
        self.cmd("continue pace")
        self.assertEqual(self.profile()["pending"]["step"], 1)
        self.assertEqual(self.row()["evs"], [0] * 6)
        self.cmd("continue recovery")
        self.assertEqual(self.profile()["pending"]["step"], 1)
        self.cmd("cancel")
        self.assertIsNone(self.profile()["pending"])
        self.assertEqual(self.profile()["completed"], 0)

    def test_free_partial_full_reset_preview_hp_and_replay(self):
        """Confirmed EV removal preserves HP deficit, all other resources and reward count."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.services.field_items import FieldMedicineUse

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[128, 128, 0, 0, 0, 0])
        mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        FieldMedicineUse._refresh(mon, self.row())
        old_max = get_max_hp(mon)
        OwnedPokemon.objects.filter(pk=mon.pk).update(current_hp=old_max - 10)
        before = self.row()
        self.assertIn("HP ", self.cmd("reset 3=HP/64"))
        self.assertEqual(self.row(), before)
        self.cmd("confirm")
        self.assertEqual(self.row()["evs"], [64, 128, 0, 0, 0, 0])
        FieldMedicineUse._refresh(mon, self.row())
        self.assertEqual(mon.current_hp, get_max_hp(mon) - 10)
        saved = self.snapshot()
        self.cmd("confirm")
        self.assertEqual(self.snapshot(), saved)
        self.cmd("reset 3=all")
        self.cmd("confirm")
        self.assertEqual(self.row()["evs"], [0] * 6)
        self.assertEqual(self.profile()["completed"], 0)
        self.assertEqual(self.snapshot()["bags"], saved["bags"])
        for key in ("ivs", "nature", "level", "total_exp", "held_item", "status"):
            self.assertEqual(self.row()[key], before[key])

    def test_stale_reset_and_session_refuse_without_resource_changes(self):
        """An intervening EV/HP change invalidates an exact preview; no old fields restore."""
        from pokemon.models.core import OwnedPokemon

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[64, 64, 0, 0, 0, 0])
        self.cmd("reset 3=all")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=self.row()["current_hp"] - 1)
        before = self.snapshot()
        self.assertIn("changed", self.cmd("confirm"))
        self.assertEqual(self.snapshot(), before)
        self.cmd("cancel")
        self.cmd("3=Attack")
        self.cmd("confirm")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[64, 65, 0, 0, 0, 0])
        self.now += timedelta(seconds=30)
        before = self.snapshot()
        self.assertIn("changed", self.cmd("continue pace"))
        self.assertEqual(self.snapshot(), before)

    def test_final_step_rollback_and_retry(self):
        """A real post-save fault rolls EV/HP/profile back before exactly one retry."""
        from pokemon.models.core import OwnedPokemon

        self.cmd("3=Attack")
        self.cmd("confirm")
        for _ in range(2):
            self.now += timedelta(seconds=30)
            self.cmd("continue technique")
        self.now += timedelta(seconds=30)
        before, profile = self.snapshot(), self.profile()
        original = OwnedPokemon.save

        def refuse(mon, *args, **kwargs):
            """Write through the real SQL save before aborting this private operation."""
            value = original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and mon.evs[1] == 64:
                raise RuntimeError("training post-write fixture refusal")
            return value

        with patch.object(OwnedPokemon, "save", refuse):
            self.cmd("continue recovery")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.profile(), profile)
        self.cmd("continue recovery")
        self.assertEqual(self.row()["evs"][1], 64)
        self.assertEqual(self.profile()["completed"], 1)

    def test_concurrent_final_step_has_one_gain_and_one_milestone(self):
        """Two fresh connections claiming the same step serialize one EV/item receipt."""
        from django.db import connections

        self.finish()
        owner = self.players[0].character
        profile = self.profile()
        profile["completed"] = 5
        owner.attributes.add(self.service().key, profile)
        EVIDENCE.append({"label": "separate-milestone-prerequisite", "prior_useful_sessions": 5})
        self.cmd("3=Attack")
        self.cmd("confirm")
        for _ in range(2):
            self.now += timedelta(seconds=30)
            self.cmd("continue technique")
        self.now += timedelta(seconds=30)
        expected, barrier = self.service().token(), Barrier(2)

        def claim():
            """Keep unexpected database/mechanics errors visible rather than count them as refusals."""
            from pokemon.services.training_grounds import TrainingError

            connections.close_all()
            barrier.wait(timeout=10)
            try:
                return self.service().advance("pace", expected=expected)["changed"]
            except TrainingError:
                return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(lambda _: claim(), range(2)))
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(self.row()["evs"][1], 128)
        self.assertEqual(self.profile()["completed"], 6)
        self.assertEqual(self.players[0].trainer.get_item_quantity("Rare Candy"), 1)

    def test_sixty_useful_sessions_reset_without_rewards_and_gold_once(self):
        """Earn every milestone through commands; free resets never advance the count."""
        for completed in range(1, 62):
            if self.row()["evs"][1] == 252:
                before_count = self.profile()["completed"]
                self.cmd("reset 3=Attack")
                self.cmd("confirm")
                self.assertEqual(self.profile()["completed"], before_count)
            self.finish()
            self.assertEqual(self.profile()["completed"], completed)
            trainer = self.players[0].trainer
            for item, expected in (("Rare Candy", completed // 6), ("Bottle Cap", completed // 12),
                                   ("Gold Bottle Cap", int(completed >= 60))):
                self.assertEqual(trainer.get_item_quantity(item), expected, (completed, item))
        saved = self.snapshot()
        self.cmd("confirm")
        self.cmd("continue pace")
        self.assertEqual(self.snapshot(), saved)

    def test_post_reward_sql_fault_rolls_back_evs_counter_and_all_rewards(self):
        """The third milestone delivery cannot leave partial Candy/Cap/Gold rewards."""
        from pokemon.models.trainer import Trainer

        self.cmd("3=Attack")
        self.cmd("confirm")
        owner, profile = self.players[0].character, self.profile()
        profile["completed"] = 59
        owner.attributes.add(self.service().key, profile)
        EVIDENCE.append({"label": "separate-prior-milestone-prerequisite", "completed": 59})
        for _ in range(2):
            self.now += timedelta(seconds=30)
            self.cmd("continue technique")
        self.now += timedelta(seconds=30)
        before, pending = self.snapshot(), self.profile()
        original = Trainer.add_item

        def fail_after_gold(trainer, item, *args, **kwargs):
            """Preserve the actual SQL credit before the deliberate private failure."""
            value = original(trainer, item, *args, **kwargs)
            if item == "Gold Bottle Cap":
                raise RuntimeError("post-gold training fixture refusal")
            return value

        with patch.object(Trainer, "add_item", fail_after_gold):
            self.cmd("continue recovery")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.profile(), pending)
        self.cmd("continue recovery")
        self.assertEqual(self.row()["evs"][1], 64)
        for item in ("Rare Candy", "Bottle Cap", "Gold Bottle Cap"):
            self.assertEqual(self.players[0].trainer.get_item_quantity(item), 1)

    def test_room_battle_egg_fainted_foreign_and_reservation_guards(self):
        """Current SQL and ordinary custody, rather than old caller/model caches, decide eligibility."""
        from uuid import uuid4
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.ownership import PokemonReservations

        for field, invalid, original in (("is_egg", True, False), ("current_hp", 0, self.row()["current_hp"]),
                                         ("trainer_id", self.players[1].trainer.pk, self.players[0].trainer.pk)):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: invalid})
            before = self.snapshot()
            self.cmd("3=Attack")
            self.assertEqual(self.snapshot(), before)
            self.assertIsNone(self.profile()["pending"])
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**{field: original})
        token = uuid4()
        reservations = PokemonReservations(self.players[0])
        reservations.claim("market", [self.mon.pk], token)
        before = self.snapshot()
        self.cmd("3=Attack")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.profile()["pending"])
        reservations.release("market", token)
        for key in ("battle_lock", "battle_id"):
            self.players[0].character.attributes.add(key, "training-fixture-battle")
            self.cmd("3=Attack")
            self.assertIsNone(self.profile()["pending"])
            self.players[0].character.attributes.remove(key)
        self.players[0].ndb.battle_instance = object()
        self.cmd("3=Attack")
        self.assertIsNone(self.profile()["pending"])
        self.players[0].ndb.battle_instance = None
        self.room.db.training_ground = False
        self.assertIn("Training Grounds", self.cmd("3=Attack"))
        self.assertIsNone(self.profile()["pending"])
        self.room.db.training_ground = True
        self.finish()

    def test_concurrent_reset_and_post_save_reset_failure(self):
        """One reviewed reset commits once; a failed write preserves all fields until retry."""
        from django.db import connections
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.training_grounds import TrainingError

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(evs=[64, 128, 0, 0, 0, 0])
        self.cmd("reset 3=all")
        expected, before, profile = self.service().token(), self.snapshot(), self.profile()
        original = OwnedPokemon.save

        def fail_after_reset(mon, *args, **kwargs):
            value = original(mon, *args, **kwargs)
            if mon.pk == self.mon.pk and list(mon.evs) == [0] * 6:
                raise RuntimeError("reset post-write fixture refusal")
            return value

        with patch.object(OwnedPokemon, "save", fail_after_reset):
            self.cmd("confirm")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.profile(), profile)
        barrier = Barrier(2)

        def claim():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return self.service().confirm(expected=expected)["changed"]
            except TrainingError:
                return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(lambda _: claim(), range(2)))
        self.assertEqual(outcomes.count(True), 1)
        self.assertEqual(self.row()["evs"], [0] * 6)
        self.assertEqual(self.profile()["completed"], 0)
        self.finish("Speed")
        self.assertEqual(self.row()["evs"], [0, 0, 0, 0, 0, 64])

    def test_box_inactive_fusion_and_current_fusion(self):
        """Only the actual current Fusion supplements normal party targets."""
        from pokemon.services.placement import PlacementService

        placement = PlacementService(self.players[0].storage)
        placement.to_box(self.mon)
        self.cmd(str(self.mon.pk) + "=Attack")
        self.assertIsNone(self.profile()["pending"])
        placement.to_party(self.mon, slot=3)
        placement.reserve_for_fusion(self.mon)
        for target in ("fusion", str(self.mon.pk)):
            self.cmd(target + "=Attack")
            self.assertIsNone(self.profile()["pending"])
        self.players[0].character.db.fusion_id = str(self.mon.pk)
        self.cmd("fusion=Attack")
        self.cmd("confirm")
        for _ in range(3):
            self.now += timedelta(seconds=30)
            self.cmd("continue pace")
        self.assertEqual(self.row()["evs"][1], 64)
        self.cmd("reset fusion=Attack/32")
        self.cmd("confirm")
        self.assertEqual(self.row()["evs"][1], 32)

    def test_expiry_level_placement_and_saved_profile_corruption(self):
        """Stale previews and malformed clocks/records cannot manufacture training credit."""
        from copy import deepcopy
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.placement import PlacementService

        self.cmd("3=Attack")
        self.now += timedelta(seconds=301)
        before = self.snapshot()
        self.assertIn("expired", self.cmd("confirm"))
        self.assertEqual(self.snapshot(), before)
        self.cmd("3=Attack")
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(level=51)
        self.assertIn("changed", self.cmd("confirm"))
        self.cmd("cancel")
        self.cmd("3=Attack")
        self.cmd("confirm")
        PlacementService(self.players[0].storage).to_box(self.mon)
        self.now += timedelta(seconds=30)
        before = self.snapshot()
        self.cmd("continue pace")
        self.assertEqual(self.snapshot(), before)
        PlacementService(self.players[0].storage).to_party(self.mon, slot=3)
        profile = self.profile()
        for key, value in (("next_at", profile["pending"]["created_at"]), ("step", True),
                           ("amount", 200), ("baseline", [True, 0, 0, 0, 0, 0])):
            invalid = deepcopy(profile)
            invalid["pending"][key] = value
            self.players[0].character.attributes.add(self.service().key, invalid)
            before = self.snapshot()
            self.assertIn("staff", self.cmd("continue pace"))
            self.assertEqual(self.snapshot(), before)
        self.players[0].character.attributes.add(self.service().key, profile)
        self.cmd("cancel")

    def test_fainted_free_reset_never_revives_and_bad_amounts_do_nothing(self):
        """The useful reset exception permits a fainted owned target without healing."""
        from pokemon.models.core import OwnedPokemon

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=0, evs=[128, 128, 0, 0, 0, 0])
        for amount in ("0", "-1", "253", "129", "1.5", "all/1", "True"):
            before = self.snapshot()
            self.cmd("reset 3=" + (amount if amount.startswith("all") else "HP/" + amount))
            self.assertEqual(self.snapshot(), before)
            self.assertIsNone(self.profile()["pending"])
        self.cmd("reset 3=all")
        self.cmd("confirm")
        self.assertEqual(self.row()["evs"], [0] * 6)
        self.assertEqual(self.row()["current_hp"], 0)
        self.assertEqual(self.profile()["completed"], 0)

    def test_npc_and_pvp_comparison_real_damage_order_and_unchanged_battle_progression(self):
        """Earn 252 Attack/Speed and measure real battles against a faster level-55 native peer."""
        from uuid import uuid4
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.trainer import NPCTrainer, NPCPokemonTemplate
        from pokemon.services.trainer_encounters import generate_static_trainer_encounter

        npc = NPCTrainer.objects.create(name="Training comparison " + uuid4().hex)
        NPCPokemonTemplate.objects.create(npc_trainer=npc, species="Mew", level=55,
            template_key="peer", sort_order=1, ivs=[0] * 6, evs=[0] * 6, nature="Hardy", move_names=["Pound"])

        def measure(mode):
            """Control seed and observe use_move calls without replacing action or damage rules."""
            for mon in (self.mon, self.foe):
                OwnedPokemon.flush_cached_instance(mon)
                OwnedPokemon.objects.get(pk=mon.pk).heal()
            self.session = BattleSession(self.players[0], self.players[1] if mode == "pvp" else None,
                                         rng=random.Random(853))
            if mode == "pvp":
                self.session.start_pvp()
            else:
                self.session.start_trainer_encounter(generate_static_trainer_encounter(npc))
            battle = self.session.battle
            ours, theirs = [participant.active[0] for participant in battle.participants]
            before, evs, turn_before = theirs.hp, list(self.row()["evs"]), battle.turn_count
            battle.rng = random.Random(853)
            battle.debug = True
            with patch.object(battle, "use_move", wraps=battle.use_move) as observe:
                if mode == "pvp":
                    self.turn("A1 Pound B1", "B1 Pound A1", rebuild=False)
                else:
                    self.command("attack", "A1 Pound B1")
                    self.assertEqual(battle.turn_count, turn_before + 1)
            order = [str(call.args[0].pokemon.model_id) for call in observe.call_args_list]
            self.assertEqual(len(order), 2)
            value = {"damage": before - theirs.hp, "our_speed": ours.stats["spe"],
                     "their_speed": theirs.stats["spe"], "our_attack": ours.stats["atk"],
                     "first_is_ours": order[0] == str(ours.model_id), "mode": mode}
            EVIDENCE.append(dict(value, label="real-training-battle-comparison", seed=853,
                                 evs=evs, order=order, captured=True))
            self.assertFalse(getattr(battle, "_callback_failures", []))
            self.session.end()
            self.session = None
            self.assertEqual(self.row()["evs"], evs)
            return value

        baseline = {mode: measure(mode) for mode in ("npc", "pvp")}
        for stat in ("Attack", "Speed"):
            for _ in range(4):
                self.finish(stat)
        self.assertEqual(self.row()["evs"], [0, 252, 0, 0, 0, 252])
        for mode in baseline:
            trained = measure(mode)
            self.assertEqual((baseline[mode]["our_attack"], baseline[mode]["our_speed"]), (105, 105))
            self.assertEqual((trained["our_attack"], trained["our_speed"]), (136, 136))
            self.assertFalse(baseline[mode]["first_is_ours"])
            self.assertTrue(trained["first_is_ours"])
            self.assertGreater(trained["damage"], baseline[mode]["damage"])
        self.cmd("reset 3=all")
        self.cmd("confirm")
        for mode in baseline:
            reset = measure(mode)
            self.assertEqual(reset, baseline[mode])

    def test_real_elapsed_session_requires_three_active_inputs_after_ninety_seconds(self):
        """Use the actual server clock through reconnects; waiting never writes earned progress."""
        from django.db import connection
        from django.utils import timezone

        self.assertEqual(timezone.now.__module__, "django.utils.timezone")
        self.cmd("3=Attack")
        self.cmd("confirm")
        started = time.monotonic()
        for step in range(3):
            pending = self.profile()["pending"]
            self.cmd("continue pace")
            self.assertEqual(self.profile()["pending"]["step"], step)
            while timezone.now().timestamp() < pending["next_at"] + 0.05:
                time.sleep(min(1, pending["next_at"] + 0.05 - timezone.now().timestamp()))
            connection.close()
            self.players[0].attributes.reset_cache()
            self.cmd("status")
            self.assertEqual(self.row()["evs"], [0] * 6)
            self.now = timezone.now()
            self.cmd("continue " + ("technique", "pace", "recovery")[step])
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, 90)
        self.assertEqual(self.row()["evs"][1], 64)
        self.assertEqual(self.profile()["completed"], 1)
        EVIDENCE.append({"label": "actual-elapsed-training-session", "elapsed_seconds": elapsed,
                         "server_clock_unpatched": True, "captured_transport": True,
                         "logged_in_socket_acceptance": False})


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("training-grounds"), IsolatedBattleLogs():
                names = unittest.defaultTestLoader.getTestCaseNames(TrainingCases)
                selected = os.environ.get("PF2_TRAINING_SELECT")
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
                    TrainingCases(name) for name in names if not selected or selected in name))
    finally:
        if os.environ.get("PF2_TRAINING_EVIDENCE"):
            Path(os.environ["PF2_TRAINING_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
