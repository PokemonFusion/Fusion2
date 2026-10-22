"""Ordinary +hold/+flee, capture separation and rebuilds in disposable PG.

An explicit PF2_TEST_POSTGRES_DSN is required. Only session transport and
controlled encounter selection are adapted; commands, queues and persistence
are production implementations. No live game characters or services are used.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

WALKTHROUGH = []


class PlayerView(SessionTransport):
    """Capture output and delegate inventory to the real player implementation."""

    def has_item(self, name, quantity=1):
        """Check real persistent inventory."""
        return User.has_item(self, name, quantity)

    def remove_item(self, name, quantity=1):
        """Debit real persistent inventory."""
        return User.remove_item(self, name, quantity)


class SmokeBallCases(unittest.TestCase):
    """Drive the normal held escape route, including fresh session rebuilds."""

    def setUp(self):
        """Create ordinary owners and full-health, deliberately slow holders."""
        room = ObjectDB.objects.create(db_key="smoke-room-" + uuid4().hex)
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, db=room.db,
                                    ndb=room.ndb, attributes=room.attributes, contents=[])
        self.players = []
        for _ in range(2):
            character = ObjectDB.objects.create(db_key="smoke-player-" + uuid4().hex)
            trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
            player = PlayerView(character, trainer, UserStorage.objects.create(user=character))
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
            self.room.contents.append(player)
            create_owned_pokemon("Shuckle", trainer, 20, ability="Sturdy", nature="Hardy",
                                 ivs=[0] * 6, evs=[0] * 6, active_move_names=["Splash"])
        self.player = self.players[0]
        self.mon = OwnedPokemon.objects.get(trainer=self.player.trainer)
        self.player.trainer.add_item("Smoke Ball", 2)
        self.player.trainer.add_item("Poke Ball", 2)
        self.player.trainer.add_item("Master Ball", 2)
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """End only this case's current local battle."""
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()
        self.search.stop()

    def find(self, query):
        """Resolve character transports while all persistent identities stay real."""
        return [p for p in self.players if query == f"#{p.id}"]

    def command(self, kind, args="", player=None):
        """Use the shipped command parsing and execution entry points."""
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller, command.args = player or self.player, args
        command.cmdstring = "+" + kind
        command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        return command.caller.messages[-1]

    def row(self):
        """Read SQL directly, without relying on cached owned instances."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def inventory(self):
        """Read exact real held-item and capture-ball quantities."""
        return {name: self.player.trainer.get_item_quantity(name)
                for name in ("Smoke Ball", "Poke Ball", "Master Ball")}

    def equip(self):
        """Equip through +hold, consuming one bag copy into the held slot."""
        self.assertIn("now holding Smoke Ball", self.command("hold", "1=Smoke Ball"))
        self.assertEqual(self.row()["held_item"], "Smoke Ball")
        self.assertEqual(self.inventory()["Smoke Ball"], 1)

    def start(self, kind="wild", trap="Arena Trap"):
        """Select a controlled encounter, then use the production battle lifecycle."""
        self.session = BattleSession(self.player, self.players[1] if kind == "pvp" else None)
        if kind in {"wild", "trainer"}:
            foe = create_battle_pokemon("Dugtrio", 50, is_wild=kind == "wild", move_names=["Splash"])
            EncounterPokemon.objects.filter(pk=foe.model_id.split(":", 1)[1]).update(ability=trap)
            foe.ability = trap
            self.session._track_temp_opponent_team([foe])
            battle_type = BattleType.WILD if kind == "wild" else BattleType.TRAINER
            self.session._select_opponent = lambda: (foe, "Fixture Dugtrio", battle_type, "Fixture encounter")
        self.session.start()
        return self.session

    def rebuild(self):
        """Discard live references and reconstruct the durable production checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    def flee(self):
        """Submit +flee and require a real engine outcome, not just queued feedback."""
        self.last_battle = self.session.battle
        self.command("flee")
        if self.last_battle.type == BattleType.PVP:
            self.session.queue_move("Splash", caller=self.players[1])
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        return self.last_battle._flee_result

    def flow(self, trap):
        """Inspect, equip, rebuild, flee and remove the same reusable held copy."""
        detail = self.command("itemdex", "Smoke Ball")
        self.assertIn("+flee", detail)
        self.assertIn("Held Items", detail)
        self.assertIn("Smoke Ball", self.command("inventory"))
        self.equip()
        self.assertIn("Smoke Ball", self.command("party", "1"))
        before, bag = self.row(), self.inventory()
        pp = list(ActiveMoveslot.objects.filter(pokemon=self.mon).values())
        placements = list(self.player.storage.placements.filter(pokemon=self.mon).values())
        self.start(trap=trap)
        # Magnet Pull requires Steel; this is explicit fixture setup, not an item effect.
        if trap == "Magnet Pull":
            self.session.battle.participants[0].active[0].types = ["Steel"]
        self.rebuild()
        result = self.flee()
        self.assertTrue(result["success"])
        self.assertEqual(result["reason"], "smokeball")
        self.assertTrue(self.last_battle.battle_over)
        self.assertNotIn(self.session.battle_id, self.room.db.battles or [])
        self.assertFalse(self.player.db.battle_lock)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.inventory(), bag)
        self.assertEqual(list(ActiveMoveslot.objects.filter(pokemon=self.mon).values()), pp)
        self.assertEqual(list(self.player.storage.placements.filter(pokemon=self.mon).values()), placements)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.player.trainer).count(), 1)
        self.assertFalse(CaptureReceipt.objects.filter(storage=self.player.storage).exists())
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assertEqual(OwnedPokemon.objects.get(pk=self.mon.pk).held_item, "Smoke Ball")
        self.assertIn("returned to your inventory", self.command("hold", "1="))
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.inventory()["Smoke Ball"], 2)
        WALKTHROUGH.append({"trap": trap, "commands": ["+inventory", "+itemdex Smoke Ball",
                            "+hold 1=Smoke Ball", "+party 1", "rebuild checkpoint", "+flee", "+hold 1="],
                            "flee_result": {key: result[key] for key in ("success", "reason", "message")},
                            "held_reusable": True, "unrelated_state_unchanged": True,
                            "capture_receipts": 0, "capture_balls_unchanged": True})

    def restriction(self, kind):
        """Trainer/PvP/no-flee restrictions win even after repeated rebuilds."""
        self.equip()
        self.start("wild" if kind == "no_flee" else kind)
        if kind == "no_flee":
            self.session.battle.flee_allowed = False
        self.rebuild()
        self.rebuild()
        bag = self.inventory()
        result = self.flee()
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "restricted")
        self.assertFalse(self.session.battle.battle_over)
        self.assertEqual(self.inventory(), bag)
        self.assertEqual(self.row()["held_item"], "Smoke Ball")

    def suppression(self, kind):
        """All normal effective-item suppression/removal survives checkpoint restore."""
        self.equip()
        if kind == "klutz":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability="Klutz")
            OwnedPokemon.flush_cached_instance(self.mon)
        self.start()
        holder = self.session.battle.participants[0].active[0]
        if kind == "flag":
            holder.item_suppressed = True
        elif kind == "klutz":
            holder.ability = "Klutz"
        elif kind == "embargo":
            holder.volatiles["embargo"] = {"duration": 5}
        elif kind == "magicroom":
            self.session.battle.field.pseudo_weather["magicroom"] = {"duration": 5}
        else:
            holder.item = ""
        self.rebuild()
        bag = self.inventory()
        self.assertEqual(self.flee()["reason"], "trapped")
        self.assertFalse(self.session.battle.battle_over)
        self.assertEqual(self.inventory(), bag)

    def test_bag_copy_cannot_help(self):
        """The command cannot borrow an effect from the bag."""
        self.start()
        self.assertEqual(self.flee()["reason"], "trapped")
        self.assertEqual(self.inventory()["Smoke Ball"], 2)

    def test_benched_holders_copy_cannot_help_acting_lead(self):
        """Normal +hold on slot two never grants slot one's flee action an effect."""
        create_owned_pokemon("Shuckle", self.player.trainer, 20, ability="Sturdy", nature="Hardy",
                             ivs=[0] * 6, evs=[0] * 6, active_move_names=["Splash"])
        self.assertIn("now holding Smoke Ball", self.command("hold", "2=Smoke Ball"))
        self.start()
        self.rebuild()
        self.assertEqual(self.flee()["reason"], "trapped")
        self.assertEqual(self.row()["held_item"], "")
        self.assertEqual(self.inventory()["Smoke Ball"], 1)

    def test_suppressed_klutz_reactivates_item_after_rebuild(self):
        """An explicitly suppressed Klutz does not disable Smoke Ball."""
        self.equip()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability="Klutz")
        OwnedPokemon.flush_cached_instance(self.mon)
        self.start()
        holder = self.session.battle.participants[0].active[0]
        holder.ability, holder.ability_suppressed = "Klutz", True
        self.rebuild()
        self.assertEqual(self.flee()["reason"], "smokeball")

    def test_item_command_and_direct_choices_reject_without_queue_or_debit(self):
        """Smoke Ball never enters the normal capture/item action route."""
        self.start()
        bag = self.inventory()
        turn = self.session.battle.turn_count
        for args in ("Smoke Ball", "A1 Smoke Ball"):
            self.assertIn("held item", self.command("item", args))
        with self.assertRaisesRegex(ValueError, "held item"):
            self.session.choices_for(self.player).item("Smoke Ball")
        self.assertFalse(self.session.state.declare)
        self.assertEqual(self.session.battle.turn_count, turn)
        self.assertEqual(self.inventory(), bag)
        self.assertFalse(CaptureReceipt.objects.filter(storage=self.player.storage).exists())

    def test_restored_legacy_item_declaration_never_captures_or_debits(self):
        """Old saved Smoke Ball item actions remain harmless at final dispatch."""
        self.start()
        bag = self.inventory()
        holder = self.session.battle.participants[0].active[0]
        self.session.state.declare["A1"] = {"item": "Smoke Ball", "target": "B1",
                                            "trainer": str(self.player.id), "pokemon": holder.model_id}
        self.rebuild()
        action = self.session.battle.participants[0].pending_action
        self.assertIs(action.target, self.session.battle.participants[0])
        self.session.battle.execute_item(action)
        self.assertEqual(self.inventory(), bag)
        self.assertFalse(CaptureReceipt.objects.filter(storage=self.player.storage).exists())
        self.assertFalse(self.session.battle.battle_over)

    def test_real_capture_command_still_targets_wild_debits_and_places(self):
        """A real Master Ball keeps normal capture behavior through +item."""
        self.equip()
        self.start()
        battle = self.session.battle
        self.command("item", "Master Ball")
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertTrue(battle.capture_succeeded)
        self.assertEqual(self.inventory(), {"Smoke Ball": 1, "Poke Ball": 2, "Master Ball": 1})
        self.assertEqual(CaptureReceipt.objects.filter(storage=self.player.storage).count(), 1)
        self.assertEqual(OwnedPokemon.objects.filter(trainer=self.player.trainer).count(), 2)
        self.assertEqual(self.row()["held_item"], "Smoke Ball")


def add_case(name, method, value):
    """Report each trap/policy/suppression as an independently counted case."""
    def case(self):
        return getattr(self, method)(value)
    case.__doc__ = f"{method}: {value}."
    setattr(SmokeBallCases, "test_" + name, case)


for label, trap in (("arena", "Arena Trap"), ("shadow", "Shadow Tag"), ("magnet", "Magnet Pull")):
    add_case("flow_" + label, "flow", trap)
for policy in ("trainer", "pvp", "no_flee"):
    add_case("restricted_" + policy, "restriction", policy)
for effect in ("flag", "klutz", "embargo", "magicroom", "removed"):
    add_case("suppression_" + effect, "suppression", effect)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        from evennia.objects.models import ObjectDB
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import BattleType
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import CaptureReceipt, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.user import User
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_flee, cmd_battle_item, cmd_inventory, cmd_party, cmd_pokedex, cmd_sheet
        COMMANDS = {"hold": (cmd_party, cmd_party.CmdSetHoldItem),
                    "party": (cmd_sheet, cmd_sheet.CmdSheetPokemon),
                    "inventory": (cmd_inventory, cmd_inventory.CmdInventory),
                    "itemdex": (cmd_pokedex, cmd_pokedex.CmdItemdexSearch),
                    "flee": (cmd_battle_flee, cmd_battle_flee.CmdBattleFlee),
                    "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem)}
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SmokeBallCases))
        if os.environ.get("PF2_SMOKE_BALL_EVIDENCE"):
            Path(os.environ["PF2_SMOKE_BALL_EVIDENCE"]).write_text(
                json.dumps(WALKTHROUGH, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
