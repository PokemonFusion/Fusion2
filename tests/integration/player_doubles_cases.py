"""Ordinary player doubles commands and complete battles on disposable PostgreSQL."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class PlayerDoublesCases(unittest.TestCase):
    """Exercise production requests, commands, queues, engine turns and rebuilds."""

    def setUp(self):
        """Give each ordinary player three real owned party members."""
        room = ObjectDB.objects.create(db_key="Doubles room " + uuid4().hex[:8])
        self.room = SimpleNamespace(id=room.pk, key=room.key, db=room.db, ndb=room.ndb,
                                    attributes=room.attributes, contents=[], msg_contents=lambda message: None)
        self.players = []
        for side in ("Host", "Guest"):
            character = ObjectDB.objects.create(db_key=side + uuid4().hex[:8])
            trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
            player = PlayerView(character, trainer, UserStorage.objects.create(user=character))
            player.location = self.room
            self.players.append(player)
            for species in ("Squirtle", "Eevee", "Pikachu"):
                create_owned_pokemon(species, trainer, 20, ivs=[0] * 6, evs=[0] * 6, nature="Hardy",
                                     active_move_names=["Tackle", "Water Gun", "Surf", "Helping Hand"])
        self.room.contents = self.players
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()
        self.pvp_search = patch("evennia.search_object", self.find)
        self.pvp_search.start()

    def tearDown(self):
        """Release only the case's local session and transport patches."""
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()
        self.search.stop()
        self.pvp_search.stop()

    def find(self, query):
        """Resolve real model-backed character transports without an Evennia process."""
        return [player for player in self.players if str(player.id) == str(query).lstrip("#")]

    def command(self, kind, arguments, player=None):
        """Execute an actual normal-player command boundary."""
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller = player or self.players[0]
        command.args = arguments
        command.cmdstring = kind
        if kind == "attack":
            command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()

    def launch(self):
        """Create, join and start doubles through the ordinary PvP commands."""
        self.command("create", "double")
        self.command("join", self.players[0].key, self.players[1])
        requests = self.room.db.pvp_requests
        self.assertEqual(requests[self.players[0].id].battle_format, "double")
        self.assertEqual(requests[self.players[0].id].opponent_id, self.players[1].id)
        self.command("start", "")
        self.session = self.players[0].ndb.battle_instance
        self.assertIsNotNone(self.session, self.players[0].messages)
        self.assertEqual([len(part.active) for part in self.session.battle.participants], [2, 2])
        self.assertFalse(self.room.db.pvp_requests)
        return self.session

    def rebuild(self):
        """Discard both runtime transports and restore the durable battle choices."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    def test_commands_keep_both_actions_and_restore_targets(self):
        """Two normal inputs survive a rebuild and spend each actor's own PP."""
        session = self.launch()
        self.command("attack", "A1 Water Gun B2")
        self.command("attack", "A2 Tackle B1")
        self.assertEqual(set(session.state.declare), {"A1", "A2"})
        session = self.rebuild()
        actions = session.battle.participants[0].pending_action
        self.assertEqual(len(actions), 2)
        self.assertEqual([action.target_slot for action in actions], [1, 0])
        self.command("attack", "B1 Tackle A1", self.players[1])
        self.command("attack", "B2 Tackle A2", self.players[1])
        self.assertFalse(session.turn_state.get("error"), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)
        for part, move_index in ((session.battle.participants[0], 1), (session.battle.participants[1], 0)):
            for index, mon in enumerate(part.active):
                selected = move_index if index == 0 else 0
                stored = OwnedPokemon.objects.get(pk=mon.model_id.split(":", 1)[1])
                self.assertEqual(stored.current_hp, mon.hp)
                slot = stored.activemoveslot_set.get(slot=selected + 1)
                self.assertLess(slot.current_pp, get_pp(MOVEDEX[_normalize_key(slot.move.name)]))

    def test_invalid_and_stale_targets_do_not_overwrite_sibling(self):
        """Foreign actors, ambiguous targets and stale target refs remain unqueued."""
        session = self.launch()
        self.command("attack", "B1 Tackle A1")
        self.command("attack", "A1 Water Gun")
        self.command("attack", "A1 Water Gun B3")
        self.assertFalse(session.state.declare)
        self.command("attack", "A1 Water Gun B2")
        self.command("attack", "A2 Tackle B1")
        session.state.declare["A1"]["target_ref"] = "owned:999999999"
        session = self.rebuild()
        self.assertEqual(set(session.state.declare), {"A2"})
        self.assertEqual(session.battle.participants[0].pending_action.pokemon,
                         session.data.turndata.positions["A2"].pokemon)

    def test_switch_second_slot_and_target_follows_incoming(self):
        """A2's legal reserve replaces A2 and receives the B2 attack aimed there."""
        session = self.launch()
        own = session.battle.participants[0]
        lead_ref, reserve_ref = own.pokemons[0].model_id, own.pokemons[2].model_id
        before_hp = own.pokemons[2].hp
        self.command("switch", "A2 3")
        self.command("attack", "A1 Tackle B1")
        self.command("attack", "B1 Tackle A1", self.players[1])
        self.command("attack", "B2 Tackle A2", self.players[1])
        self.assertFalse(session.turn_state.get("error"), session.turn_state)
        self.assertEqual(active_at(own, 0).model_id, lead_ref)
        self.assertEqual(active_at(own, 1).model_id, reserve_ref)
        self.assertLess(active_at(own, 1).hp, before_hp)

    def test_one_remaining_slot_advances_and_survives_rebuild(self):
        """An empty A1 never steals A2's identity or blocks readiness."""
        session = self.launch()
        own = session.battle.participants[0]
        active_slots(own)
        survivor_ref = own.active[1].model_id
        own.pokemons[0].hp = own.pokemons[2].hp = 0
        session.battle.run_faint()
        session._sync_active_battle_state()
        session = self.rebuild()
        self.assertNotIn("A1", session.state.positions)
        self.assertEqual(session.data.turndata.positions["A2"].pokemon.model_id, survivor_ref)
        self.command("attack", "A2 Tackle B2")
        self.command("attack", "B1 Tackle A2", self.players[1])
        self.command("attack", "B2 Tackle A2", self.players[1])
        self.assertFalse(session.turn_state.get("error"), session.turn_state)
        self.assertEqual(session.battle.turn_count, 2)

    def test_complete_doubles_battle_via_player_commands(self):
        """Play both normal sides to a terminal result, including forced reserves."""
        session = self.launch()
        battle = session.battle
        for _ in range(50):
            if battle.battle_over:
                break
            turn = battle.turn_count
            for player in self.players:
                if battle.battle_over:
                    break
                choices = session.choices_for(player)
                for name, pos in list(choices.positions().items()):
                    if battle.battle_over:
                        break
                    opponents = choices.battle.opponents_of(choices.participant)
                    target = next(label for label, slot in session.data.turndata.positions.items()
                                  if any(mon is slot.pokemon for part in opponents for mon in part.active))
                    self.command("attack", f"{name} Tackle {target}", player)
            self.assertFalse(session.turn_state.get("error"), session.turn_state)
            self.assertGreater(battle.turn_count, turn)
        self.assertTrue(battle.battle_over, "The complete battle did not terminate")
        self.assertIsNone(self.players[0].db.battle_id)
        self.assertIsNone(self.players[1].db.battle_id)
        self.assertNotIn(session.battle_id, self.room.db.battles or [])

    def test_expired_interactive_move_prompt_cannot_queue(self):
        """An actual command callback remembers its actor and original turn."""
        session = self.launch()
        import evennia.utils.evmenu as evmenu
        callbacks = []
        with patch.object(evmenu, "get_input", side_effect=lambda caller, prompt, callback: callbacks.append(callback)):
            self.command("attack", "A2")
        self.assertEqual(len(callbacks), 1)
        for name, target, player in (("A1", "B1", self.players[0]), ("A2", "B2", self.players[0]),
                                     ("B1", "A1", self.players[1]), ("B2", "A2", self.players[1])):
            self.command("attack", f"{name} Tackle {target}", player)
        self.assertEqual(session.battle.turn_count, 2)
        callbacks[0](self.players[0], "", "A B1")
        self.assertFalse(session.state.declare)
        self.assertIn("earlier turn", self.players[0].messages[-1])

    def test_gapped_party_switch_prompt_preserves_sibling_choice_and_rebuild(self):
        """Doubles commands display canonical reserves and persist internal indices."""
        from evennia.utils import evmenu

        own = self.players[0].storage.get_party()
        placement = PlacementService(self.players[0].storage)
        placement.to_party(own[1], 4)
        placement.to_party(own[0], 2)
        placement.to_party(own[2], 6)
        session = self.launch()
        self.command("attack", "A1 Tackle B1")
        saved = dict(session.state.declare["A1"])
        callbacks, prompts = [], []
        with patch.object(evmenu, "get_input", side_effect=lambda caller, prompt, callback: (prompts.append(prompt), callbacks.append(callback))):
            self.command("switch", "A2")
        self.assertIn("6. Pikachu", prompts[0])
        self.assertNotIn("3. Pikachu", prompts[0])
        callbacks[0](self.players[0], "", "6")
        self.assertEqual(session.state.declare["A1"], saved)
        self.assertEqual(session.state.declare["A2"]["switch"], 3)
        restored = self.rebuild()
        self.assertEqual(restored.state.declare["A1"], saved)
        self.assertEqual(restored.state.declare["A2"]["switch"], 3)
        self.command("attack", "B1 Tackle A1", self.players[1])
        self.command("attack", "B2 Tackle A1", self.players[1])
        self.assertEqual(active_at(restored.battle.participants[0], 1).model_id, f"owned:{own[2].pk}")
        self.assertEqual(self.players[0].storage.get_party_slots(), [None, own[0], None, own[1], None, own[2]])

    def test_readiness_rechecked_without_consuming_request(self):
        """A guest who faints after joining cannot consume the ready room request."""
        self.command("create", "double")
        self.command("join", self.players[0].key, self.players[1])
        party = self.players[1].storage.get_party()
        for mon in list(party)[1:]:
            mon.current_hp = 0
            mon.save(update_fields=["current_hp"])
        self.command("start", "")
        self.assertIsNone(self.players[0].ndb.battle_instance)
        self.assertIsNone(self.players[1].ndb.battle_instance)
        self.assertIn(self.players[0].id, self.room.db.pvp_requests)
        self.assertIn("two conscious", self.players[0].messages[-1])

    def test_item_checkpoints_preserve_removal_swap_and_legacy_fallback(self):
        """Owned and encounter restores keep battle items, including an empty slot."""
        from pokemon.battle.battledata import Pokemon
        from pokemon.services.encounters import create_encounter_pokemon, encounter_ref
        from utils.pokemon_utils import build_battle_pokemon_from_model

        owned = self.players[0].storage.get_party()[0]
        owned.held_item = "Leftovers"
        owned.save(update_fields=["held_item"])
        encounter = create_encounter_pokemon(
            species="Eevee", level=20, source_kind="wild", held_item="Leftovers",
        )
        for model, reference in ((owned, f"owned:{owned.pk}"), (encounter, encounter_ref(encounter))):
            with self.subTest(reference=reference):
                initial = build_battle_pokemon_from_model(model)
                initial.model_id = reference
                self.assertEqual(getattr(initial.item, "name", initial.item), "Leftovers")
                legacy = initial.to_dict()
                del legacy["item"]
                legacy_item = Pokemon.from_dict(legacy).item
                self.assertEqual(getattr(legacy_item, "name", legacy_item), "Leftovers")
                for item in (None, "", "Choice Scarf"):
                    initial.item = item
                    restored = Pokemon.from_dict(initial.to_dict())
                    self.assertEqual(getattr(restored.item, "name", restored.item), item)
                self.assertEqual(model.held_item, "Leftovers")

    def test_spread_nonstat_messages_and_effects_survive_rebuild(self):
        """Real move commands summarize healing, volatiles and group item removal."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.services.move_management import initialize_generated_moveset

        for name, volatile in (("Life Dew", None), ("Teeter Dance", "confusion"),
                               ("Heal Block", "healblock"), ("Corrosive Gas", None)):
            with self.subTest(move=name):
                for index, player in enumerate(self.players):
                    player.messages.clear()
                    for slot, mon in enumerate(player.storage.get_party()):
                        mon.heal()
                        mon.nickname = f"Side {index} Member {slot}"
                        if name == "Life Dew" and index == 0:
                            mon.current_hp = get_max_hp(mon)//2
                        mon.held_item = "Leftovers" if name == "Corrosive Gas" else ""
                        mon.save()
                lead = self.players[0].storage.get_party()[0]
                initialize_generated_moveset(lead, active_move_names=[name], replace_active=True)
                session = self.launch()
                own, foe = session.battle.participants
                if name == "Corrosive Gas":
                    self.assertTrue(all(mon.item for part in (own, foe) for mon in part.active))
                start_hp = {mon.model_id:mon.hp for mon in own.active}
                self.command("attack", f"A1 {name}")
                self.command("attack", "A2 Helping Hand A1")
                self.command("attack", "B1 Helping Hand B2", self.players[1])
                self.command("attack", "B2 Helping Hand B1", self.players[1])
                self.assertEqual(session.battle.turn_count, 2)
                self.assertFalse(session.turn_state.get("error"), session.turn_state)
                text = "\n".join(self.players[0].messages)
                targets = own.active if name == "Life Dew" else (foe.active if name == "Heal Block" else [*foe.active,own.active[1]])
                for mon in targets:
                    summary = f"used {name}!" if mon is own.active[0] else f"used {name} on {mon.name}!"
                    self.assertIn(summary, text)
                    self.assertNotIn(f"used {name} on {mon.name} but it had no effect", text)
                if name == "Life Dew":
                    self.assertGreater(own.active[1].hp, start_hp[own.active[1].model_id])
                elif volatile:
                    self.assertTrue(all(volatile in mon.volatiles for mon in targets))
                    if volatile == "confusion":
                        self.assertTrue(all(isinstance(mon.volatiles[volatile], dict) for mon in targets))
                        self.assertTrue(all(mon.volatiles[volatile]["turns"] > 0 for mon in targets))
                else:
                    self.assertTrue(all(not mon.item for mon in targets))
                stored = OwnedPokemon.objects.get(pk=lead.pk)
                self.assertEqual(stored.activemoveslot_set.get(slot=1).current_pp, get_pp(MOVEDEX[_normalize_key(name)])-1)
                restored = self.rebuild()
                self.assertEqual(restored.battle.turn_count, 2)
                self.assertFalse(restored.turn_state.get("error"))
                if name == "Corrosive Gas":
                    own, foe = restored.battle.participants
                    self.assertTrue(own.active[0].item)
                    self.assertTrue(all(not mon.item for mon in [*foe.active, own.active[1]]))
                if volatile == "confusion":
                    targets = [*restored.battle.participants[1].active,
                               restored.battle.participants[0].active[1]]
                    durations = {mon.model_id: mon.volatiles[volatile]["turns"] for mon in targets}
                    with patch("pokemon.dex.functions.conditions_funcs.random.random", return_value=1.0):
                        self.command("attack", "A1 Teeter Dance")
                        self.command("attack", "A2 Helping Hand A1")
                        self.command("attack", "B1 Helping Hand B2", self.players[1])
                        self.command("attack", "B2 Helping Hand B1", self.players[1])
                    self.assertEqual(restored.battle.turn_count, 3)
                    self.assertFalse(restored.turn_state.get("error"))
                    self.assertTrue(all(mon.volatiles[volatile]["turns"] == durations[mon.model_id] - 1
                                        for mon in targets))
                self.session.end()


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_battle_switch, cmd_pvp
        from pokemon.battle._shared import _normalize_key, get_pp
        from pokemon.battle.active_slots import active_at, active_slots
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.dex import MOVEDEX
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService

        COMMANDS = {"attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                    "switch": (cmd_battle_switch, cmd_battle_switch.CmdBattleSwitch),
                    "create": (cmd_pvp, cmd_pvp.CmdPvpCreate), "join": (cmd_pvp, cmd_pvp.CmdPvpJoin),
                    "start": (cmd_pvp, cmd_pvp.CmdPvpStart)}
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PlayerDoublesCases))
        raise SystemExit(not result.wasSuccessful())
