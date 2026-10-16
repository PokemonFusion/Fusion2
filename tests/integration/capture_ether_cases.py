"""Capture debit and Ether regressions in a guarded disposable PostgreSQL schema.

Run with an explicit PF2_TEST_POSTGRES_DSN. Production tables are built directly;
no migrations, service operations or live game data are involved.
"""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class ItemFixture(unittest.TestCase):
    """Build real owned Pokémon, inventory and battle representations."""

    def setUp(self):
        """Keep each case's player and party entirely inside the test schema."""
        character = ObjectDB.objects.create(db_key="capture-ether-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=character)
        self.player = SimpleNamespace(
            key=character.key, trainer=self.trainer, storage=self.storage,
            db=character.db, ndb=SimpleNamespace(), msg=lambda text: None,
        )
        self.owned = create_owned_pokemon(
            "Squirtle", self.trainer, 5, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Watergun", "Tailwhip"],
        )

    def battle(self, target=None):
        """Construct a new battle as on reconnect, with the same owned slots."""
        active = build_battle_pokemon_from_model(self.owned)
        actor = BattleParticipant("Player", [active], player=self.player)
        foe = BattleParticipant("Foe", [target or Pokemon("Rattata", hp=10, max_hp=20)])
        actor.active, foe.active = [active], [foe.pokemons[0]]
        battle = Battle(BattleType.WILD, [actor, foe])
        return battle, actor, foe

    def race(self, *actions):
        """Run competing calls on distinct real PostgreSQL connections."""
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                return pid, action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            results = [future.result(timeout=30) for future in [pool.submit(run, action) for action in actions]]
        self.assertEqual(len({pid for pid, _ in results}), len(actions))
        return [result for _, result in results]


class CaptureDebitCases(ItemFixture):
    """Successful retries, competing claims and failures cannot double-debit."""

    def encounter(self):
        """Return one persisted encounter and a pre-capture battle snapshot."""
        encounter = create_encounter_pokemon(
            species="Rattata", level=5, source_kind="wild", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, current_hp=1, move_names=["Quickattack"],
        )
        target = Pokemon("Rattata", hp=1, max_hp=get_max_hp(encounter), model_id=f"encounter:{encounter.pk}")
        return encounter, target.to_dict()

    def throw(self, snapshot):
        """Execute an actual engine item action from a restored snapshot."""
        battle, actor, foe = self.battle(Pokemon.from_dict(snapshot))
        battle.execute_item(Action(actor, ActionType.ITEM, foe, item="masterball"))
        return battle, foe

    def test_successful_snapshot_replay_spends_one_ball(self):
        """A successful pre-capture snapshot never debits or rolls twice."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        with patch("pokemon.battle.capture.attempt_capture", return_value=CaptureOutcome(True, 4, False)) as roll:
            for _ in range(2):
                battle, foe = self.throw(snapshot)
                self.assertTrue(foe.has_lost)
                self.assertTrue(battle.battle_over)
        self.assertEqual(roll.call_count, 1)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def test_replay_succeeds_after_spending_the_last_ball(self):
        """The receipt is checked before an empty inventory can reject recovery."""
        self.trainer.add_item("masterball", 1)
        encounter, snapshot = self.encounter()
        self.throw(snapshot)
        battle, foe = self.throw(snapshot)
        self.assertTrue(foe.has_lost)
        self.assertTrue(battle.battle_over)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 0)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)

    def test_replay_after_release_does_not_recreate_or_debit(self):
        """A retained receipt still protects the ball after releasing the catch."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        self.throw(snapshot)
        caught_id = CaptureReceipt.objects.get(encounter_id=encounter.pk).owned_id
        PlacementService(self.storage).release(OwnedPokemon.objects.get(pk=caught_id))
        self.throw(snapshot)
        self.assertFalse(OwnedPokemon.objects.filter(pk=caught_id).exists())
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def test_replay_cleans_restored_temporary_tracking(self):
        """Recovery still removes the captured encounter from saved temp IDs."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        self.throw(snapshot)
        reference = f"encounter:{encounter.pk}"
        writes = Mock()
        session = SimpleNamespace(temp_pokemon_ids=[reference, "encounter:other"], storage=SimpleNamespace(set=writes))
        self.player.ndb.battle_instance = session
        self.throw(snapshot)
        self.assertEqual(session.temp_pokemon_ids, ["encounter:other"])
        writes.assert_called_once_with("temp_pokemon_ids", ["encounter:other"])
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def test_capture_commit_failure_rolls_back_ball_and_owned_creation(self):
        """Failure after placement restores the item and encounter for a retry."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        count = OwnedPokemon.objects.count()
        with patch.object(CaptureReceipt.objects, "create", side_effect=RuntimeError("isolated receipt failure")):
            _, foe = self.throw(snapshot)
        self.assertFalse(foe.has_lost)
        self.assertEqual(OwnedPokemon.objects.count(), count)
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 2)
        self.throw(snapshot)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)

    def test_failed_throw_spends_one_ball_and_later_success_spends_one(self):
        """Legitimate unsuccessful throws remain ordinary paid attempts."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        with patch("pokemon.battle.capture.attempt_capture", return_value=CaptureOutcome(False, 1, False)):
            _, foe = self.throw(snapshot)
        self.assertFalse(foe.has_lost)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)
        self.assertFalse(CaptureReceipt.objects.filter(encounter_id=encounter.pk).exists())
        self.throw(snapshot)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 0)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)

    def test_partial_inventory_failure_rolls_back_and_never_rolls(self):
        """Even a remover failing after its SQL debit cannot lose the item."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        original = Trainer.remove_item

        def remove_then_fail(trainer, *args, **kwargs):
            original(trainer, *args, **kwargs)
            raise RuntimeError("isolated post-debit failure")

        with patch.object(Trainer, "remove_item", remove_then_fail), patch("pokemon.battle.capture.attempt_capture") as roll:
            self.throw(snapshot)
        roll.assert_not_called()
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 2)
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())

    def test_missing_encounter_spends_nothing(self):
        """A stale identifier with no receipt cannot consume an item."""
        self.trainer.add_item("masterball", 1)
        encounter, snapshot = self.encounter()
        encounter.delete()
        self.throw(snapshot)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def resolve(self, snapshot, player=None, trainer=None):
        """Use the production attempt boundary for concurrent claim checks."""
        trainer = trainer or self.trainer
        try:
            return WildCaptureAttempt(
                target_poke=Pokemon.from_dict(snapshot), player=player or self.player,
                trainer=trainer, ball_name="masterball",
            ).resolve(roll=lambda: CaptureOutcome(True, 4, False), consume_ball=lambda: trainer.remove_item("masterball"))
        except PlacementError as error:
            return error

    def test_concurrent_successful_replays_debit_once(self):
        """Independent PostgreSQL connections share the same successful claim."""
        self.trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        results = self.race(lambda: self.resolve(snapshot), lambda: self.resolve(snapshot))
        self.assertEqual(results[0].placement.owned_pokemon_id, results[1].placement.owned_pokemon_id)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def test_competing_owners_only_winner_pays(self):
        """A foreign claim discovered after waiting never charges the loser."""
        character = ObjectDB.objects.create(db_key="other-capture-" + uuid4().hex)
        other_trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        other_player = SimpleNamespace(storage=UserStorage.objects.create(user=character))
        for trainer in (self.trainer, other_trainer):
            trainer.add_item("masterball", 2)
        encounter, snapshot = self.encounter()
        results = self.race(lambda: self.resolve(snapshot), lambda: self.resolve(snapshot, other_player, other_trainer))
        self.assertEqual(sum(isinstance(result, PlacementError) for result in results), 1)
        self.assertEqual(CaptureReceipt.objects.filter(encounter_id=encounter.pk).count(), 1)
        self.assertEqual(sum(trainer.get_item_quantity("masterball") for trainer in (self.trainer, other_trainer)), 3)


class EtherCases(ItemFixture):
    """PP caps, persistence and item debit remain consistent across failures."""

    def set_pp(self, pp, *, slot=1):
        """Change the actual saved PP, rather than only the battle cache."""
        self.owned.activemoveslot_set.filter(slot=slot).update(current_pp=pp)

    def pp(self, *, slot=1):
        """Read fresh SQL after each operation."""
        return self.owned.activemoveslot_set.filter(slot=slot).values_list("current_pp", flat=True).get()

    def use(self, *, cached_pp=None, display_name=None):
        """Use Ether through the actual battle engine and return its snapshot."""
        battle, actor, _ = self.battle()
        active = actor.active[0]
        if cached_pp is not None:
            active.moves[0].pp = cached_pp
        if display_name:
            active.moves[0].name = display_name
        battle.execute_item(Action(actor, ActionType.ITEM, actor, item="ether"))
        return active

    def test_restoration_survives_snapshot_and_next_battle(self):
        """The stored slot wins over stale PP and display-name differences."""
        self.trainer.add_item("ether", 2)
        self.set_pp(1)
        active = self.use(cached_pp=24, display_name="Water Gun")
        self.assertEqual(self.pp(), 11)
        self.assertEqual(active.moves[0].pp, 11)
        self.assertEqual(Pokemon.from_dict(active.to_dict()).moves[0].pp, 11)
        rebuilt = build_battle_pokemon_from_model(self.owned)
        self.assertEqual(rebuilt.to_dict()["moves"][0]["pp"], 11)
        self.assertEqual(self.trainer.get_item_quantity("ether"), 1)

    def test_pp_is_capped_at_move_maximum(self):
        """Water Gun at 24/25 restores one PP and consumes one Ether."""
        self.trainer.add_item("ether", 2)
        self.set_pp(24)
        active = self.use(cached_pp=24)
        self.assertEqual(self.pp(), 25)
        self.assertEqual(active.moves[0].pp, 25)
        self.assertEqual(self.trainer.get_item_quantity("ether"), 1)

    def test_pp_boost_changes_the_restoration_cap(self):
        """PP bonuses belong to the stored move, not its display spelling."""
        slot = self.owned.activemoveslot_set.get(slot=1)
        MovePPBoost.objects.create(pokemon=self.owned, move=slot.move, bonus_pp=10)
        self.trainer.add_item("ether", 1)
        self.set_pp(33)
        active = self.use(display_name="Water Gun")
        self.assertEqual(self.pp(), 35)
        self.assertEqual(active.moves[0].pp, 35)

    def test_full_first_move_is_skipped_for_next_depleted_move(self):
        """The implicit Ether target is the first move that can gain PP."""
        self.trainer.add_item("ether", 1)
        self.set_pp(3, slot=2)
        active = self.use()
        self.assertEqual(self.pp(), 25)
        self.assertEqual(self.pp(slot=2), 13)
        self.assertEqual(active.moves[1].pp, 13)

    def test_all_moves_full_does_not_spend_item(self):
        """A stale cached deficit cannot cause a pointless inventory debit."""
        self.trainer.add_item("ether", 1)
        self.use(cached_pp=1)
        self.assertEqual(self.pp(), 25)
        self.assertEqual(self.trainer.get_item_quantity("ether"), 1)

    def test_zero_pp_can_be_restored(self):
        """An exhausted move gains usable saved PP."""
        self.trainer.add_item("ether", 1)
        self.set_pp(0)
        self.use()
        self.assertEqual(self.pp(), 10)

    def test_no_item_does_not_restore_pp(self):
        """Item availability remains a precondition for the effect."""
        self.set_pp(1)
        self.use()
        self.assertEqual(self.pp(), 1)

    def test_pp_write_failure_rolls_back_item_and_snapshot(self):
        """A failure after the SQL write undoes both sides of the operation."""
        self.trainer.add_item("ether", 1)
        self.set_pp(1)
        original = ActiveMoveslot.save

        def save_then_fail(slot, *args, **kwargs):
            original(slot, *args, **kwargs)
            raise RuntimeError("isolated PP write failure")

        with patch.object(ActiveMoveslot, "save", save_then_fail):
            active = self.use(cached_pp=1)
        self.assertEqual(self.pp(), 1)
        self.assertEqual(active.moves[0].pp, 1)
        self.assertEqual(self.trainer.get_item_quantity("ether"), 1)

    def test_last_ether_is_not_used_twice_concurrently(self):
        """Two independent connections cannot get two effects from one item."""
        self.trainer.add_item("ether", 1)
        self.set_pp(1)
        active_a = build_battle_pokemon_from_model(self.owned)
        active_b = build_battle_pokemon_from_model(self.owned)

        def restore(active):
            return BattlePPRestoration(active, self.trainer).restore(lambda: self.trainer.remove_item("ether"))

        results = self.race(lambda: restore(active_a), lambda: restore(active_b))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.pp(), 11)
        self.assertEqual(self.trainer.get_item_quantity("ether"), 0)

    def test_reserved_fusion_uses_durable_pp(self):
        """The same item path restores an active Fusion's reserved Pokémon."""
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.trainer.add_item("ether", 1)
        self.set_pp(1)
        self.use()
        form = get_battle_party_with_fusion(self.player)[0]
        self.assertEqual(build_battle_pokemon_from_model(form).to_dict()["moves"][0]["pp"], 11)

    def test_inventory_cache_is_not_refreshed_on_rollback(self):
        """The trainer cache follows committed inventory, not a rolled-back debit."""
        self.trainer.add_item("ether", 1)
        refresh = Mock()
        with patch.object(Trainer, "_sync_character_inventory", refresh):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.trainer.remove_item("ether")
                raise RuntimeError("isolated rollback")
            refresh.assert_not_called()
        self.assertEqual(self.trainer.get_item_quantity("ether"), 1)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        from django.db import close_old_connections, connection, connections, transaction
        from evennia.objects.models import ObjectDB

        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.capture import CaptureOutcome
        from pokemon.battle.engine import Action, ActionType, Battle, BattleParticipant, BattleType
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import CaptureReceipt, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.battle_items import BattlePPRestoration
        from pokemon.services.capture import WildCaptureAttempt
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementError, PlacementService
        from utils.fusion import get_battle_party_with_fusion
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)
