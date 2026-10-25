"""Held status berries and Synchronize through real owned-player commands."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import incense_cases as transport
import plate_theft_cases as removal

EVIDENCE = transport.EVIDENCE
ITEMS = ("Pecha Berry", "PSN Cure Berry", "Burnt Berry")


class HeldStatusBerryCases(unittest.TestCase):
    """Borrow production nickname, equip, target, persistence and stock checks."""

    fixture_tag = "held-status-858"
    native_family = "unused"
    native_abilities = {**removal.PlateTheftCases.native_abilities,
                        "Venomoth": "Shield Dust", "Tyranitar": "Unnerve"}
    setUp = removal.PlateTheftCases.setUp
    tearDown = removal.PlateTheftCases.tearDown
    capture = removal.PlateTheftCases.capture
    command = removal.PlateTheftCases.command
    snapshot = removal.PlateTheftCases.snapshot
    hold = removal.PlateTheftCases.hold
    saved_item = removal.PlateTheftCases.saved_item
    stop = removal.PlateTheftCases.stop
    items = removal.PlateTheftCases.items
    start = removal.PlateTheftCases.start
    seed = 853

    def rebuild(self):
        """Durable restore must preserve exact major/sleep/toxic condition state."""
        before = [(p.active[0].status or "", p.active[0].toxic_counter,
                   p.active[0].tempvals.get("sleep_turns"), p.active[0].tempvals.get("slp_turns"))
                  for p in self.session.battle.participants]
        removal.PlateTheftCases.rebuild(self)
        after = [(p.active[0].status or "", p.active[0].toxic_counter,
                  p.active[0].tempvals.get("sleep_turns"), p.active[0].tempvals.get("slp_turns"))
                 for p in self.session.battle.participants]
        self.assertEqual(after, before)

    def turn(self, ours, theirs="Safeguard", *, rebuild=False):
        """Run actual commands and retain observation-only move order and effects."""
        before, starts = self.snapshot(), [len(p.messages) for p in self.players]
        battle = self.session.battle
        number = battle.turn_count
        random.seed(self.seed)
        battle.rng = random.Random(self.seed)
        self.command("attack", "A1 " + ours)
        self.assertEqual(battle.turn_count, number)
        if rebuild:
            self.rebuild()
            self.rebuild()
            battle = self.session.battle
            battle.rng = random.Random(self.seed)
        with patch.object(battle, "use_move", wraps=battle.use_move) as observation:
            self.command("attack", "B1 " + theirs, 1)
        self.assertEqual(battle.turn_count, number + 1)
        self.assertFalse(getattr(battle, "_callback_failures", []))
        actions = [str(call.args[0].pokemon.model_id) for call in observation.call_args_list]
        messages = [p.messages[start:] for p, start in zip(self.players, starts)]
        record = {
            "label": "ordinary-player-battle-turn",
            "item": self.item,
            "facet": self.facet,
            "commands": ["+attack A1 " + ours, "+attack B1 " + theirs],
            "seed": self.seed,
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

    def prepare(self, item, facet, move):
        """Grant only labelled sources/stock, then use real capture nickname input."""
        self.item, self.facet, self.idle = item, facet, "Iron Defense"
        self.seed = 3 if move == "Ice Beam" else 853
        source = "Venomoth" if move == "Poison Powder" else "Tyranitar" if facet == "unnerve" else "Mew"
        self.capture(0, "Mew", "Buddy", ["Iron Defense", "Skill Swap"])
        moves = list(dict.fromkeys([move, "Safeguard", "Magic Room", "Embargo"])) if source == "Mew" else (
            [move, "Iron Defense"] if source == "Tyranitar" else [move])
        self.capture(1, source, "Source", moves)
        if facet != "missing":
            self.player.trainer.add_item(item, 2)
        EVIDENCE.append({"label": "separate-fixture-prerequisites", "item": item, "facet": facet,
                         "stock_grant": 0 if facet == "missing" else 2,
                         "controllers": [{"side": index, "character_id": player.id,
                                          "owned_id": str(mon.pk), "trainer_id": mon.trainer_id}
                                         for index, (player, mon) in enumerate(zip(self.players, self.owned))],
                         "source": "Tagged encounter/capture finalization and stock; normal nickname menu",
                         "after": self.snapshot()})

    def check(self, item, facet, move):
        """Run a useful/no-effect status move, then durable reconnect/end/unhold."""
        if facet in {"rollback", "missing"}:
            removal.PlateTheftCases.exercise(self, item, facet, move)
            return
        self.prepare(item, facet, move)
        self.start()
        initial = self.snapshot()
        if facet in {"magicroom", "embargo"}:
            self.turn(self.idle, "Magic Room" if facet == "magicroom" else "Embargo")
            self.rebuild()
            self.assertIsNone(EffectContext.item(self.session.battle.participants[0].active[0]))
        slot = next(s for s in self.owned[1].activemoveslot_set.all()
                    if normalize_name(s.move.name) == normalize_name(move))
        pp = ActiveMoveslot.objects.get(pk=slot.pk).current_pp
        bag = self.snapshot()["bags"]
        record = self.turn(self.idle, move, rebuild=facet == "checkpoint")
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)
        status = {"Toxic": "tox", "Poison Powder": "psn", "Will-O-Wisp": "brn", "Ice Beam": "frz",
                  "Thunder Wave": "par"}.get(move, "")
        useful = status == "frz" if item == "Burnt Berry" else status in {"psn", "tox"}
        prevented = facet in {"magicroom", "embargo", "unnerve"}
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(self.items(), [item if prevented or not useful else "", ""])
        self.assertEqual(holder.status or "", status if prevented or not useful else "")
        if prevented:
            if facet == "magicroom":
                self.turn(self.idle, "Magic Room")
            elif facet == "unnerve":
                self.turn("Skill Swap", "Iron Defense")
            else:
                for _ in range(5):
                    if not getattr(self.session.battle.participants[0].active[0], "volatiles", {}).get("embargo"):
                        break
                    self.turn(self.idle, "Safeguard")
                    self.rebuild()
                self.assertNotIn("embargo", self.session.battle.participants[0].active[0].volatiles)
                # Expiry is a residual boundary; eating resumes on the next
                # ordinary update, before the next poison residual.
                self.turn(self.idle, "Safeguard")
            holder = self.session.battle.participants[0].active[0]
            self.assertEqual(self.items(), ["", ""])
            self.assertFalse(holder.status)
        if useful:
            self.assertEqual(holder.toxic_counter, 0)
        self.assertEqual(self.snapshot()["bags"], bag)
        for _ in range(2):
            self.rebuild()
        runtime = [p.active[0].to_dict() for p in self.session.battle.participants]
        expected = self.items()
        before_end = self.snapshot()
        self.stop()
        self.assertEqual(self.items(), expected)
        self.assertEqual(self.snapshot()["bags"], bag)
        for player in self.players:
            self.assertFalse(player.db.in_battle)
            self.assertFalse(player.db.battle_lock)
        after_end = self.snapshot()
        self.assertEqual(after_end["placements"], initial["placements"])
        mutable = {"held_item", "current_hp", "status", "sleep_turns"}
        stable = lambda rows: [{key: value for key, value in row.items() if key not in mutable} for row in rows]
        self.assertEqual(stable(after_end["owned"]), stable(initial["owned"]))
        EVIDENCE.append({"label": "accepted-held-status", "item": item, "facet": facet,
                         "move": move, "useful": useful, "prevented": prevented,
                         "pp_before": pp, "pp_after": ActiveMoveslot.objects.get(pk=slot.pk).current_pp,
                         "initial": initial, "before_end": before_end,
                         "after_end": after_end, "restored_runtime": runtime,
                         "messages": record["messages"]})
        self.command("hold", "3=")
        self.assertEqual(self.items(), ["", ""])
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1 if useful else 2)
        EVIDENCE.append({"label": "ordinary-postbattle-unhold", "item": item, "facet": facet,
                         "after": self.snapshot()})


def add_case(item, facet, move):
    """Count each real condition/guard independently."""
    def test(self):
        """Verify one normal player command and persisted outcome."""
        self.check(item, facet, move)
    key = "".join(c for c in (item + facet + move).lower() if c.isalnum())
    setattr(HeldStatusBerryCases, "test_" + key, test)


for item in ITEMS:
    for facet in ("rollback", "missing", "healthy"):
        add_case(item, facet, "Safeguard")
    for move in ("Toxic", "Will-O-Wisp", "Thunder Wave"):
        add_case(item, "normal", move)
for item in ITEMS[:2]:
    add_case(item, "normal", "Poison Powder")
    add_case(item, "checkpoint", "Toxic")
    for facet in ("magicroom", "embargo", "unnerve"):
        add_case(item, facet, "Toxic")
add_case("Burnt Berry", "normal", "Ice Beam")
for item in ("Lum Berry", "Miracle Berry"):
    add_case(item, "normal", "Toxic")
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
                unittest.defaultTestLoader.loadTestsFromTestCase(HeldStatusBerryCases))
        finally:
            if os.environ.get("PF2_HELD_STATUS_EVIDENCE"):
                Path(os.environ["PF2_HELD_STATUS_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
