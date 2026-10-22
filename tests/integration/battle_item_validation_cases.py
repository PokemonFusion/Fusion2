"""Ordinary item input, restored choices and SQL effects in private PostgreSQL."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

EVIDENCE = []


class ItemPlayer(SessionTransport):
    """Capture transport while inventory stays on production User/Trainer rows."""

    def has_item(self, name, quantity=1):
        """Check the real bag without granting stock in the player route."""
        return User.has_item(self, name, quantity)

    def remove_item(self, name, quantity=1):
        """Use the production atomic inventory writer."""
        return User.remove_item(self, name, quantity)


class BattleItemValidationCases(unittest.TestCase):
    """Prove rejection before actions, with supported battle-use controls."""

    def setUp(self):
        """Create tagged ordinary players with production party/move/HP data."""
        room = ObjectDB.objects.create(db_key="item-766-room-" + uuid4().hex)
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, db=room.db,
                                    ndb=room.ndb, attributes=room.attributes, contents=[])
        self.players = []
        self.owned = []
        for _ in range(2):
            character = ObjectDB.objects.create(db_key="item-766-player-" + uuid4().hex,
                                                db_typeclass_path="pokemon.user.User")
            player = ItemPlayer(character, character.trainer, character.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
            roster = []
            for species in ("Squirtle", "Eevee", "Pikachu"):
                roster.append(create_owned_pokemon(species, player.trainer, 20, nature="Hardy",
                              ivs=[0] * 6, evs=[0] * 6, active_move_names=["Splash", "Tackle", "Water Gun"]))
            self.owned.append(roster)
        self.player, self.mon = self.players[0], self.owned[0][0]
        self.room.contents = self.players
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """Release only this test's local session and transport adapter."""
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()
        self.search.stop()

    def find(self, query):
        """Resolve model-backed transports in place of a live Evennia session."""
        return [player for player in self.players if str(player.id) == str(query).lstrip("#")]

    def command(self, args, kind="item", player=None):
        """Execute the real command parser, choices, queue and turn lifecycle."""
        player = player or self.player
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller, command.args, command.cmdstring = player, args, "+" + kind
        command.parse()
        with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
            command.func()
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        return player.messages[-1] if player.messages else ""

    def give(self, item, quantity=2, player=None):
        """Separate disposable bag setup from ordinary player input."""
        (player or self.player).trainer.add_item(item, quantity)

    def state(self, pokemon=None, **fields):
        """Set explicit SQL fixture preconditions and refresh the shared instance."""
        pokemon = pokemon or self.mon
        OwnedPokemon.objects.filter(pk=pokemon.pk).update(**fields)
        # Evennia refresh_from_db can return its own stale identity instance.
        # Discard that fixture reference, then let production party reads reload.
        OwnedPokemon.flush_cached_instance(pokemon)
        OwnedPokemon.objects.get(pk=pokemon.pk)

    def start(self, kind="wild", doubles=False):
        """Use the production session with only encounter selection controlled."""
        self.session = BattleSession(self.player, self.players[1] if kind == "pvp" else None)
        if kind != "pvp":
            foe = create_battle_pokemon("Magikarp", 20, is_wild=kind == "wild", move_names=["Splash"])
            self.session._track_temp_opponent_team([foe])
            self.session._select_opponent = lambda: (foe, "Fixture Magikarp",
                BattleType.WILD if kind == "wild" else BattleType.TRAINER, "Fixture encounter")
        if kind == "pvp":
            self.session.start_pvp(battle_format="double" if doubles else "single")
        else:
            self.session.start()
        return self.session

    def rebuild(self):
        """Drop live references and reconstruct the durable production checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    @staticmethod
    def action_state(action):
        """Retain stable action identities without Python object addresses."""
        if action is None:
            return None
        return {"kind": action.action_type.name, "item": action.item,
                "pokemon": getattr(action.pokemon, "model_id", None),
                "target": getattr(action.target_pokemon, "model_id", None),
                "move": getattr(action.move, "name", None), "item_move": action.item_move}

    def snapshot(self):
        """Read runtime, both persisted declaration views, all bags and SQL rows."""
        if self.session.battle is not None:
            self._snapshot_context = (self.session.battle, self.session.state, self.session.data)
        battle, battle_state, data = self._snapshot_context
        state = {
            "turn": battle.turn_count, "state": battle_state.to_dict(),
            "positions": {name: pos.turninit.to_dict() for name, pos in data.turndata.positions.items()},
            "pending": [[self.action_state(action) for action in (
                part.pending_action if isinstance(part.pending_action, list)
                else [part.pending_action] if part.pending_action else [])] for part in battle.participants],
            "runtime": [[mon.to_dict() for mon in part.pokemons] for part in battle.participants],
            "persisted_state": self.session.storage.get("state"), "persisted_data": self.session.storage.get("data"),
            "controls": [player.db.battle_control for player in self.players],
            "inventory": [list(player.trainer.list_inventory().values("item_name", "quantity")) for player in self.players],
            "inventory_cache": [player.db.inventory for player in self.players],
            "owned": list(OwnedPokemon.objects.filter(trainer__in=[p.trainer for p in self.players]).order_by("pk").values()),
            "moves": list(ActiveMoveslot.objects.filter(pokemon__trainer__in=[p.trainer for p in self.players]).order_by("pk").values()),
            "placements": list(PokemonPlacement.objects.filter(storage__in=[p.storage for p in self.players]).order_by("pk").values()),
            "captures": list(CaptureReceipt.objects.filter(storage__in=[p.storage for p in self.players]).order_by("pk").values()),
        }
        return json.loads(json.dumps(state, default=str))

    def record(self, label, args, player=None):
        """Capture actual input/output and independent SQL before/after state."""
        player = player or self.player
        before, start = self.snapshot(), len(player.messages)
        self.command(args, player=player)
        EVIDENCE.append({"label": label, "command": "+item " + args, "before": before,
                         "after": self.snapshot(), "messages": player.messages[start:]})

    def test_fresh_water_and_oran_rejected_without_any_action_or_state_change(self):
        """Reproduce the audit: unsupported stocked items cannot waste turn 1."""
        self.state(current_hp=1)
        for item in ("Fresh Water", "Oran Berry"):
            self.give(item)
        self.start()
        for args in ("Fresh Water", "A1 Fresh Water=1", "Oran Berry", "A1 ORAN-BERRY=1"):
            before = self.snapshot()
            self.record("unsupported-player-item", args)
            self.assertEqual(self.snapshot(), before)
            self.assertIn("+use", self.player.messages[-1])

    def test_other_unsupported_stock_held_and_unknown_names_rejected(self):
        """Capacity/progression/held/unknown stock never becomes a battle action."""
        for item in ("PP Up", "PP Max", "Rare Candy", "Leftovers", "Light Ball", "Unknown Item", "Smoke Ball"):
            self.give(item)
        self.start()
        for item in ("PP Up", "PP Max", "Rare Candy", "Leftovers", "Light Ball", "Unknown Item", "Smoke Ball"):
            before = self.snapshot()
            self.record("unsupported-family", item)
            self.assertEqual(self.snapshot(), before)
            self.assertIn("+flee" if item == "Smoke Ball" else "+use", self.player.messages[-1])

    def test_direct_choices_and_public_queue_share_policy(self):
        """Bypassing the command cannot persist an unsupported declaration."""
        self.give("Fresh Water")
        self.start()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "supported manual battle"):
            self.session.choices_for(self.player).item("Fresh Water", actor="A1")
        self.assertFalse(self.session.queue_item("Fresh Water", caller=self.player, actor="A1"))
        self.assertEqual(self.snapshot(), before)

    def test_supported_item_with_missing_stock_does_not_queue(self):
        """A legal item still requires current inventory before any declaration."""
        self.start()
        before = self.snapshot()
        self.record("supported-but-no-stock", "Potion")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("do not have", self.player.messages[-1])

    def test_potion_after_rejection_uses_same_turn_and_only_one_copy(self):
        """A rejected input leaves the actor free for a supported healing action."""
        self.state(current_hp=1)
        self.give("Fresh Water")
        self.give("Potion")
        self.start()
        self.record("unsupported-before-potion", "Fresh Water")
        self.record("supported-potion", "Potion")
        self.assertEqual(self.session.battle.turn_count, 2)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("current_hp", flat=True).get(), 21)
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Fresh Water"), 2)

    def test_supported_no_effect_keeps_existing_action_cost_without_debit(self):
        """A full-health Potion is supported, so its queued no-effect turn remains."""
        self.give("Potion")
        self.start()
        before = self.snapshot()
        self.record("supported-no-effect", "Potion")
        after = self.snapshot()
        self.assertEqual(after["turn"], before["turn"] + 1)
        for field in ("owned", "inventory", "inventory_cache", "placements", "captures"):
            self.assertEqual(after[field], before[field])
        self.assertTrue(any("had no effect" in text for text in self.player.messages))

    def test_reserve_revival_and_selected_move_ether_after_rebuild(self):
        """Revive and selected-move PP restoration keep ordinary targeting."""
        reserve = self.owned[0][2]
        self.state(reserve, current_hp=0)
        ActiveMoveslot.objects.filter(pokemon=reserve, slot__in=[2, 3]).update(current_pp=0)
        self.give("Revive")
        self.give("Ether")
        self.start()
        self.rebuild()
        self.record("supported-reserve-revival", "Revive=3")
        row = OwnedPokemon.objects.filter(pk=reserve.pk).values().get()
        self.assertEqual(row["current_hp"], get_max_hp(reserve) // 2)
        self.rebuild()
        self.record("supported-reserve-selected-ether", "Ether=3/Water Gun")
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=reserve).order_by("slot").values_list("current_pp", flat=True)), [40, 0, 10])
        self.assertEqual(self.player.trainer.get_item_quantity("Ether"), 1)

    def test_elixir_and_max_ether_keep_raw_capacity_after_rebuild(self):
        """Both multi-move and selected-slot restoratives use stored raw PP."""
        tackle = self.mon.activemoveslot_set.get(slot=2).move
        MovePPBoost.objects.create(pokemon=self.mon, move=tackle, bonus_pp=21)
        self.mon.activemoveslot_set.update(current_pp=0)
        self.give("Elixir")
        self.give("Max Ether")
        self.start()
        self.record("supported-elixir", "Elixir")
        self.assertEqual(list(self.mon.activemoveslot_set.order_by("slot").values_list("current_pp", flat=True)), [10, 10, 10])
        self.rebuild()
        self.record("supported-max-ether", "Max Ether=1/2")
        self.assertEqual(list(self.mon.activemoveslot_set.order_by("slot").values_list("current_pp", flat=True)), [10, 56, 10])

    def test_capture_after_rejection_and_rebuild_keeps_exact_ball_route(self):
        """A genuine wild capture still consumes its ball and saves one catch."""
        self.give("Fresh Water")
        self.give("Master Ball")
        self.start()
        self.record("unsupported-before-capture", "Fresh Water")
        self.rebuild()
        battle = self.session.battle
        self.record("supported-wild-capture", "Master Ball")
        self.assertTrue(battle.capture_succeeded)
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 1)
        self.assertEqual(self.player.trainer.get_item_quantity("Fresh Water"), 2)
        self.assertEqual(CaptureReceipt.objects.filter(storage=self.player.storage).count(), 1)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.player.trainer).count(), 4)

    def test_trainer_and_pvp_capture_restrictions_do_not_spend_action(self):
        """Manual capability does not override the wild-only capture restriction."""
        self.give("Master Ball")
        self.start("trainer")
        before = self.snapshot()
        self.record("trainer-ball-rejected", "Master Ball")
        self.assertEqual(self.snapshot(), before)
        self.assertIn("wild", self.player.messages[-1])

    def test_doubles_rejection_preserves_sibling_and_all_actor_choices(self):
        """Unsupported A2/B2 inputs cannot erase queued A1/B1 actions."""
        for player in self.players:
            self.give("Fresh Water", player=player)
            self.give("Potion", player=player)
        self.state(self.owned[0][1], current_hp=1)
        self.state(self.owned[1][1], current_hp=1)
        self.start("pvp", doubles=True)
        self.command("A1 Splash", "attack")
        before = self.snapshot()
        self.record("doubles-A2-rejected", "A2 Fresh Water=2")
        self.assertEqual(self.snapshot(), before)
        self.command("A2 Potion=2")
        self.command("B1 Splash", "attack", self.players[1])
        before = self.snapshot()
        self.record("doubles-B2-rejected", "B2 Fresh Water=2", self.players[1])
        self.assertEqual(self.snapshot(), before)
        self.record("doubles-B2-potion", "B2 Potion=2", self.players[1])
        self.assertEqual(self.session.battle.turn_count, 2)
        for roster, player in zip(self.owned, self.players):
            self.assertEqual(OwnedPokemon.objects.filter(pk=roster[1].pk).values_list("current_hp", flat=True).get(), 21)
            self.assertEqual(player.trainer.get_item_quantity("Potion"), 1)

    def test_doubles_actor_selection_and_pvp_ball_reject_without_queue(self):
        """Valid item capability still requires an owned explicit actor in doubles."""
        self.give("Potion")
        self.give("Poke Ball")
        self.start("pvp", doubles=True)
        before = self.snapshot()
        for args in ("Potion", "B1 Potion", "A1 Poke Ball"):
            self.record("actor-or-capture-rejected", args)
            self.assertEqual(self.snapshot(), before)

    def inject(self, item="Fresh Water", *, pending=True, declaration=True, position=True):
        """Fixture a legacy invalid input in any of the three saved action views."""
        actor = self.session.battle.participants[0]
        pokemon = actor.active[0]
        if declaration:
            self.session.state.declare["A1"] = {"item": item, "target": "A1",
                "trainer": str(self.player.id), "pokemon": pokemon.model_id}
        if position:
            self.session.data.turndata.positions["A1"].declareItem(item)
        action = Action(actor, ActionType.ITEM, actor, item=item, pokemon=pokemon, target_pokemon=pokemon)
        if pending:
            actor.pending_action = action
        self.session._persist_turn_state()
        return action

    def test_restored_bad_doubles_choice_preserves_valid_sibling(self):
        """Discard one old A2 item without losing A1's paid-in-PP move choice."""
        self.give("Oran Berry")
        self.give("Potion")
        self.start("pvp", doubles=True)
        self.command("A1 Splash", "attack")
        actor = self.session.battle.participants[0]
        pokemon = actor.active[1]
        good = actor.pending_action
        bad = Action(actor, ActionType.ITEM, actor, item="Oran Berry", pokemon=pokemon, target_pokemon=pokemon)
        actor.pending_action = [good, bad]
        self.session.state.declare["A2"] = {"item": "Oran Berry", "trainer": str(self.player.id), "pokemon": pokemon.model_id}
        self.session.data.turndata.positions["A2"].declareItem("Oran Berry")
        before = self.snapshot()
        self.rebuild()
        after = self.snapshot()
        for field in ("turn", "owned", "inventory", "moves", "placements", "captures"):
            self.assertEqual(after[field], before[field])
        self.assertEqual(set(self.session.state.declare), {"A1"})
        self.assertEqual(self.session.battle.participants[0].pending_action.move.name, "Splash")
        self.command("A2 Potion=2")
        self.command("B1 Splash", "attack", self.players[1])
        self.command("B2 Splash", "attack", self.players[1])
        self.assertEqual(self.session.battle.turn_count, 2)
        self.assertEqual(self.mon.activemoveslot_set.get(slot=1).current_pp, 39)
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 2)

    def assert_discarded(self, before):
        """A stale input is removed, with turn, bags and Pokemon state preserved."""
        after = self.snapshot()
        for field in ("turn", "owned", "inventory", "inventory_cache", "moves", "placements", "captures", "runtime"):
            self.assertEqual(after[field], before[field], field)
        self.assertNotIn("A1", self.session.state.declare)
        self.assertIsNone(self.session.data.turndata.positions["A1"].turninit.item)
        self.assertIsNone(self.session.battle.participants[0].pending_action)
        self.assertNotIn("A1", self.session.storage.get("state")["declare"])

    def test_restored_unsupported_declaration_cannot_resurrect_on_second_rebuild(self):
        """Old field-only declarations free the actor before restored readiness."""
        self.give("Fresh Water")
        self.start()
        self.inject()
        before = self.snapshot()
        self.rebuild()
        self.assert_discarded(before)
        self.rebuild()
        self.assert_discarded(before)
        self.give("Potion")
        self.command("Potion")
        self.assertEqual(self.session.battle.turn_count, before["turn"] + 1)

    def test_readiness_discards_stale_input_before_auto_opponent_or_turn(self):
        """A ready-looking old item never grants the opponent a free action."""
        self.give("Oran Berry")
        self.start()
        self.inject("Oran Berry")
        before = self.snapshot()
        self.assertFalse(self.session.is_turn_ready())
        self.assert_discarded(before)

    def test_direct_session_turn_discards_invalid_deferred_action(self):
        """Direct turn entry shares the guard before disabling player control."""
        self.give("Fresh Water")
        self.start()
        self.inject()
        before = self.snapshot()
        self.session.run_turn()
        self.assert_discarded(before)
        self.assertTrue(self.player.db.battle_control)

    def test_deferred_pending_only_and_position_only_are_discarded(self):
        """Orphan legacy pending and PositionData views cannot bypass checks."""
        self.give("Fresh Water")
        self.start()
        for pending, position in ((True, False), (False, True)):
            self.inject(pending=pending, declaration=False, position=position)
            before = self.snapshot()
            self.assertFalse(self.session.is_turn_ready())
            self.assert_discarded(before)

    def test_direct_engine_turn_rejects_before_counter_or_effects(self):
        """A caller bypassing session readiness still cannot spend the turn."""
        self.give("Fresh Water")
        self.start()
        self.inject()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "supported manual battle"):
            self.session.battle.run_turn()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_empty_and_null_saved_item_choices_are_discarded(self):
        """An explicit invalid item value is distinct from no item declaration."""
        self.start()
        for item in (None, ""):
            self.inject(item)
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "supported manual battle"):
                self.session.battle.run_turn()
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(self.session.is_turn_ready())
            self.assert_discarded(before)

    def test_final_dispatch_rejects_unsupported_without_no_effect_or_debit(self):
        """Even an action constructed outside the queue cannot invoke a field item."""
        self.give("Fresh Water")
        self.start()
        action = self.inject()
        before = self.snapshot()
        self.session.battle.execute_item(action)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(getattr(action, "item_executed", False))

    def test_supported_declaration_survives_rebuild_and_preserves_target_move(self):
        """A queued reserve Ether keeps its actor/target/move while waiting on PvP."""
        reserve = self.owned[0][2]
        reserve.activemoveslot_set.filter(slot=3).update(current_pp=0)
        self.give("Ether")
        self.start("pvp")
        self.command("A1 Ether=3/Water Gun")
        self.assertEqual(self.session.battle.turn_count, 1)
        self.rebuild()
        action = self.session.battle.participants[0].pending_action
        self.assertEqual((action.item, action.item_move, action.target_pokemon.model_id), ("Ether", "Water Gun", "owned:" + str(reserve.pk)))
        self.command("B1 Splash", "attack", self.players[1])
        self.assertEqual(self.session.battle.turn_count, 2)
        self.assertEqual(reserve.activemoveslot_set.get(slot=3).current_pp, 10)
        self.assertEqual(self.player.trainer.get_item_quantity("Ether"), 1)

    def test_stale_capture_on_nonwild_rebuild_is_discarded(self):
        """A formerly accepted ball declaration cannot bypass capture restrictions."""
        self.give("Master Ball")
        self.start("pvp")
        self.inject("Master Ball")
        before = self.snapshot()
        self.rebuild()
        self.assert_discarded(before)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        from evennia.objects.models import ObjectDB
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import Action, ActionType, BattleType
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import CaptureReceipt, PokemonPlacement
        from pokemon.user import User
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_battle_item
        COMMANDS = {"item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                    "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack)}
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BattleItemValidationCases))
        if os.environ.get("PF2_BATTLE_ITEM_EVIDENCE"):
            Path(os.environ["PF2_BATTLE_ITEM_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
