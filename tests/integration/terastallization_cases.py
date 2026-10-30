"""Ordinary Tera commands, checkpoints and rollback on disposable PostgreSQL."""

from __future__ import annotations

import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class TerastallizationCases(unittest.TestCase):
    """Keep player models, persistence and complete engine turns real."""

    def setUp(self):
        """Give two ordinary players canonical parties and saved Tera types."""
        room = ObjectDB.objects.create(db_key="Tera room " + uuid4().hex[:8])
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
                mon = create_owned_pokemon(species, trainer, 20, ivs=[0] * 6, evs=[0] * 6, nature="Hardy",
                                           active_move_names=["Tackle", "Water Gun", "Surf", "Tera Blast"])
                mon.tera_type = "Stellar" if species == "Eevee" else "Water"
                mon.save(update_fields=["tera_type"])
        self.room.contents = self.players
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()
        self.pvp_search = patch("evennia.search_object", self.find)
        self.pvp_search.start()

    def tearDown(self):
        """Clean up only this case's session and transport patches."""
        if self.session and not getattr(self.session, "_ended", False):
            self.session.end()
        self.search.stop()
        self.pvp_search.stop()

    def find(self, query):
        """Resolve model-backed test transports through ordinary battle lookup."""
        return [player for player in self.players if str(player.id) == str(query).lstrip("#")]

    def command(self, kind, arguments, player=None):
        """Execute a real, registered player command without staff privileges."""
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller, command.args, command.cmdstring = player or self.players[0], arguments, kind
        if kind == "attack":
            command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()

    def launch(self, battle_format="double"):
        """Start singles or doubles through the normal PvP create/join flow."""
        self.command("create", battle_format)
        self.command("join", self.players[0].key, self.players[1])
        self.command("start", "")
        self.session = self.players[0].ndb.battle_instance
        self.assertIsNotNone(self.session, self.players[0].messages)
        self.session.battle.rng = random.Random(3)
        return self.session

    def rebuild(self):
        """Discard live references, retaining only the room's saved checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    def declare_turn(self):
        """Fill all four real actions while deferring turn execution for assertions."""
        with patch.object(self.session, "maybe_run_turn"):
            for actor, target, player in (("A1", "B1", self.players[0]), ("A2", "B1", self.players[0]),
                                           ("B1", "A1", self.players[1]), ("B2", "A2", self.players[1])):
                self.command("attack", f"{actor} Water Gun {target}", player)
        self.assertEqual(len(self.session.state.declare), 4)

    def test_doubles_command_reservation_and_spent_boost_rebuild(self):
        """A2's declaration, use and spent Stellar type survive two rebuilds."""
        self.launch()
        self.command("tera", "A2")
        self.assertIn("Stellar", self.players[0].messages[-1])
        self.command("tera", "A1")
        self.assertIn("reserved", self.players[0].messages[-1])
        session = self.rebuild()
        self.assertEqual(session.battle.tera_pending["A"]["type"], "Stellar")
        self.declare_turn()
        session.execute_persistent_turn()
        self.assertEqual(session.battle.tera_used, {"A"})
        self.assertEqual(session.battle.participants[0].active[1].stellar_boosted_types, ["Water"])
        session = self.rebuild()
        mon = session.battle.participants[0].active[1]
        self.assertEqual((mon.terastallized, mon.types, mon.stellar_boosted_types), ("Stellar", ["Normal"], ["Water"]))
        self.command("tera", "A1")
        self.assertIn("already used", self.players[0].messages[-1])
        from evennia.utils.ansi import strip_ansi

        text = display_battle_interface(self.players[0], self.players[1], session.state, viewer_team="A")
        plain = strip_ansi(text)
        a1 = plain.split("YOU  Squirtle (A1)", 1)[1].split("YOU  Eevee (A2)", 1)[0]
        a2 = plain.split("YOU  Eevee (A2)", 1)[1]
        self.assertIn("[Tera Stellar]", a2)
        self.assertNotIn("[Tera Stellar]", a1)
        for style in ("legacy", "classic_modern", "pf1"):
            with self.subTest(style=style):
                classic = display_battle_interface(
                    self.players[0], self.players[1], session.state,
                    viewer_team="A", style=style,
                )
                self.assertIn("A2: Tera Stellar", strip_ansi(classic))

    def test_singles_command_and_independent_opposing_side(self):
        """An omitted actor works in singles; each side may use its own allowance."""
        session = self.launch("single")
        self.command("tera", "")
        self.command("tera", "", self.players[1])
        self.command("attack", "Water Gun B1")
        self.command("attack", "Water Gun A1", self.players[1])
        self.assertFalse(session.turn_state.get("error"), session.turn_state)
        self.assertEqual(session.battle.tera_used, {"A", "B"})
        rebuilt = self.rebuild()
        self.assertEqual(rebuilt.battle.tera_used, {"A", "B"})
        self.assertTrue(all(part.active[0].types == ["Water"] for part in rebuilt.battle.participants))

    def test_failed_checkpoint_rolls_back_use_typing_pp_and_stellar_charge(self):
        """A failed turn restores one pending declaration and permits one clean retry."""
        session = self.launch()
        self.command("tera", "A2")
        self.declare_turn()
        original_set = session.storage.set

        def fail_checkpoint(key, value):
            """Fail only after the engine has transformed and used its attacks."""
            if key == "data":
                raise RuntimeError("injected checkpoint failure")
            return original_set(key, value)

        before = [(mon.pk, mon.current_hp, list(mon.activemoveslot_set.values_list("current_pp", flat=True)))
                  for mon in OwnedPokemon.objects.filter(trainer=self.players[0].trainer)]
        with patch.object(session.storage, "set", side_effect=fail_checkpoint):
            with self.assertRaisesRegex(RuntimeError, "checkpoint failure"):
                session.execute_persistent_turn()
        self.assertFalse(session.battle.tera_used)
        self.assertEqual(session.battle.tera_pending["A"]["type"], "Stellar")
        self.assertIsNone(session.battle.participants[0].active[1].terastallized)
        self.assertFalse(session.battle.participants[0].active[1].stellar_boosted_types)
        self.assertEqual(
            {identifier: hp for identifier, hp, _pp in before},
            dict(OwnedPokemon.objects.filter(trainer=self.players[0].trainer).values_list("pk", "current_hp")),
        )
        after = [(mon.pk, mon.current_hp, list(mon.activemoveslot_set.values_list("current_pp", flat=True)))
                 for mon in OwnedPokemon.objects.filter(trainer=self.players[0].trainer)]
        self.assertEqual(before, after)
        session.execute_persistent_turn()
        self.assertEqual(session.battle.tera_used, {"A"})
        self.assertEqual(session.battle.participants[0].active[1].stellar_boosted_types, ["Water"])

    def test_end_preserves_owned_configuration_and_reverts_runtime_typing(self):
        """Concession/cleanup leaves configured Tera types and species untouched."""
        session = self.launch()
        self.command("tera", "A2")
        self.declare_turn()
        session.execute_persistent_turn()
        mon = session.battle.participants[0].active[1]
        session.end()
        self.assertIsNone(mon.terastallized)
        self.assertEqual(mon.types, ["Normal"])
        stored = OwnedPokemon.objects.get(pk=mon.model_id.split(":", 1)[1])
        self.assertEqual((stored.species, stored.tera_type), ("Eevee", "Stellar"))

    def test_configured_npc_stellar_type_survives_encounter_checkpoint(self):
        """Existing encounter data selects Stellar without adding a database column."""
        from pokemon.battle.battledata import Pokemon
        from pokemon.services.trainer_encounters import generate_random_trainer_encounter

        self.room.db.npc_trainer_chart = [{"species": "Eevee", "min_level": 20, "max_level": 20,
                                          "tera_type": "Stellar", "move_names": ["Tera Blast"],
                                          "ai_profile": "trainer_tera"}]
        encounter = generate_random_trainer_encounter(self.room, rng=random.Random(4))
        self.assertEqual(encounter.ai_profile, "trainer_tera")
        mon = encounter.team[0]
        self.assertEqual(mon.tera_type, "Stellar")
        rebuilt = Pokemon.from_dict(mon.to_dict())
        self.assertEqual((rebuilt.tera_type, rebuilt.types, rebuilt.terastallized), ("Stellar", ["Normal"], None))

    def test_legacy_owned_checkpoint_uses_configuration_only_when_key_is_absent(self):
        """Legacy loads inherit configuration; explicit checkpoint values win."""
        from pokemon.battle.battledata import Pokemon

        session = self.launch()
        original = session.battle.participants[0].active[1]
        payload = original.to_dict()
        payload.pop("tera_type")
        self.assertEqual(Pokemon.from_dict(payload).tera_type, "Stellar")
        for value in ("", "Fire"):
            with self.subTest(saved_type=value):
                payload["tera_type"] = value
                self.assertEqual(Pokemon.from_dict(payload).tera_type, value)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_battle_tera, cmd_pvp
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.interface import display_battle_interface
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer

        COMMANDS = {"attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                    "tera": (cmd_battle_tera, cmd_battle_tera.CmdBattleTera),
                    "create": (cmd_pvp, cmd_pvp.CmdPvpCreate), "join": (cmd_pvp, cmd_pvp.CmdPvpJoin),
                    "start": (cmd_pvp, cmd_pvp.CmdPvpStart)}
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TerastallizationCases))
        raise SystemExit(not result.wasSuccessful())
