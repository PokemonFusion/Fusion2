"""Ordinary Mega Stone removal commands over disposable owned SQL fixtures."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE
from isolated_postgres import IsolatedPostgres


class MegaStoneTheftCases(BattlePlayerFixture):
    """Keep native/nickname setup separate from actual equip and battle inputs."""

    def command(self, kind, args="", side=0):
        """Add shipped field/inspection/Mega commands to the ordinary PvP fixture."""
        if kind not in {"hold", "party", "inventory", "mega"}:
            return super().command(kind, args, side)
        from commands.player.cmd_party import CmdSetHoldItem
        from commands.player.cmd_sheet import CmdSheetPokemon
        from commands.player.cmd_inventory import CmdInventory
        from commands.player.cmd_battle_mega import CmdBattleMega

        cls = {"hold": CmdSetHoldItem, "party": CmdSheetPokemon,
               "inventory": CmdInventory, "mega": CmdBattleMega}[kind]
        player = self.players[side]
        before, start = self.snapshot(), len(player.messages)
        command = cls()
        command.caller, command.args, command.cmdstring = player, args, command.key
        command.parse()
        command.func()
        EVIDENCE.append({"case": self.id(), "label": "ordinary-player-command",
                         "side": side, "command": command.key + (" " + args if args else ""),
                         "before": before, "after": self.snapshot(),
                         "messages": player.messages[start:]})

    def prepare(self, *, eligible=True, move="Thief", stone="Blastoisinite",
                native="Blastoise", source=None, suppression=None,
                holder_name=None, source_name="Friend", holder_species=None,
                holder_ability=None):
        """Label native/move/nickname/stock prerequisites, never public acquisition."""
        from pokemon.models.core import OwnedPokemon

        self.stone, self.move = stone, move
        self.eligible = eligible
        species = holder_species or (native if eligible else "Mew")
        self.idle = "Safeguard" if species == "Mew" else "Rain Dance"
        self.mon = self.add(0, species, [self.idle, "Transform"] if species == "Mew"
                            else [self.idle, "Water Gun"], slot=3, ability=holder_ability)
        source = source or ("Swoobat" if suppression == "klutz"
                            else "Hypno" if move == "Switcheroo" else "Mew")
        source_moves = [move, "Calm Mind"]
        if suppression:
            source_moves.append({"magicroom": "Magic Room", "embargo": "Embargo",
                                 "klutz": "Skill Swap"}[suppression])
        self.thief = self.add(1, source, source_moves, slot=3,
                              ability="Klutz" if suppression == "klutz" else None)
        for mon, nickname in ((self.mon, holder_name or ("Buddy" if eligible else native)),
                              (self.thief, source_name)):
            OwnedPokemon.objects.filter(pk=mon.pk).update(
                nickname=nickname, nature="Bold", ivs=[31] * 6,
                evs=[252, 0, 252, 0, 0, 0])
            OwnedPokemon.flush_cached_instance(mon)
            mon.refresh_from_db()
            mon.heal()
        self.players[0].trainer.add_item(stone, 2)
        self.swap = move in {"Trick", "Switcheroo"}
        self.occupied = False
        if self.swap:
            self.players[1].trainer.add_item("Shed Shell", 2)
        EVIDENCE.append({"case": self.id(), "label": "separate-tagged-prerequisites",
                         "limit": "Native owned rows, legal moves, nickname and bag setup; no hunt, purchase or socket claim",
                         "stone": stone, "eligible_holder": eligible,
                         "after": self.snapshot()})
        self.command("inventory")
        self.command("party", "3")

    def items(self):
        """Read independent current owned fields, not cached model properties."""
        from pokemon.models.core import OwnedPokemon

        return [OwnedPokemon.objects.values_list("held_item", flat=True).get(pk=mon.pk)
                for mon in (self.mon, self.thief)]

    def resources(self):
        """Compare durable HP/status/items/PP and bags across engine rebuilds."""
        snapshot = self.snapshot()
        return {key: snapshot[key] for key in ("owned", "placements", "moves", "bags")}

    def equipped(self):
        """Equip real bag copies before ordinary create/join/start commands."""
        self.command("hold", "3=" + self.stone)
        if self.swap:
            self.command("hold", "3=Shed Shell", 1)
        self.assertEqual(self.items(), [self.stone, "Shed Shell" if self.swap or self.occupied else ""])
        self.launch()

    def outcome(self, expected, *, mega=False):
        """Check one real move debit, effects, repeated rebuilds, end and unhold."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.names import normalize_name

        slot = next(slot for slot in ActiveMoveslot.objects.filter(pokemon=self.thief).select_related("move")
                    if normalize_name(slot.move.name) == normalize_name(self.move))
        before_pp = slot.current_pp
        before_hp = self.session.battle.participants[0].active[0].hp
        before_bags = self.snapshot()["bags"]
        if mega:
            self.command("mega")
        self.turn(self.idle, self.move + " A1", rebuild=True)
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, before_pp - 1)
        self.assertEqual(self.items(), expected)
        self.assertEqual(self.snapshot()["bags"], before_bags)
        damage = before_hp - self.session.battle.participants[0].active[0].hp
        if self.move in {"Thief", "Knock Off"}:
            self.assertGreater(damage, 0)
            self.assertGreater(self.session.battle.participants[0].active[0].hp, 0)
        if mega:
            self.assertEqual(str(self.session.battle.participants[0].active[0].species), "Blastoise-Mega")
            self.assertEqual(self.session.battle.mega_used, {"A"})
        before = self.resources()
        self.rebuild()
        self.rebuild()
        self.assertEqual(self.resources(), before)
        self.assertEqual(self.items(), expected)
        EVIDENCE.append({"case": self.id(), "label": "accepted-removal-outcome",
                         "stone": self.stone, "move": self.move, "held_after": expected,
                         "damage": damage, "pp_before": before_pp, "pp_after": before_pp - 1,
                         "pending_rebuilds": 1, "completed_rebuilds": 2,
                         "after": self.snapshot()})
        self.session.end()
        self.session = None
        self.assertEqual(self.items(), expected)
        self.command("party", "3")
        for side in (0, 1):
            self.command("hold", "3=", side)
        self.assertEqual(self.items(), ["", ""])
        counts = [player.trainer.get_item_quantity(self.stone) for player in self.players]
        self.assertEqual(counts, [2, 0] if expected[0] == self.stone else
                         [1, 0] if self.move == "Knock Off" else [1, 1])
        if self.swap or self.occupied:
            self.assertEqual(sum(player.trainer.get_item_quantity("Shed Shell")
                                 for player in self.players), 2)
        EVIDENCE.append({"case": self.id(), "label": "accepted-postbattle-conservation",
                         "stone_bag_counts": counts, "after": self.snapshot()})

    def removal(self, move, eligible, suppression=None):
        """Normal equip, legal suppression move if requested, then removal attempt."""
        from pokemon.battle.effect_context import EffectContext

        self.prepare(move=move, eligible=eligible, suppression=suppression)
        self.equipped()
        if suppression:
            self.turn(self.idle, {"magicroom": "Magic Room", "embargo": "Embargo A1",
                                  "klutz": "Skill Swap A1"}[suppression])
            self.rebuild()
            self.assertIsNone(EffectContext.item(self.session.battle.participants[0].active[0]))
        expected = [self.stone, "Shed Shell" if self.swap else ""] if eligible else (
            ["", ""] if move == "Knock Off" else ["Shed Shell" if self.swap else "", self.stone])
        self.outcome(expected)

    def test_compatible_thief_does_not_protect_foreign_holder(self):
        """Native Sableye can steal Sablenite from a real foreign Mew holder."""
        self.prepare(eligible=False, stone="Sablenite", native="Sableye", source="Sableye",
                     holder_name="Buddy", source_name="Sableye")
        self.equipped()
        self.outcome(["", "Sablenite"])

    def test_source_nickname_cannot_protect_foreign_holder(self):
        """Mew named Blastoise cannot protect Buddy's Blastoisinite."""
        self.prepare(eligible=False, holder_name="Buddy", source_name="Blastoise")
        self.equipped()
        self.outcome(["", "Blastoisinite"])

    def test_actual_mega_activation_remains_protected_and_reversible(self):
        """+mega and its real bound attack retain the renamed native's stone."""
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        self.equipped()
        self.outcome(["Blastoisinite", ""], mega=True)
        self.assertEqual(OwnedPokemon.objects.values_list("species", flat=True).get(pk=self.mon.pk), "Blastoise")

    def test_actual_transform_cannot_grant_native_protection(self):
        """A genuine Mew copy of Sableye still loses Sablenite to the native."""
        self.prepare(eligible=False, stone="Sablenite", native="Sableye", source="Sableye")
        self.equipped()
        self.turn("Transform B1", "Calm Mind")
        holder = self.session.battle.participants[0].active[0]
        self.assertTrue(holder.transformed)
        self.assertEqual((str(holder.base_species), str(holder.species)), ("Mew", "Sableye"))
        self.idle = "Calm Mind"
        self.outcome(["", "Sablenite"])

    def test_sticky_hold_retains_generic_protection(self):
        """A non-native native-Sticky-Hold source keeps the equipped stone."""
        self.prepare(eligible=False, holder_name="Blastoise", holder_species="Gastrodon",
                     holder_ability="Sticky Hold")
        self.equipped()
        self.outcome(["Blastoisinite", ""])

    def test_occupied_thief_cannot_receive_a_second_item(self):
        """Ordinary held occupancy still prevents Thief on a foreign holder."""
        self.prepare(eligible=False)
        self.occupied = True
        self.players[1].trainer.add_item("Shed Shell", 2)
        self.command("hold", "3=Shed Shell", 1)
        self.equipped()
        self.outcome(["Blastoisinite", "Shed Shell"])

    def test_failed_equip_rolls_back_bag_and_holder(self):
        """A deliberate isolated post-debit save failure grants no held copy."""
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        before = self.resources()
        original, failed = OwnedPokemon.save, []

        def refuse(mon, *args, **kwargs):
            """Inject only after this fixture's actual held write is attempted."""
            if mon.pk == self.mon.pk and mon.held_item == self.stone:
                failed.append(str(mon.pk))
                raise RuntimeError("mega-920 isolated held-save refusal")
            return original(mon, *args, **kwargs)

        with patch.object(OwnedPokemon, "save", refuse):
            self.command("hold", "3=" + self.stone)
        self.assertEqual(failed, [str(self.mon.pk)])
        self.assertEqual(self.resources(), before)
        EVIDENCE.append({"case": self.id(), "label": "accepted-isolated-equip-rollback",
                         "after": self.snapshot()})


def add_removal_case(move, eligible, suppression=None):
    """Count each exact route/control independently in the persistent matrix."""
    def test(self):
        """Exercise genuine ordinary-player commands and fresh SQL assertions."""
        self.removal(move, eligible, suppression)
    name = "test_" + "_".join((move.replace(" ", "").lower(),
                               "native" if eligible else "foreign", suppression or "ordinary"))
    setattr(MegaStoneTheftCases, name, test)


for removal_move in ("Thief", "Knock Off", "Trick", "Switcheroo"):
    for native_holder in (False, True):
        add_removal_case(removal_move, native_holder)
for suppression_kind in ("magicroom", "embargo", "klutz"):
    for native_holder in (False, True):
        add_removal_case("Trick", native_holder, suppression_kind)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("mega-theft-920"):
                result = unittest.TextTestRunner(verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(MegaStoneTheftCases))
    finally:
        if os.environ.get("PF2_MEGA_THEFT_EVIDENCE"):
            Path(os.environ["PF2_MEGA_THEFT_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
