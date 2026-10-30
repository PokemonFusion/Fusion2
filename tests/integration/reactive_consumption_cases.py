"""Six reactive consumables through ordinary commands and isolated owned SQL."""

import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE
from isolated_postgres import IsolatedPostgres

ITEMS = ("Jaboca Berry", "Rowap Berry", "Kee Berry", "Maranga Berry",
         "Weakness Policy", "Throat Spray")
BERRIES = ITEMS[:4]


class ReactiveConsumptionCases(BattlePlayerFixture):
    """Separate labelled setup/fault injection from real ordinary-player inputs."""

    def snapshot(self):
        """Keep independent SQL resources and named histories, not full graphs."""
        from pokemon.battle.item_consumption import ItemUseHistory

        full = super().snapshot()
        fields = {"id", "species", "nickname", "trainer_id", "held_item", "current_hp",
                  "status", "ability", "level", "ivs", "evs", "nature", "is_egg"}
        full["owned"] = [{key: value for key, value in row.items() if key in fields}
                         for row in full["owned"]]
        full["checkpoint_sha256"] = hashlib.sha256(
            json.dumps(full.pop("checkpoint"), sort_keys=True, default=str).encode("utf-8")).hexdigest()
        full["histories"] = ([ItemUseHistory.freeze(mon) for part in self.session.battle.participants
                              for mon in part.active] if self.session else [])
        full["used_items"] = ItemUseHistory.freeze_sides(self.session.battle) if self.session else {}
        return full

    def command(self, kind, args="", side=0):
        """Use shipped inventory, party and held-item parsers alongside PvP inputs."""
        if kind not in {"hold", "party", "inventory"}:
            return super().command(kind, args, side)
        from commands.player.cmd_party import CmdSetHoldItem
        from commands.player.cmd_sheet import CmdSheetPokemon
        from commands.player.cmd_inventory import CmdInventory

        cls = {"hold": CmdSetHoldItem, "party": CmdSheetPokemon, "inventory": CmdInventory}[kind]
        player = self.players[side]
        before, start = self.snapshot(), len(player.messages)
        command = cls()
        command.caller, command.args, command.cmdstring = player, args, command.key
        command.parse()
        command.func()
        EVIDENCE.append({"case": self.id(), "label": "ordinary-player-command", "side": side,
                         "command": command.key + (" " + args if args else ""),
                         "before": before, "after": self.snapshot(), "messages": player.messages[start:]})

    def prepare(self, item, mode, second_item=None):
        """Label native, known-move and stock prerequisites; no public-source claim."""
        from pokemon.models.core import OwnedPokemon

        self.item, self.mode = item, mode
        physical = item in {"Jaboca Berry", "Kee Berry", "Weakness Policy"}
        source = "Swoobat" if mode == "klutz" else "Houndoom" if "unnerve" in mode else "Mew"
        ability = "Klutz" if mode == "klutz" else "Unnerve" if "unnerve" in mode else "Synchronize"
        self.move = ("Screech" if item == "Throat Spray" else
                     "Assurance" if mode == "klutz" and physical else
                     "Air Cutter" if mode == "klutz" else
                     "Payback" if source == "Houndoom" and physical else
                     "Swift" if source == "Houndoom" else
                     "Payback" if item == "Weakness Policy" else
                     "Aerial Ace" if physical else "Water Gun")
        self.mon = self.add(0, "Mew", ["Amnesia", "Recycle", "Gastro Acid", "Screech"],
                            slot=3, ability="Synchronize")
        extra = {"klutz": "Skill Swap", "magicroom": "Magic Room", "embargo": "Embargo",
                 "mixed": "Trick"}.get(mode, "Embargo")
        moves = list(dict.fromkeys(([self.move] if item != "Throat Spray" else [])
                                  + ["Rain Dance", "Thief", extra]))
        self.foe = self.add(1, source, moves, slot=3, ability=ability)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nickname="Buddy", nature="Bold", ivs=[31] * 6, evs=[252, 0, 252, 0, 0, 0])
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon.refresh_from_db()
        self.mon.heal()
        self.players[0].trainer.add_item(item, 2)
        if second_item:
            self.players[1].trainer.add_item(second_item, 2)
        EVIDENCE.append({"case": self.id(), "label": "separate-tagged-prerequisites",
                         "item": item, "mode": mode, "known_moves": moves, "second_item": second_item,
                         "limit": "Native rows, legal known-move slots, nickname and stock setup; no purchase/hunt/socket claim",
                         "after": self.snapshot()})
        self.command("inventory")
        self.command("party", "3")
        self.command("hold", "3=" + item)
        if second_item:
            self.command("hold", "3=" + second_item, 1)
        self.assertEqual(self.items(), [item, second_item or ""])
        self.launch()

    def items(self):
        """Read authoritative physical holding independently from runtime caches."""
        from pokemon.models.core import OwnedPokemon
        return [OwnedPokemon.objects.values_list("held_item", flat=True).get(pk=mon.pk)
                for mon in (self.mon, self.foe)]

    def resources(self):
        """Compare durable resources and recoverable runtime history after faults."""
        snapshot = self.snapshot()
        return {key: snapshot[key] for key in
                ("owned", "placements", "moves", "bags", "histories", "used_items")}

    def history(self, consumed):
        """Rebuild twice without replaying a use, PP debit or recovery grant."""
        from pokemon.names import normalize_name

        snapshot = self.resources()
        for _ in range(2):
            self.rebuild()
            self.assertEqual(self.resources(), snapshot)
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(normalize_name(getattr(holder.last_used_item, "name", "")),
                         normalize_name(self.item) if consumed else "")
        self.assertEqual(len(holder.side.used_items), int(consumed))

    def trigger(self, *, rebuild=True):
        """Pay for a real category/super-effective hit or a genuine sound move."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.names import normalize_name

        mon = self.mon if self.item == "Throat Spray" else self.foe
        slot = next(slot for slot in ActiveMoveslot.objects.filter(pokemon=mon).select_related("move")
                    if normalize_name(slot.move.name) == normalize_name(self.move))
        pp = slot.current_pp
        self.turn(self.move + " B1" if self.item == "Throat Spray" else "Amnesia",
                  "Rain Dance" if self.item == "Throat Spray" else self.move + " A1", rebuild=rebuild)
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)

    def finish(self, expected_counts):
        """Ordinary end/inspection/unhold returns each physical copy only once."""
        bags, expected = self.snapshot()["bags"], self.items()
        self.session.end()
        self.session = None
        self.assertEqual(self.items(), expected)
        self.assertEqual(self.snapshot()["bags"], bags)
        for side in (0, 1):
            self.command("party", "3", side)
            self.command("hold", "3=", side)
        self.assertEqual(self.items(), ["", ""])
        self.assertEqual([player.trainer.get_item_quantity(self.item) for player in self.players], expected_counts)
        EVIDENCE.append({"case": self.id(), "label": "accepted-postbattle-conservation",
                         "item": self.item, "mode": self.mode, "expected_bags": expected_counts,
                         "after": self.snapshot()})

    def exercise(self, item, mode):
        """Use the same owned-flow checks for useful, blocked and failed-write routes."""
        self.prepare(item, mode)
        if mode in {"magicroom", "embargo", "klutz", "suppressedunnerve"}:
            ours = "Gastro Acid B1" if mode == "suppressedunnerve" else "Amnesia"
            theirs = {"magicroom": "Magic Room", "embargo": "Embargo A1",
                      "klutz": "Skill Swap A1", "suppressedunnerve": "Rain Dance"}[mode]
            self.turn(ours, theirs)
            self.rebuild()
        bags = self.snapshot()["bags"]
        self.trigger()
        blocked = mode in {"magicroom", "embargo", "klutz", "unnerve"}
        self.assertEqual(self.items(), [item if blocked else "", ""])
        self.assertEqual(self.snapshot()["bags"], bags)
        self.history(not blocked)
        EVIDENCE.append({"case": self.id(), "label": "accepted-reactive-outcome",
                         "item": item, "mode": mode, "blocked": blocked, "after": self.snapshot()})
        if blocked:
            self.turn("Recycle", "Rain Dance", rebuild=True)
            self.assertEqual(self.items(), [item, ""])
            self.finish([2, 0])
            return
        if mode == "spent":
            self.finish([1, 0])
            return
        self.turn("Recycle", "Rain Dance", rebuild=True)
        self.assertEqual(self.items(), [item, ""])
        self.assertIsNone(self.session.battle.participants[0].active[0].last_used_item)
        self.assertEqual(self.session.battle.participants[0].active[0].side.used_items, [])
        if item in BERRIES:
            self.assertTrue(self.session.battle.participants[0].active[0].ate_berry)
        before = self.resources()
        self.rebuild()
        self.assertEqual(self.resources(), before)
        # Embargo preserves the recovered physical copy for actual Thief.
        self.turn("Amnesia", "Embargo A1")
        self.turn("Amnesia", "Thief A1", rebuild=True)
        self.assertEqual(self.items(), ["", item])
        self.turn("Recycle", "Rain Dance", rebuild=True)
        self.assertEqual(self.items(), ["", item])
        before = self.resources()
        self.rebuild()
        self.assertEqual(self.resources(), before)
        EVIDENCE.append({"case": self.id(), "label": "accepted-recovery-without-duplicate",
                         "item": item, "mode": mode, "after": self.snapshot()})
        self.finish([1, 1])

    def rollback(self, item):
        """Fail after real SQL item/HP/PP sync, then retry the saved legal inputs."""
        self.prepare(item, "rollback")
        before = self.resources()
        original, faults = self.session.storage.set, []

        def refuse(key, value):
            """Inject only after this exact fixture's used item reaches SQL."""
            if key == "data" and not self.items()[0]:
                faults.append(self.snapshot())
                raise RuntimeError("reactive-921 isolated checkpoint refusal")
            return original(key, value)

        self.command("attack", "Screech B1" if item == "Throat Spray" else "Amnesia")
        with patch.object(self.session.storage, "set", side_effect=refuse):
            try:
                self.command("attack", "Rain Dance" if item == "Throat Spray" else self.move + " A1", 1)
            except RuntimeError as error:
                self.assertIn("reactive-921 isolated checkpoint refusal", str(error))
        self.assertEqual(len(faults), 1)
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.items(), [item, ""])
        self.session.execute_persistent_turn()
        self.assertEqual(self.items(), ["", ""])
        self.history(True)
        EVIDENCE.append({"case": self.id(), "label": "accepted-isolated-consumption-rollback",
                         "item": item, "fault_state": faults[0], "after": self.snapshot()})
        self.finish([1, 0])

    def mixed(self, berry, second_item):
        """Receive a second real held copy with Trick, use it and recover only it."""
        from pokemon.names import normalize_name

        self.prepare(berry, "mixed", second_item)
        bags = self.snapshot()["bags"]
        self.trigger()
        self.assertEqual(self.items(), ["", second_item])
        self.history(True)
        self.turn("Amnesia", "Trick A1", rebuild=True)
        self.assertEqual(self.items(), [second_item, ""])
        self.turn("Screech B1" if second_item == "Throat Spray" else "Amnesia",
                  "Rain Dance" if second_item == "Throat Spray" else "Thief A1", rebuild=True)
        self.assertEqual(self.items(), ["", ""])
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(normalize_name(holder.last_used_item.name), normalize_name(second_item))
        self.assertIsNone(holder.consumed_berry)
        self.assertIsNone(holder.berry_consumed)
        self.assertTrue(holder.ate_berry)
        self.assertEqual(len(holder.side.used_items), 2)
        before = self.resources()
        for _ in range(2):
            self.rebuild()
            self.assertEqual(self.resources(), before)
        self.turn("Recycle", "Rain Dance", rebuild=True)
        self.assertEqual(self.items(), [second_item, ""])
        self.assertEqual(self.snapshot()["bags"], bags)
        EVIDENCE.append({"case": self.id(), "label": "accepted-mixed-use-recovery",
                         "berry": berry, "second_item": second_item, "after": self.snapshot()})
        self.finish([1, 0])
        self.assertEqual([player.trainer.get_item_quantity(second_item) for player in self.players], [1, 1])

    def test_mixed_kee_then_weakness_policy(self):
        """Ordinary Trick and a super-effective Thief supersede Kee recovery."""
        self.mixed("Kee Berry", "Weakness Policy")

    def test_mixed_maranga_then_throat_spray(self):
        """Ordinary Trick and Screech supersede Maranga recovery."""
        self.mixed("Maranga Berry", "Throat Spray")


def add_case(item, mode):
    """Expose every exact item/control as an independently counted SQL case."""
    def test(self):
        """Execute ordinary inputs and compare independent owned SQL/resources."""
        self.rollback(item) if mode == "rollback" else self.exercise(item, mode)
    key = "".join(character for character in (item + mode).lower() if character.isalnum())
    setattr(ReactiveConsumptionCases, "test_" + key, test)


for item in ITEMS:
    for mode in ("normal", "spent", "magicroom", "embargo", "klutz", "rollback"):
        add_case(item, mode)
for item in BERRIES:
    for mode in ("unnerve", "suppressedunnerve"):
        add_case(item, mode)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("reactive-consumption-921"):
                result = unittest.TextTestRunner(verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(ReactiveConsumptionCases))
    finally:
        if os.environ.get("PF2_REACTIVE_CONSUMPTION_EVIDENCE"):
            Path(os.environ["PF2_REACTIVE_CONSUMPTION_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
