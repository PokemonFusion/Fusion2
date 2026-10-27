"""Normal battle command boundaries over isolated SQL and captured transport."""

import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from ui_cases import PlayerView

EVIDENCE = []


class BattlePlayerView(PlayerView):
    """Keep ordinary owner/inventory lookup on the actual User implementation."""

    def get_pokemon_by_id(self, identifier):
        """Resolve a full ID through the shipped owner-validated lookup."""
        from pokemon.user import User
        return User.get_pokemon_by_id(self, identifier)

    def get_active_pokemon_by_slot(self, slot):
        """Resolve the canonical slot, retaining holes."""
        from pokemon.user import User
        return User.get_active_pokemon_by_slot(self, slot)

    def has_item(self, item, quantity=1):
        """Read normal bag stock."""
        from pokemon.user import User
        return User.has_item(self, item, quantity)

    def remove_item(self, item, quantity=1):
        """Spend only through the normal inventory service."""
        from pokemon.user import User
        return User.remove_item(self, item, quantity)

    def deposit_pokemon(self, identifier, box=1):
        """Move the owned party member through the normal custody service."""
        from pokemon.user import User
        return User.deposit_pokemon(self, identifier, box)

    def _pokemon_is_in_party(self, pokemon):
        """Use the same canonical membership check as ordinary storage commands."""
        from pokemon.user import User
        return User._pokemon_is_in_party(self, pokemon)

    def get_box(self, index=1):
        """Resolve the player's real storage box."""
        from pokemon.user import User
        return User.get_box(self, index)


class BattlePlayerFixture(unittest.TestCase):
    """Use ordinary controllers, real parsers, mechanics and durable checkpoints."""

    def setUp(self):
        """Create separate tagged fixture identities, never existing game characters."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.storage import UserStorage, ensure_boxes
        from pokemon.models.trainer import Trainer

        room = ObjectDB.objects.create(db_key="battle-repair-room-" + uuid4().hex)
        self.room = SimpleNamespace(
            id=room.pk, pk=room.pk, key=room.key, db=room.db, ndb=room.ndb,
            attributes=room.attributes, contents=[], msg_contents=lambda message: None,
        )
        self.players, self.session = [], None
        for side in ("Host", "Guest"):
            character = ObjectDB.objects.create(db_key=side + uuid4().hex)
            character.permissions.add("Player")
            trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
            player = BattlePlayerView(character, trainer, UserStorage.objects.create(user=character))
            ensure_boxes(player.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
        self.room.contents = self.players
        self.patches = [patch(name, self.find) for name in
                        ("pokemon.battle.battleinstance.search_object", "evennia.search_object",
                         "pokemon.battle.watchers.search_object")]
        for item in self.patches:
            item.start()

    def tearDown(self):
        """End only the fixture battle; its enclosing disposable schema owns all rows."""
        try:
            if self.session and self.session.battle_id in (self.room.db.battles or []):
                self.session.end()
        finally:
            for item in reversed(self.patches):
                item.stop()

    def find(self, query):
        """Resolve model-backed transports by the same persistent character ID."""
        return [player for player in self.players if str(player.id) == str(query).lstrip("#")]

    def add(self, side, species, moves, *, ability=None, slot=None, level=50):
        """Label legal native fixture setup separately from normal player actions."""
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.services.placement import PlacementService

        mon = create_owned_pokemon(
            species, self.players[side].trainer, level, nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, active_move_names=moves,
            **({"ability": ability} if ability is not None else {}),
        )
        if slot:
            PlacementService(self.players[side].storage).to_party(mon, slot=slot)
        EVIDENCE.append({"case": self.id(), "label": "separate-native-fixture-setup",
                         "side": side, "species": species, "ability": mon.ability,
                         "moves": moves, "after": self.snapshot()})
        return mon

    def snapshot(self):
        """Read fresh authoritative rows independently from the current checkpoint."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement

        owned = OwnedPokemon.objects.filter(trainer__in=[p.trainer for p in self.players])
        return {
            "owned": list(owned.order_by("pk").values()),
            "placements": list(PokemonPlacement.objects.filter(pokemon__in=owned).order_by("pk").values()),
            "moves": list(ActiveMoveslot.objects.filter(pokemon__in=owned).order_by("pokemon_id", "slot").values()),
            "bags": [list(p.trainer.list_inventory().order_by("pk").values("item_name", "quantity"))
                     for p in self.players],
            "checkpoint": self.session.data.to_dict() if self.session else None,
            "turn": self.session.battle.turn_count if self.session else None,
            "declarations": dict(self.session.state.declare) if self.session else None,
            "callbacks": list(getattr(self.session.battle, "_callback_failures", [])) if self.session else [],
        }

    def command(self, kind, args="", side=0):
        """Drive shipped commands and record exact inputs, messages and SQL resources."""
        from commands.player import cmd_battle_attack, cmd_battle_switch, cmd_pvp, cmd_battle_item
        from commands.player import cmd_party, cmd_fusion, cmd_battle_concede

        commands = {
            "create": (cmd_pvp, cmd_pvp.CmdPvpCreate), "join": (cmd_pvp, cmd_pvp.CmdPvpJoin),
            "start": (cmd_pvp, cmd_pvp.CmdPvpStart),
            "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
            "switch": (cmd_battle_switch, cmd_battle_switch.CmdBattleSwitch),
            "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
            "deposit": (cmd_party, cmd_party.CmdDepositPokemon),
            "fusion": (cmd_fusion, cmd_fusion.CmdTempFuse),
            "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
        }
        module, cls = commands[kind]
        player = self.players[side]
        before, start = self.snapshot(), len(player.messages)
        command = cls()
        command.caller, command.args, command.cmdstring = player, args, command.key
        command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        self.session = self.players[0].ndb.battle_instance or self.session
        EVIDENCE.append({"case": self.id(), "label": "ordinary-player-command", "side": side,
                         "command": command.key + (" " + args if args else ""),
                         "before": before, "after": self.snapshot(), "messages": player.messages[start:]})

    def launch(self, battle_format="single"):
        """Create/join/start through ordinary PvP requests."""
        self.command("create", "double" if battle_format == "double" else "")
        self.command("join", self.players[0].key, 1)
        self.command("start")
        self.assertIsNotNone(self.session, self.players[0].messages)
        self.session.battle.rng = random.Random(915)
        return self.session

    def turn(self, ours, theirs, *, rebuild=False):
        """Resolve a complete legal turn, optionally restoring a pending player input."""
        before = self.session.battle.turn_count
        self.command("attack", ours)
        if rebuild:
            self.rebuild()
        self.command("attack", theirs, 1)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.turn_count, before + 1)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))

    def rebuild(self):
        """Discard the engine and reconstruct its production saved checkpoint."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler

        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session


def run(cases):
    """Run only in an explicit disposable PostgreSQL schema; do not migrate or deploy."""
    from isolated_postgres import IsolatedPostgres
    from ordinary_player_fixtures import OrdinaryPlayerFixtures

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("battle-repair-915-918"):
                result = unittest.TextTestRunner(verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(cases))
    finally:
        if os.environ.get("PF2_BATTLE_REPAIR_EVIDENCE"):
            Path(os.environ["PF2_BATTLE_REPAIR_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
