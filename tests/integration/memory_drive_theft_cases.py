"""Reuse the owned-player removal harness for all 21 Memories and Drives."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import incense_cases as transport
import plate_theft_cases as removal


EVIDENCE = transport.EVIDENCE
MEMORIES = tuple(kind + " Memory" for kind in (
    "Bug", "Dark", "Dragon", "Electric", "Fairy", "Fighting", "Fire", "Flying",
    "Ghost", "Grass", "Ground", "Ice", "Poison", "Psychic", "Rock", "Steel", "Water",
))
DRIVES = ("Burn Drive", "Chill Drive", "Douse Drive", "Shock Drive")


class MemoryDriveTheftCases(unittest.TestCase):
    """Keep real commands, identity, PP, conservation and checkpoint assertions."""

    fixture_tag = "memory-drive-856"
    native_abilities = {**removal.PlateTheftCases.native_abilities,
                        "Silvally": "RKS System", "Genesect": "Download"}
    setUp = removal.PlateTheftCases.setUp
    tearDown = removal.PlateTheftCases.tearDown
    capture = removal.PlateTheftCases.capture
    start = removal.PlateTheftCases.start
    items = removal.PlateTheftCases.items
    command = removal.PlateTheftCases.command
    snapshot = removal.PlateTheftCases.snapshot
    hold = removal.PlateTheftCases.hold
    saved_item = removal.PlateTheftCases.saved_item
    stop = removal.PlateTheftCases.stop
    rebuild = removal.PlateTheftCases.rebuild
    turn = removal.PlateTheftCases.turn
    exercise = removal.PlateTheftCases.exercise

    def prepare(self, item, facet, move):
        """Create legal native holders and foreign sources with labelled stock."""
        self.item, self.facet = item, facet
        self.native_family = "Silvally" if item in MEMORIES else "Genesect"
        native_holder = facet.startswith("native") or facet.endswith("_native")
        holder = self.native_family if native_holder else "Gastrodon" if facet == "sticky" else "Mew"
        source = "Hypno" if move == "Switcheroo" else "Mew"
        nickname = None if facet.endswith("default") else (
            self.native_family if facet in {"foreign", "magic_foreign", "embargo_foreign", "checkpoint_foreign", "sticky"}
            else self.native_family + "-Imposter" if facet == "prefix" else "Buddy"
        )
        self.idle = "Iron Defense" if native_holder else "Rain Dance" if holder == "Gastrodon" else "Safeguard"
        signature = "Multi-Attack" if self.native_family == "Silvally" else "Techno Blast"
        self.capture(0, holder, nickname, [self.idle, signature] if native_holder else [self.idle, "Surf"])
        self.capture(1, source, self.native_family if facet == "source_foreign" else "Buddy",
                     [move, "Magic Room", "Embargo", "Safeguard"] if source == "Mew"
                     else [move, "Magic Room", "Safeguard"])
        if facet != "missing":
            self.player.trainer.add_item(item, 2)
        if facet in {"occupied", "swap", "native_swap"}:
            self.players[1].trainer.add_item("Shed Shell", 2)
        EVIDENCE.append({
            "label": "separate-fixture-prerequisites", "item": item, "facet": facet,
            "native_family": self.native_family,
            "source": "Tagged encounter and production capture finalization; not wild/ball commands",
            "stock_grant": 0 if facet == "missing" else 2,
            "source_item_grant": 2 if facet in {"occupied", "swap", "native_swap"} else 0,
            "after": self.snapshot(),
        })

    def typed_move(self, item):
        """Use the native signature through +attack, then restore and persist it."""
        self.prepare(item, "type_native", "Thief")
        self.start()
        move = "Multi-Attack" if item in MEMORIES else "Techno Blast"
        expected = resolve_dex_entry(ITEMDEX, item).raw["onMemory" if item in MEMORIES else "onDrive"]
        slot = next(s for s in self.owned[0].activemoveslot_set.all()
                    if normalize_name(s.move.name) == normalize_name(move))
        pp = ActiveMoveslot.objects.get(pk=slot.pk).current_pp
        battle = self.session.battle
        hp = battle.participants[1].active[0].hp
        with patch.object(battle, "use_move", wraps=battle.use_move) as observation:
            receipt = self.turn(move)
        action = next(call.args[0] for call in observation.call_args_list
                      if call.args[0].pokemon.model_id == "owned:" + str(self.owned[0].pk))
        self.assertEqual(action.move.type, expected)
        damage = hp - self.session.battle.participants[1].active[0].hp
        self.assertGreater(damage, 0)
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)
        before = self.snapshot()
        self.rebuild()
        self.rebuild()
        self.assertEqual(self.items(), [item, ""])
        self.assertEqual(self.snapshot()["bags"], before["bags"])
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(str(holder.base_species), self.native_family)
        self.assertEqual(str(holder.species), resolve_dex_entry(ITEMDEX, item).raw["forcedForme"])
        runtime = [part.active[0].to_dict() for part in self.session.battle.participants]
        self.stop()
        self.assertEqual(self.items(), [item, ""])
        for player in self.players:
            self.assertFalse(player.db.in_battle)
            self.assertFalse(player.db.battle_lock)
        EVIDENCE.append({"label": "accepted-native-typed-move", "item": item, "facet": "type_native",
                         "move": move, "type": action.move.type, "damage": damage,
                         "pp_before": pp, "pp_after": ActiveMoveslot.objects.get(pk=slot.pk).current_pp,
                         "runtime": runtime, "after_end": self.snapshot(), "messages": receipt["messages"]})
        self.command("hold", "3=")
        self.assertEqual(self.items(), ["", ""])
        self.assertEqual(self.player.trainer.get_item_quantity(item), 2)


def add_case(item, facet, move="Thief"):
    """Count each exact item and acceptance facet independently."""
    def test(self):
        """Exercise the production player flow and its persisted state."""
        self.typed_move(item) if facet == "type_native" else self.exercise(item, facet, move)
    key = "".join(c for c in (item + facet + move).lower() if c.isalnum())
    setattr(MemoryDriveTheftCases, "test_" + key, test)


for item in MEMORIES + DRIVES:
    for facet in ("foreign_default", "foreign", "prefix", "native_default", "native",
                  "source_foreign", "checkpoint_foreign", "rollback", "missing", "type_native"):
        add_case(item, facet)
for item in ("Fire Memory", "Burn Drive"):
    for move in ("Knock Off", "Trick", "Switcheroo"):
        for facet in ("foreign", "native", "swap", "native_swap"):
            add_case(item, facet, move)
    for move in ("Thief", "Knock Off", "Trick", "Switcheroo"):
        for facet in ("magic_foreign", "magic_native"):
            add_case(item, facet, move)
    for facet in ("embargo_foreign", "embargo_native", "occupied", "sticky"):
        add_case(item, facet)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_party
        from evennia.objects.models import ObjectDB
        from evennia.utils.evmenu import CmdEvMenuNode
        from menus.capture_nickname import start_capture_nickname
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.effect_context import EffectContext
        from pokemon.battle.handler import battle_handler
        from pokemon.dex import ITEMDEX
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import normalize_name, resolve_dex_entry
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.capture_nicknames import CaptureNicknames
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        COMMANDS = {"attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                    "hold": (cmd_party, cmd_party.CmdSetHoldItem)}
        for module in (transport, removal):
            for name in ("ObjectDB", "BattleSession", "battle_handler", "ITEMDEX", "OwnedPokemon",
                         "ActiveMoveslot", "PokemonPlacement", "PlacementService", "User",
                         "COMMANDS", "resolve_dex_entry", "CmdEvMenuNode", "start_capture_nickname",
                         "CaptureNicknames", "create_encounter_pokemon", "Pokemon", "get_max_hp",
                         "finalize_wild_capture", "EffectContext", "normalize_name"):
                setattr(module, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(MemoryDriveTheftCases))
        finally:
            if os.environ.get("PF2_MEMORY_DRIVE_EVIDENCE"):
                Path(os.environ["PF2_MEMORY_DRIVE_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
