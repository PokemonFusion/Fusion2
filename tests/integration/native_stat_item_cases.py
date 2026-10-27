"""Ordinary nickname/equip/attack routes for #853 in disposable PostgreSQL."""

import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import incense_cases as transport


EVIDENCE = transport.EVIDENCE
PROFILES = {
    "Light Ball": ("Pikachu", "Quick Attack", "ModifyAtk", "atk", "outgoing"),
    "Thick Club": ("Cubone", "Bone Club", "ModifyAtk", "atk", "outgoing"),
    "Deep Sea Scale": ("Clamperl", "Iron Defense", "ModifySpD", "spd", "incoming"),
    "Deep Sea Tooth": ("Clamperl", "Water Gun", "ModifySpA", "spa", "outgoing"),
    "Metal Powder": ("Ditto", "Transform", "ModifyDef", "def", "incoming"),
    "Quick Powder": ("Ditto", "Transform", "ModifySpe", "spe", "order"),
    "Lucky Punch": ("Chansey", "Pound", "ModifyCritRatio", None, "critical"),
    "Stick": ("Farfetch'd", "Peck", "ModifyCritRatio", None, "critical"),
    "Leek": ("Sirfetch'd", "Peck", "ModifyCritRatio", None, "critical"),
}
IDLE_MOVES = {
    "Pikachu": "Tail Whip",
    "Cubone": "Tail Whip",
    "Clamperl": "Iron Defense",
    "Chansey": "Tail Whip",
    "Farfetch'd": "Swords Dance",
    "Sirfetch'd": "Swords Dance",
}


class NativeStatItemCases(unittest.TestCase):
    """Reuse the accepted command transport, not its incense-specific assertions."""

    command = transport.IncenseCases.command
    snapshot = transport.IncenseCases.snapshot
    hold = transport.IncenseCases.hold
    saved_item = transport.IncenseCases.saved_item
    stop = transport.IncenseCases.stop
    rebuild = transport.IncenseCases.rebuild

    def setUp(self):
        """Create separate ordinary tagged characters and a private battle room."""
        room = ObjectDB.objects.create(db_key="native-item-853-room-" + uuid4().hex)
        self.room = SimpleNamespace(
            id=room.pk,
            pk=room.pk,
            key=room.key,
            db=room.db,
            ndb=room.ndb,
            attributes=room.attributes,
            contents=[],
        )
        self.players, self.owned, self.session = [], [], None
        for _ in range(2):
            character = ObjectDB.objects.create(
                db_key="native-item-853-player-" + uuid4().hex,
                db_typeclass_path="pokemon.user.User",
            )
            character.permissions.add("Player")
            player = transport.IncensePlayer(character, character.trainer, character.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
        self.player = self.players[0]
        self.room.contents = self.players
        self.search = patch(
            "pokemon.battle.battleinstance.search_object",
            lambda query: [p for p in self.players if str(p.id) == str(query).lstrip("#")],
        )
        self.search.start()

    def tearDown(self):
        """Release only the current tagged session and ordinary menu transport."""
        self.stop()
        for player in self.players:
            menu = player.ndb._evmenu
            if menu:
                menu.close_menu()
        self.search.stop()

    def prepare(self, item, *, foreign=False, stock=True):
        """Label native source setup separately from normal nickname/menu input."""
        self.item = item
        native, move, self.event, self.stat, self.kind = PROFILES[item]
        species = "Mew" if foreign else native
        self.attack_move = move
        if foreign and self.kind in {"outgoing", "critical"}:
            self.attack_move = "Swift" if item == "Deep Sea Tooth" else "Pound"
        moves = list(dict.fromkeys([self.attack_move, IDLE_MOVES.get(species, self.attack_move)]))
        encounter = create_encounter_pokemon(
            species=species,
            level=50,
            source_kind="wild",
            nature="Hardy",
            ivs=[0] * 6,
            evs=[0] * 6,
            current_hp=1,
            move_names=moves,
        )
        target = Pokemon(
            species,
            level=50,
            hp=1,
            max_hp=get_max_hp(encounter),
            model_id="encounter:" + str(encounter.pk),
        )
        result = finalize_wild_capture(
            target_poke=target, player=self.player, trainer=self.player.trainer
        )
        caught = OwnedPokemon.objects.get(pk=result.owned_pokemon_id.split(":", 1)[1])
        opponent = create_owned_pokemon(
            "Mew",
            self.players[1].trainer,
            50,
            nature="Calm",
            ability="Synchronize",
            ivs=[0] * 6,
            evs=[252, 0, 0, 0, 252, 0],
            active_move_names=["Safeguard", "Pound", "Swift", "Magic Room"],
        )
        self.owned = [caught, opponent]
        for player, mon in zip(self.players, self.owned):
            PlacementService(player.storage).to_party(mon, slot=3)
        if stock:
            self.player.trainer.add_item(item, 2)
        EVIDENCE.append(
            {
                "label": "separate-fixture-prerequisites",
                "item": item,
                "native": species,
                "foreign_control": foreign,
                "stock_grant": 2 if stock else 0,
                "source": "New tagged encounter plus production capture finalization; not a wild/ball command walkthrough",
                "before_nickname": self.snapshot(),
            }
        )
        before = self.snapshot()
        self.assertTrue(start_capture_nickname(self.player))
        nickname = native if foreign else "Buddy"
        for value in ("yes", nickname):
            command = CmdEvMenuNode()
            command.caller, command.raw_string, command.session = self.player, value, None
            command.func()
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=caught.pk).values_list("nickname", flat=True).get(),
            nickname,
        )
        self.assertEqual(CaptureNicknames(self.player).pending(), [])
        EVIDENCE.append(
            {
                "label": "ordinary-capture-nickname-menu",
                "item": item,
                "inputs": ["yes", nickname],
                "before": before,
                "after": self.snapshot(),
                "messages": list(self.player.messages),
            }
        )

    def start(self, item):
        """Equip by canonical slot and construct a real persistent PvP session."""
        self.stop()
        for index, mon in enumerate(self.owned):
            OwnedPokemon.flush_cached_instance(mon)
            self.owned[index] = OwnedPokemon.objects.get(pk=mon.pk)
            self.owned[index].heal()
        self.hold(item)
        self.session = BattleSession(self.player, self.players[1], rng=random.Random(853))
        self.session.start_pvp()
        self.session.battle.debug = True
        self.assertEqual(
            str(self.session.battle.participants[0].active[0].base_species), self.owned[0].species
        )
        self.assertEqual(self.session.battle.participants[0].active[0].name, self.owned[0].name)

    def turn(self, ours, theirs="Safeguard", *, rebuild=False):
        """Run actual commands and retain observation-only move order and effects."""
        before, starts = self.snapshot(), [len(p.messages) for p in self.players]
        battle = self.session.battle
        number = battle.turn_count
        random.seed(853)
        battle.rng = random.Random(853)
        self.command("attack", "A1 " + ours)
        self.assertEqual(battle.turn_count, number)
        if rebuild:
            self.rebuild()
            self.rebuild()
            battle = self.session.battle
            battle.rng = random.Random(853)
        with patch.object(battle, "use_move", wraps=battle.use_move) as observation:
            self.command("attack", "B1 " + theirs, 1)
        self.assertEqual(battle.turn_count, number + 1)
        self.assertFalse(getattr(battle, "_callback_failures", []))
        actions = [str(call.args[0].pokemon.model_id) for call in observation.call_args_list]
        messages = [p.messages[start:] for p, start in zip(self.players, starts)]
        record = {
            "label": "ordinary-player-battle-turn",
            "item": self.item,
            "commands": ["+attack A1 " + ours, "+attack B1 " + theirs],
            "seed": 853,
            "queued_rebuilds": 2 if rebuild else 0,
            "before": before,
            "after": self.snapshot(),
            "executed_move_order": actions,
            "messages": messages,
            "damage_traces": [
                match.groups()
                for text in messages[0]
                for match in transport.DEBUG.finditer(str(text))
            ],
        }
        EVIDENCE.append(record)
        self.assertEqual(record["before"]["bags"], record["after"]["bags"])
        return record

    def measure(self, held, *, magic=False, queued=False):
        """Measure a useful normal effect without replacing mechanics or RNG rolls."""
        self.start(held)
        if magic:
            self.turn(IDLE_MOVES[self.owned[0].species], "Magic Room")
            self.assertIn("magicroom", self.session.battle.field.pseudo_weather)
        battle = self.session.battle
        holder, opponent = [part.active[0] for part in battle.participants]
        raw = 0 if self.stat is None else holder.stats[self.stat]
        modifier = battle.runEvent(self.event, holder, opponent, None, raw)
        if self.kind == "incoming":
            ours = "Transform" if self.item == "Metal Powder" else "Iron Defense"
            theirs = "Pound" if self.item == "Metal Powder" else "Swift"
            hp_before = holder.hp
        elif self.kind == "order":
            ours, theirs, hp_before = "Transform", "Swift", holder.hp
        else:
            ours, theirs, hp_before = self.attack_move, "Safeguard", opponent.hp
        record = self.turn(ours, theirs, rebuild=queued)
        holder, opponent = [part.active[0] for part in self.session.battle.participants]
        damage = hp_before - (holder.hp if self.kind in {"incoming", "order"} else opponent.hp)
        self.assertGreater(damage, 0)
        for mon in self.owned:
            self.assertFalse(mon.is_egg)
        self.assertEqual(self.saved_item(), held)
        if self.kind == "order":
            self.assertTrue(holder.transformed)
            self.assertEqual(str(holder.base_species), self.owned[0].species)
        if record["damage_traces"]:
            self.assertEqual(len(record["damage_traces"]), 1, record["messages"])
        else:
            self.fail("Missing real damage trace")
        self.stop()
        after = self.snapshot()
        self.assertFalse(self.player.db.in_battle)
        self.assertFalse(self.player.db.battle_lock)
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.owned[0].pk)
            .values_list("held_item", flat=True)
            .get(),
            held,
        )
        EVIDENCE.append({"label": "persisted-battle-end", "item": self.item, "after": after})
        return {
            "raw": raw,
            "modified": modifier,
            "damage": damage,
            "critical": record["damage_traces"][0][7],
            "order": record["executed_move_order"],
        }

    def exercise(self, item, facet):
        """Accept one item's native/foreign/suppression/checkpoint/rollback facet."""
        self.prepare(item, foreign=facet == "foreign", stock=facet != "missing")
        if facet == "rollback":
            before, start = self.snapshot(), len(self.player.messages)
            original = OwnedPokemon.save
            injected = []

            def fail_held(mon, *args, **kwargs):
                """Inject a post-debit save failure only in this tagged hold attempt."""
                if mon.pk == self.owned[0].pk and mon.held_item == item:
                    injected.append(mon.pk)
                    raise RuntimeError("native-item-853 held save fault")
                return original(mon, *args, **kwargs)

            with patch.object(OwnedPokemon, "save", fail_held):
                self.command("hold", "3=" + item)
            self.assertEqual(injected, [self.owned[0].pk])
            self.assertIn(
                "Unable to change held item; Pokemon and inventory were unchanged.",
                self.player.messages[start:],
            )
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(any("is now holding" in str(m) for m in self.player.messages[start:]))
            EVIDENCE.append(
                {
                    "label": "expected-hold-rollback",
                    "item": item,
                    "injected_save_failures": len(injected),
                    "before": before,
                    "after": self.snapshot(),
                    "messages": self.player.messages[start:],
                }
            )
            self.hold(item)
            self.hold("")
            self.assertEqual(self.player.trainer.get_item_quantity(item), 2)
            return
        if facet == "missing":
            before = self.snapshot()
            self.command("hold", "3=" + item)
            self.assertEqual(self.snapshot(), before)
            return
        baseline = self.measure("", magic=facet == "magic")
        held = self.measure(item, magic=facet == "magic", queued=facet == "checkpoint")
        expected = (
            baseline["raw"]
            if facet in {"foreign", "magic"}
            else (2 if self.stat is None else baseline["raw"] * 2)
        )
        self.assertEqual(held["modified"], expected)
        if facet in {"foreign", "magic"}:
            self.assertEqual(baseline["damage"], held["damage"])
        elif self.kind == "incoming":
            self.assertLess(held["damage"], baseline["damage"])
        elif self.kind == "order":
            identifier = "owned:" + str(self.owned[0].pk)
            self.assertNotEqual(baseline["order"][0], identifier)
            self.assertEqual(held["order"][0], identifier)
        elif self.kind == "outgoing":
            self.assertGreater(held["damage"], baseline["damage"])
        else:
            self.assertEqual(baseline["critical"], "False")
            self.assertEqual(held["critical"], "True")
            self.assertGreater(held["damage"], baseline["damage"])
        EVIDENCE.append(
            {
                "label": "matched-item-outcome",
                "item": item,
                "facet": facet,
                "baseline": baseline,
                "held": held,
            }
        )


def add_case(item, facet):
    """Give each exact item/facet its own independently counted regression."""

    def test(self):
        """Use the ordinary player route for this item and facet."""
        self.exercise(item, facet)

    setattr(NativeStatItemCases, "test_" + transport.key(item) + "_" + facet, test)


for item in PROFILES:
    for facet in ("native", "foreign", "checkpoint", "rollback", "missing", "magic"):
        if facet == "magic" and PROFILES[item][0] == "Ditto":
            continue  # A normal Ditto cannot idle; unit coverage isolates suppression.
        add_case(item, facet)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_party, cmd_inventory, cmd_pokedex
        from evennia.objects.models import ObjectDB
        from evennia.utils.evmenu import CmdEvMenuNode
        from menus.capture_nickname import start_capture_nickname
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.dex import ITEMDEX
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import resolve_dex_entry
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.capture_nicknames import CaptureNicknames
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        COMMANDS = {
            "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
            "hold": (cmd_party, cmd_party.CmdSetHoldItem),
            "inventory": (cmd_inventory, cmd_inventory.CmdInventory),
            "itemdex": (cmd_pokedex, cmd_pokedex.CmdItemdexSearch),
        }
        for name in (
            "ObjectDB",
            "BattleSession",
            "battle_handler",
            "ITEMDEX",
            "OwnedPokemon",
            "ActiveMoveslot",
            "PokemonPlacement",
            "PlacementService",
            "User",
            "COMMANDS",
            "resolve_dex_entry",
        ):
            setattr(transport, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeStatItemCases)
            )
        finally:
            if os.environ.get("PF2_NATIVE_ITEM_EVIDENCE"):
                Path(os.environ["PF2_NATIVE_ITEM_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
