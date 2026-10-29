"""Owned command checks for indirect damage, blocked healing, Gene and Embargo."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
from reactive_consumption_cases import ReactiveConsumptionCases, EVIDENCE
from item_repair_cases import require_native_moves


MEDICINES = ("Potion", "Antidote", "Ether", "Max Ether", "Elixir", "Max Elixir",
             "Fresh Water", "Oran Berry", "Lum Berry", "Leppa Berry", "Mystery Berry")


class ItemHPCommandCases(ReactiveConsumptionCases):
    """Use normal inputs with labelled native/HP/PP/stock setup in private SQL."""

    def add(self, side, species, moves, **kwargs):
        """Qualify all prepared move slots before producing player-route evidence."""
        require_native_moves(species, moves)
        return super().add(side, species, moves, **kwargs)

    def setup_medicine(self, item, *, doubles=False):
        """Provide useful medicine targets without granting effects in the player route."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot

        self.item, self.mode = item, "medicine"
        self.mon = self.add(0, "Mew", ["Rain Dance", "Endure"], ability="Synchronize", slot=3)
        self.reserve = self.add(0, "Mew", ["Rain Dance", "Endure"], ability="Synchronize", slot=6)
        self.foe = self.add(1, "Mew", ["Rain Dance", "Embargo"], ability="Synchronize", slot=3)
        if doubles:
            self.partner = self.add(1, "Mew", ["Rain Dance"], ability="Synchronize", slot=6)
        for mon in (self.mon, self.reserve):
            OwnedPokemon.objects.filter(pk=mon.pk).update(current_hp=get_max_hp(mon) // 2,
                                                         status="psn" if item in {"Antidote", "Lum Berry"} else "")
            if "Ether" in item or "Elixir" in item or item in {"Leppa Berry", "Mystery Berry"}:
                ActiveMoveslot.objects.filter(pokemon=mon, slot=2).update(current_pp=0)
            OwnedPokemon.flush_cached_instance(mon)
        self.players[0].trainer.add_item(item, 2)
        self.command("inventory")
        self.launch("double" if doubles else "single")

    def check_medicine(self, item, mode):
        """Refuse before queuing or after a stale queued restriction, preserving stock."""
        from pokemon.models.core import OwnedPokemon

        self.setup_medicine(item)
        self.turn("Rain Dance", "Embargo A1", rebuild=True)
        self.assertIn("embargo", self.session.battle.participants[0].active[0].volatiles)
        if mode == "stale":
            self.session.battle.remove_volatile(self.session.battle.participants[0].active[0], "embargo")
        target = "6" if mode == "reserve" else "3"
        selector = "/Endure" if "Ether" in item or item in {"Leppa Berry", "Mystery Berry"} else ""
        before = self.resources()
        chosen = self.reserve if mode == "reserve" else self.mon
        old_row = OwnedPokemon.objects.filter(pk=chosen.pk).values("current_hp", "status").get()
        self.command("item", item + "=" + target + selector)
        if mode == "blocked":
            self.assertEqual(self.resources(), before)
            self.assertFalse(self.session.state.declare)
            self.assertIn("Embargo", str(self.players[0].messages[-1]))
            self.assertEqual(self.players[0].trainer.get_item_quantity(item), 2)
            self.rebuild()
        else:
            if mode == "stale":
                # Separate stale-state fault: the already queued target gained Embargo.
                holder = self.session.battle.participants[0].active[0]
                self.session.battle.apply_volatile_status(holder, "embargo",
                                                         source=self.session.battle.participants[1].active[0])
            self.command("attack", "Rain Dance", 1)
            self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
            self.assertEqual(self.players[0].trainer.get_item_quantity(item), 2 if mode == "stale" else 1)
            current = self.snapshot()
            new_row = OwnedPokemon.objects.filter(pk=chosen.pk).values("current_hp", "status").get()
            if mode == "stale":
                # Poison residuals are still a legitimate turn cost, PP/medicine stock stay intact.
                ours = lambda rows: [row for row in rows if row["pokemon_id"] != self.foe.pk]
                self.assertEqual(ours(current["moves"]), ours(before["moves"]))
                self.assertEqual(new_row["status"], old_row["status"])
                self.assertLessEqual(new_row["current_hp"], old_row["current_hp"])
            elif item in {"Potion", "Fresh Water", "Oran Berry"}:
                amount = {"Potion": 20, "Fresh Water": 30, "Oran Berry": 10}[item]
                self.assertEqual(new_row["current_hp"], old_row["current_hp"] + amount)
            elif item in {"Antidote", "Lum Berry"}:
                self.assertEqual(new_row["status"], "")
            else:
                slot = next(row for row in current["moves"] if row["pokemon_id"] == chosen.pk and row["slot"] == 2)
                self.assertGreater(slot["current_pp"], 0)
            self.rebuild()
            expected = self.resources()
            self.rebuild()
            self.assertEqual(self.resources(), expected)
        EVIDENCE.append({"case": self.id(), "label": "accepted-manual-embargo-target-policy",
                         "item": item, "mode": mode, "after": self.snapshot()})

    def test_repair_doubles_recipient_and_sibling_declaration(self):
        """An embargoed actor can target an unaffected partner; rejection keeps its sibling."""
        self.setup_medicine("Potion", doubles=True)
        for side, command in ((0, "A1 Rain Dance"), (0, "A2 Rain Dance"),
                              (1, "B1 Embargo A1"), (1, "B2 Rain Dance")):
            self.command("attack", command, side)
        self.command("attack", "A2 Rain Dance")
        before = dict(self.session.state.declare)
        self.command("item", "A1 Potion=3")
        self.assertEqual(self.session.state.declare, before)
        self.command("item", "A1 Potion=6")
        self.assertEqual(set(self.session.state.declare), {"A1", "A2"})
        self.rebuild()
        self.command("attack", "B1 Rain Dance", 1)
        self.command("attack", "B2 Rain Dance", 1)
        self.assertEqual(self.players[0].trainer.get_item_quantity("Potion"), 1)

    def check_damage(self, item, mode):
        """Measure guarded HP loss and physical item/history conservation after real input."""
        self.item, self.mode = item, mode
        residual = item in {"Black Sludge", "Sticky Barb"}
        ability = "Cute Charm" if mode == "ordinary" else "Magic Guard"
        self.mon = self.add(0, "Clefable" if residual else "Mew",
                            ["Rain Dance", "Gastro Acid"] if not residual else ["Rain Dance"],
                            ability=ability if residual else "Synchronize", slot=3)
        self.foe = self.add(1, "Mew" if residual else "Clefable",
                            ["Rain Dance", "Gastro Acid"] if residual else ["Rain Dance", "Pound", "Water Pulse"],
                            ability="Synchronize" if residual else ability, slot=3)
        self.players[0].trainer.add_item(item, 2)
        self.command("hold", "3=" + item)
        self.launch()
        if mode == "suppressed":
            self.turn("Rain Dance" if residual else "Gastro Acid B1",
                      "Gastro Acid A1" if residual else "Rain Dance")
        recipient = self.session.battle.participants[0 if residual else 1].active[0]
        before = recipient.hp
        bags = self.snapshot()["bags"]
        self.turn("Rain Dance", "Rain Dance" if residual else "Water Pulse A1" if item == "Rowap Berry" else "Pound A1")
        expected = 0 if mode == "magicguard" else recipient.max_hp // (6 if item == "Rocky Helmet" else 8)
        self.assertEqual(before - recipient.hp, expected)
        self.assertEqual(self.snapshot()["bags"], bags)
        if "Berry" in item:
            self.assertEqual(self.items(), [item if mode == "magicguard" else "", ""])
        self.rebuild()
        saved = self.resources()
        self.rebuild()
        self.assertEqual(self.resources(), saved)
        EVIDENCE.append({"case": self.id(), "label": "accepted-owned-indirect-item-damage",
                         "item": item, "mode": mode, "hp_loss": expected, "after": self.snapshot()})

    def check_heal(self, item):
        """An actual Heal Block expires across rebuilds before reusable healing resumes."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        self.item, self.mode = item, "healing"
        self.heal_idle = "Harden" if item == "Black Sludge" else "Safeguard"
        self.mon = self.add(0, "Muk" if item == "Black Sludge" else "Mew", [self.heal_idle], slot=3)
        self.foe = self.add(1, "Gothitelle", ["Safeguard", "Heal Block"], slot=3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=get_max_hp(self.mon) // 2)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.players[0].trainer.add_item(item, 1)
        self.command("hold", "3=" + item)
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        before = holder.hp
        self.turn(self.heal_idle, "Heal Block A1", rebuild=True)
        for _ in range(4):
            self.assertEqual(self.session.battle.participants[0].active[0].hp, before)
            self.turn(self.heal_idle, "Safeguard", rebuild=True)
        self.assertEqual(self.session.battle.participants[0].active[0].hp, before)
        self.turn(self.heal_idle, "Safeguard", rebuild=True)
        self.assertEqual(self.session.battle.participants[0].active[0].hp, before + holder.max_hp // 16)
        self.assertEqual(self.items(), [item, ""])

    def test_repair_berserk_gene_native_own_tempo_and_recycle(self):
        """Native Own Tempo blocks confusion while Attack and history persist once."""
        self.item, self.mode = "Berserk Gene", "gene"
        self.mon = self.add(0, "Spinda", ["Rain Dance", "Recycle"], ability="Own Tempo", slot=3)
        self.foe = self.add(1, "Mew", ["Rain Dance"], ability="Synchronize", slot=3)
        self.players[0].trainer.add_item(self.item, 2)
        self.command("hold", "3=" + self.item)
        self.launch()
        self.turn("Rain Dance", "Rain Dance", rebuild=True)
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual({k: v for k, v in holder.boosts.items() if v}, {"attack": 2})
        self.assertNotIn("confusion", holder.volatiles)
        self.history(True)
        self.turn("Recycle", "Rain Dance", rebuild=True)
        holder = self.session.battle.participants[0].active[0]
        # An eligible recovered Gene is used at the next normal update, once.
        self.assertEqual(holder.boosts["attack"], 4)
        self.assertNotIn("confusion", holder.volatiles)
        self.assertEqual(self.items(), ["", ""])
        self.assertEqual(self.players[0].trainer.get_item_quantity(self.item), 1)


def add_case(prefix, method, *args):
    """Count exact names and controls independently without inherited test duplication."""
    def test(self):
        """Drive ordinary commands and compare fresh SQL/checkpoint effects."""
        getattr(self, method)(*args)
    key = "".join(char for char in (prefix + "".join(args)).lower() if char.isalnum())
    setattr(ItemHPCommandCases, "test_repair_" + key, test)


for item in MEDICINES:
    for mode in ("blocked", "reserve", "stale"):
        add_case("medicine", "check_medicine", item, mode)
for item in ("Black Sludge", "Sticky Barb", "Rocky Helmet", "Jaboca Berry", "Rowap Berry"):
    for mode in ("ordinary", "magicguard", "suppressed"):
        add_case("damage", "check_damage", item, mode)
for item in ("Leftovers", "Black Sludge"):
    add_case("heal", "check_heal", item)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("item-hp-medicine-repairs"), IsolatedBattleLogs():
                names = [key for key in ItemHPCommandCases.__dict__ if key.startswith("test_repair_")]
                selected = os.environ.get("PF2_ITEM_REPAIR_SELECT")
                result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
                    ItemHPCommandCases(key) for key in names if not selected or selected in key))
    finally:
        if os.environ.get("PF2_ITEM_REPAIR_EVIDENCE"):
            Path(os.environ["PF2_ITEM_REPAIR_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
