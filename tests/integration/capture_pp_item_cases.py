"""Captured PP, Full Restore and inventory names on isolated PostgreSQL.

Run with PF2_TEST_POSTGRES_DSN. Production model tables are built directly in
a guarded disposable schema; no migrations or running game data are touched.
"""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class CapturePPItemCases(unittest.TestCase):
    """Verify actual saved effects, replay behavior and equivalent names."""

    def setUp(self):
        """Create one ordinary trainer and a real party member in our schema."""
        character = ObjectDB.objects.create(db_key="capture-pp-items-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=character)
        self.player = SimpleNamespace(
            key=character.key, trainer=self.trainer, storage=self.storage,
            db=character.db, ndb=SimpleNamespace(), msg=lambda text: None,
            has_item=self.trainer.has_item,
        )
        self.owned = create_owned_pokemon(
            "Squirtle", self.trainer, 5, nature="Hardy", ivs=[0] * 6, evs=[0] * 6,
            active_move_names=["Watergun"],
        )
        self.active = build_battle_pokemon_from_model(self.owned)
        self.actor = BattleParticipant("Player", [self.active], player=self.player)
        self.foe = BattleParticipant("Wild", [Pokemon("Rattata", hp=1, max_hp=20)])
        self.actor.active, self.foe.active = [self.active], [self.foe.pokemons[0]]
        self.battle = Battle(BattleType.WILD, [self.actor, self.foe])

    def encounter(self, *, names=None, pp=None):
        """Create a persisted encounter whose saved PP is deliberately reduced."""
        encounter = create_encounter_pokemon(
            species="Rattata", level=5, source_kind="wild", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, current_hp=1,
            move_names=names or ["Quickattack"], move_pp=pp if pp is not None else [2],
        )
        target = Pokemon("Rattata", hp=1, max_hp=get_max_hp(encounter), model_id=f"encounter:{encounter.pk}")
        return encounter, target

    def capture(self, target):
        """Finalize with production placement and read the committed owned row."""
        result = finalize_wild_capture(target_poke=target, player=self.player, trainer=self.trainer)
        _, identifier = parse_pokemon_ref(result.owned_pokemon_id)
        return OwnedPokemon.objects.get(pk=identifier)

    def saved_pp(self, pokemon):
        """Read move identities and PP directly from SQL."""
        return dict(pokemon.activemoveslot_set.order_by("slot").values_list("move__name", "current_pp"))

    def sync(self):
        """Run real battle cleanup and refresh the model to avoid cached proof."""
        BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=self.battle))
        self.owned.refresh_from_db()

    def race(self, *actions):
        """Start calls together on separate actual PostgreSQL connections."""
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

    def test_capture_saved_pp_survives_storage_new_battle_and_heal(self):
        """Capture fallback preserves the original QA encounter's 2/30 PP."""
        _, target = self.encounter()
        caught = self.capture(target)
        self.assertEqual(list(self.saved_pp(caught).values()), [2])
        box = StorageBox.objects.create(storage=self.storage, name="PP Box")
        service = PlacementService(self.storage)
        service.to_box(caught, box)
        service.to_party(caught, 2)
        caught.refresh_from_db()
        rebuilt = build_battle_pokemon_from_model(caught)
        self.assertEqual(rebuilt.to_dict()["moves"][0]["pp"], 2)
        self.assertEqual(Pokemon.from_dict(rebuilt.to_dict()).moves[0].pp, 2)
        caught.heal()
        self.assertEqual(list(self.saved_pp(caught).values()), [30])

    def test_capture_live_pp_wins_by_name_including_zero(self):
        """Reordered display spellings must map onto the correct owned slots."""
        _, target = self.encounter(names=["Quickattack", "Tackle", "Tailwhip"], pp=[12, 13, 14])
        target.moves = [Move("Tail Whip"), Move("Quick Attack"), Move("Tackle")]
        for move, pp in zip(target.moves, [3, 0, 4]):
            move.pp = pp
        caught = self.capture(target)
        values = {normalize_name(name): pp for name, pp in self.saved_pp(caught).items()}
        self.assertEqual(values, {"quickattack": 0, "tackle": 4, "tailwhip": 3})

    def test_real_wild_attacks_keep_spent_pp_through_capture(self):
        """Factory moves spend PP through real attacks before becoming owned."""
        target = create_battle_pokemon("Rattata", 5, is_wild=True, move_names=["Quickattack"])
        self.foe.pokemons = self.foe.active = [target]
        for _ in range(2):
            self.battle.use_move(Action(self.foe, ActionType.MOVE, self.actor, BattleMove("Quick Attack"), pokemon=target))
        self.assertEqual(target.moves[0].pp, 28)
        restored = Pokemon.from_dict(target.to_dict())
        caught = self.capture(restored)
        self.assertEqual(list(self.saved_pp(caught).values()), [28])

    def test_encounter_rebuild_uses_saved_pp_and_respects_exhaustion(self):
        """Rebuilding without snapshot moves cannot give an exhausted move PP."""
        _, target = self.encounter(pp=[0])
        restored = Pokemon.from_dict(target.to_dict())
        self.assertEqual(restored.moves[0].pp, 0)
        self.foe.pokemons = self.foe.active = [restored]
        hp = self.active.hp
        self.battle.use_move(Action(self.foe, ActionType.MOVE, self.actor, BattleMove("Quick Attack"), pokemon=restored))
        self.assertEqual(self.active.hp, hp)
        self.assertEqual(restored.moves[0].pp, 0)

    def test_capture_retry_cannot_reset_current_owned_pp(self):
        """A late pre-capture snapshot cannot overwrite PP used after capture."""
        _, target = self.encounter()
        caught = self.capture(target)
        caught.activemoveslot_set.update(current_pp=1)
        target.moves = [Move("Quick Attack")]
        target.moves[0].pp = 30
        retry = self.capture(target)
        self.assertEqual(retry.pk, caught.pk)
        self.assertEqual(list(self.saved_pp(retry).values()), [1])

    def test_captured_pp_is_clamped_to_legal_bounds(self):
        """Snapshot values cannot create negative or excessive owned PP."""
        for pp, expected in [(-2, 0), (999, 30)]:
            with self.subTest(pp=pp):
                _, target = self.encounter()
                target.moves = [Move("Quick Attack")]
                target.moves[0].pp = pp
                self.assertEqual(list(self.saved_pp(self.capture(target)).values()), [expected])

    def test_pp_save_failure_rolls_back_capture_and_ball(self):
        """PP transfer is part of the existing atomic capture transaction."""
        encounter, target = self.encounter()
        self.foe.pokemons = self.foe.active = [target]
        self.trainer.add_item("masterball", 1)
        count = OwnedPokemon.objects.count()
        with patch.object(ActiveMoveslot, "save", side_effect=RuntimeError("isolated captured PP failure")):
            self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.foe, item="Master Ball"))
        self.assertEqual(OwnedPokemon.objects.count(), count)
        self.assertFalse(CaptureReceipt.objects.filter(encounter_id=encounter.pk).exists())
        self.assertTrue(EncounterPokemon.objects.filter(pk=encounter.pk).exists())
        self.assertEqual(self.trainer.get_item_quantity("masterball"), 1)

    def test_full_restore_heals_and_cures_each_major_condition_once(self):
        """Both effects persist, share one debit and leave spent PP alone."""
        self.owned.activemoveslot_set.update(current_pp=1)
        for status in ["psn", "tox", "brn", "par", "slp", "frz"]:
            with self.subTest(status=status):
                self.trainer.add_item("fullrestore", 2)
                self.active.hp = 3
                self.active.setStatus(status)
                before = self.trainer.get_item_quantity("Full Restore")
                self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.foe, item="Full Restore"))
                self.sync()
                self.assertEqual(self.owned.current_hp, get_max_hp(self.owned))
                self.assertEqual(self.owned.status, "")
                self.assertIsNone(self.owned.sleep_turns)
                self.assertEqual(self.trainer.get_item_quantity("fullrestore"), before - 1)
                self.assertEqual(list(self.saved_pp(self.owned).values()), [1])

    def test_full_restore_hp_only_and_status_only(self):
        """Either useful effect alone permits exactly one item use."""
        self.trainer.add_item("Full Restore", 2)
        self.active.hp = 3
        self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.actor, item="fullrestore"))
        self.assertEqual(self.active.hp, self.active.max_hp)
        self.active.setStatus("psn")
        self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.actor, item="Full Restore"))
        self.assertFalse(self.active.status)
        self.assertEqual(self.trainer.get_item_quantity("fullrestore"), 0)

    def test_full_restore_healthy_and_fainted_targets_have_no_effect(self):
        """Full Restore neither wastes an item on healthy targets nor revives."""
        self.trainer.add_item("fullrestore", 2)
        self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.actor, item="Full Restore"))
        self.active.hp = 0
        self.active.setStatus("psn")
        self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.actor, item="Full Restore"))
        self.assertEqual((self.active.hp, self.active.status), (0, "psn"))
        self.assertEqual(self.trainer.get_item_quantity("fullrestore"), 2)

    def test_full_restore_item_failure_does_not_heal_or_cure(self):
        """A rejected inventory debit cannot apply either effect."""
        self.trainer.add_item("fullrestore", 1)
        self.active.hp = 3
        self.active.setStatus("psn")
        with patch.object(Trainer, "remove_item", return_value=False):
            self.battle.execute_item(Action(self.actor, ActionType.ITEM, self.actor, item="Full Restore"))
        self.assertEqual((self.active.hp, self.active.status), (3, "psn"))
        self.assertEqual(self.trainer.get_item_quantity("fullrestore"), 1)

    def test_ball_name_variants_share_one_inventory_record(self):
        """Accents, case, spacing and punctuation resolve to the same item."""
        for alias in ["Poke Ball", "Poké Ball", "POKE-BALL", "pokeball"]:
            self.trainer.add_item(alias)
        self.assertEqual(list(self.trainer.inventory.values_list("item_name", "quantity")), [("pokeball", 4)])
        for alias in ["Poke Ball", "Poké Ball", "POKE-BALL", "pokeball"]:
            self.assertTrue(self.trainer.has_item(alias))
            self.assertTrue(self.trainer.remove_item(alias))
        self.assertEqual(self.trainer.get_item_quantity("Poke Ball"), 0)

    def test_legacy_alias_rows_share_quantity_without_losing_other_balls(self):
        """Existing display/compact rows work without a migration or rewrite."""
        InventoryEntry.objects.create(owner=self.trainer, item_name="Poké Ball", quantity=1)
        InventoryEntry.objects.create(owner=self.trainer, item_name="pokeball", quantity=2)
        self.trainer.add_item("Great Ball", 4)
        self.assertEqual(self.trainer.get_item_quantity("Poke Ball"), 3)
        self.assertFalse(self.trainer.remove_item("Poke Ball", 4))
        self.assertEqual(self.trainer.get_item_quantity("pokeball"), 3)
        self.assertTrue(self.trainer.remove_item("Poke Ball", 3))
        self.assertEqual(self.trainer.get_item_quantity("pokeball"), 0)
        self.assertEqual(self.trainer.get_item_quantity("Great Ball"), 4)

    def test_add_reuses_legacy_spelling(self):
        """An existing display spelling does not gain a duplicate alias row."""
        InventoryEntry.objects.create(owner=self.trainer, item_name="Poke Ball", quantity=1)
        self.trainer.add_item("pokeball", 2)
        self.assertEqual(self.trainer.inventory.count(), 1)
        self.assertEqual(self.trainer.get_item_quantity("Poké Ball"), 3)

    def test_concurrent_alias_additions_and_last_ball_removal(self):
        """Alias normalization retains quantities under competing SQL writers."""
        self.race(lambda: self.trainer.add_item("Poke Ball"), lambda: self.trainer.add_item("Poké Ball"))
        self.assertEqual(self.trainer.inventory.count(), 1)
        self.assertEqual(self.trainer.get_item_quantity("pokeball"), 2)
        self.assertTrue(self.trainer.remove_item("pokeball"))
        results = self.race(lambda: self.trainer.remove_item("Poke Ball"), lambda: self.trainer.remove_item("Poké Ball"))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.trainer.get_item_quantity("pokeball"), 0)

    def test_real_battle_command_accepts_display_ball_names(self):
        """Command validation, engine use and durable debit agree on aliases."""
        self.trainer.add_item("pokeball", 3)
        self.player.db.battle_control = True
        instance = SimpleNamespace(battle=self.battle)
        instance.queue_item = lambda *args, **kwargs: self.battle.execute_item(self.actor.pending_action)
        system = SimpleNamespace(battle_manager=SimpleNamespace(for_player=lambda caller: instance))
        for name in ["Poke Ball", "Poké Ball", "Poke-Ball"]:
            encounter, target = self.encounter()
            self.foe.has_lost = False
            self.foe.pokemons = self.foe.active = [target]
            with patch("commands.player.cmd_battle_item.get_system", return_value=system), patch(
                "pokemon.battle.capture.attempt_capture", return_value=CaptureOutcome(True, 4, False),
            ):
                cmd = CmdBattleItem()
                cmd.caller, cmd.args = self.player, name
                cmd.func()
            self.assertTrue(CaptureReceipt.objects.filter(encounter_id=encounter.pk).exists())
        self.assertEqual(self.trainer.get_item_quantity("pokeball"), 0)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.db import close_old_connections, connection, connections
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        # The standalone Django process has not populated Evennia's flat API.
        # Supply its real Command class without starting a game service.
        with patch.object(evennia, "Command", Command):
            from commands.player.cmd_battle_item import CmdBattleItem
        from pokemon.battle.battledata import Move, Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.capture import CaptureOutcome
        from pokemon.battle.engine import Action, ActionType, Battle, BattleMove, BattleParticipant, BattleType
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import CaptureReceipt, StorageBox, UserStorage
        from pokemon.models.trainer import InventoryEntry, Trainer
        from pokemon.names import normalize_name
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.services.pokemon_refs import parse_pokemon_ref
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)
