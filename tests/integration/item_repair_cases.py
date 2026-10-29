"""October item repairs over ordinary commands and disposable owned SQL rows."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from reactive_consumption_cases import ReactiveConsumptionCases, EVIDENCE
from isolated_postgres import IsolatedPostgres


PINCH = {"Liechi Berry": {"attack": 1}, "Ganlon Berry": {"defense": 1},
         "Salac Berry": {"speed": 1}, "Petaya Berry": {"special_attack": 1},
         "Apicot Berry": {"special_defense": 1}, "Starf Berry": None}
REACTIVE = {"Absorb Bulb": ("Water Gun", {"special_attack": 1}),
            "Cell Battery": ("Thunderbolt", {"attack": 1}),
            "Luminous Moss": ("Water Gun", {"special_defense": 1}),
            "Snowball": ("Ice Beam", {"attack": 1}),
            "Kee Berry": ("Pound", {"defense": 1}),
            "Maranga Berry": ("Water Gun", {"special_defense": 1}),
            "Weakness Policy": ("Dark Pulse", {"attack": 2, "special_attack": 2}),
            "Throat Spray": ("Screech", {"special_attack": 1})}
SEEDS = {"Electric Seed": ("Electric Terrain", {"defense": 1}),
         "Grassy Seed": ("Grassy Terrain", {"defense": 1}),
         "Misty Seed": ("Misty Terrain", {"special_defense": 1}),
         "Psychic Seed": ("Psychic Terrain", {"special_defense": 1})}


def require_native_moves(species, moves):
    """Qualify prepared known slots against native learning metadata explicitly."""
    from pokemon.data.learnsets.learnsets import LEARNSETS
    from pokemon.names import normalize_name

    learnset = LEARNSETS[normalize_name(species)]["learnset"]
    for move in moves:
        if not learnset.get(normalize_name(move)):
            raise AssertionError(f"Fixture move {move} is not native to {species}.")


class ItemRepairCases(ReactiveConsumptionCases):
    """Reuse only transport and observation helpers from prior accepted fixtures."""

    def add(self, side, species, moves, **kwargs):
        """Never substitute an arbitrary move grant for native command evidence."""
        require_native_moves(species, moves)
        return super().add(side, species, moves, **kwargs)

    def setup_stat(self, item, mode):
        """Label legal native prerequisites; normal input equips each bag copy."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        self.item, self.mode = item, mode
        species, ability = (("Shuckle", "Contrary") if mode == "contrary" else
                            ("Bibarel", "Simple") if mode == "simple" else ("Mew", "Synchronize"))
        if item == "Throat Spray" and mode in {"contrary", "simple"}:
            species, ability = ("Serperior", "Contrary") if mode == "contrary" else ("Numel", "Simple")
        self.sound = "Growl" if species == "Numel" else "Round" if species == "Serperior" else "Screech"
        self.idle = "Safeguard" if species in {"Shuckle", "Serperior"} else "Rain Dance"
        moves = [self.idle, "Endure"] + ([self.sound] if item == "Throat Spray" else [])
        if species == "Mew":
            moves.append("Recycle")
        self.mon = self.add(0, species, moves, ability=ability, slot=3)
        self.move = (SEEDS[item][0] if item in SEEDS else
                     REACTIVE[item][0] if item in REACTIVE else "Pound")
        if item == "Weakness Policy":
            self.move = "Water Gun" if species == "Shuckle" else "Magical Leaf" if species == "Bibarel" else self.move
        self.wrong_terrain = "Misty Terrain" if item != "Misty Seed" else "Grassy Terrain"
        source_moves = [self.move, "Rain Dance", "Magic Room"]
        if item in SEEDS:
            source_moves.append(self.wrong_terrain)
        self.foe = self.add(1, "Mew", list(dict.fromkeys(source_moves)),
                             ability="Synchronize", slot=3, level=50 if item in PINCH or item == "Throat Spray" else 5)
        if item in PINCH:
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=get_max_hp(self.mon) // 4 + 1)
            OwnedPokemon.flush_cached_instance(self.mon)
        self.players[0].trainer.add_item(item, 2)
        self.command("inventory")
        self.command("hold", "3=" + item)
        self.assertEqual(self.items(), [item, ""])
        self.launch()
        if mode == "suppressed":
            self.turn(self.idle, "Magic Room")
            self.rebuild()

    def stat_trigger(self):
        """Use the reviewed item's real low-HP, actual-hit, sound or terrain trigger."""
        if self.item in PINCH:
            self.turn("Endure", "Pound A1")
        elif self.item == "Throat Spray":
            self.turn(self.sound + " B1", "Rain Dance")
        else:
            self.turn(self.idle, self.move + (" A1" if self.item in REACTIVE else ""))

    def check_stat(self, item, mode):
        """Compare actual stages, independent SQL and repeat rebuild conservation."""
        from pokemon.battle.utils import get_modified_stat

        self.setup_stat(item, mode)
        before = self.resources()
        holder = self.session.battle.participants[0].active[0]
        stats_before = {key: get_modified_stat(holder, key) for key in
                        ("attack", "defense", "special_attack", "special_defense", "speed")}
        if mode == "rollback":
            original, faults = self.session.storage.set, []

            def refuse(key, value):
                """Fail after owned SQL has recorded this exact consumption."""
                if key == "data" and not self.items()[0]:
                    faults.append(self.snapshot())
                    raise RuntimeError("item-repair isolated checkpoint refusal")
                return original(key, value)

            with patch.object(self.session.storage, "set", side_effect=refuse):
                try:
                    self.stat_trigger()
                except (RuntimeError, AssertionError):
                    pass
            self.assertEqual(len(faults), 1)
            self.assertEqual(self.resources(), before)
            self.session.execute_persistent_turn()
        else:
            self.stat_trigger()
        holder = self.session.battle.participants[0].active[0]
        blocked = mode == "suppressed"
        self.assertEqual(self.items(), [item if blocked else "", ""])
        self.assertEqual(self.snapshot()["bags"], before["bags"])
        stages = {key: value for key, value in holder.boosts.items() if value}
        if blocked:
            self.assertEqual(stages, {})
        else:
            multiplier = -1 if mode == "contrary" else 2 if mode == "simple" else 1
            effects = PINCH.get(item) if item in PINCH else (REACTIVE.get(item) or SEEDS[item])[1]
            if item == "Starf Berry":
                self.assertEqual(len(stages), 1)
                self.assertEqual(list(stages.values()), [2 * multiplier])
            else:
                self.assertEqual(stages, {key: delta * multiplier for key, delta in effects.items()})
            for key, stage in stages.items():
                actual = get_modified_stat(holder, key)
                self.assertLess(actual, stats_before[key]) if stage < 0 else self.assertGreater(actual, stats_before[key])
        self.history(not blocked)
        EVIDENCE.append({"case": self.id(), "label": "accepted-owned-stat-effects",
                         "item": item, "mode": mode, "stages": stages, "after": self.snapshot()})
        # Non-native Recycle is never granted just for a native ability test.
        if mode in {"normal", "rollback"} and item not in PINCH:
            if item in SEEDS:
                # Recycle on matching terrain immediately uses the recovered seed.
                self.turn("Rain Dance", self.wrong_terrain)
            self.turn("Recycle", "Rain Dance", rebuild=True)
            self.assertEqual(self.items(), [item, ""])
        self.session.end()
        self.session = None
        self.command("party", "3")
        self.assertEqual(self.players[0].trainer.get_item_quantity(item), 1)

    def test_repair_mirror_herb_observes_actual_reactive_boost(self):
        """A real opposing held consumer sees the stat item's AfterBoost event."""
        self.setup_stat("Throat Spray", "normal")
        self.session.end()
        self.session = None
        self.players[1].trainer.add_item("Mirror Herb", 1)
        self.command("hold", "3=Mirror Herb", 1)
        self.launch()
        self.stat_trigger()
        holder, foe = [part.active[0] for part in self.session.battle.participants]
        self.assertEqual((holder.boosts["special_attack"], foe.boosts["special_attack"]), (1, 1))
        self.assertEqual(self.items(), ["", ""])
        self.rebuild()
        self.assertEqual(self.session.battle.participants[1].active[0].boosts["special_attack"], 1)

    def test_repair_liechi_retains_three_earned_swords_dances_and_next_attack(self):
        """Normal moves earn +6 before the actual low-HP trigger and next hit."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        self.item, self.mode = "Liechi Berry", "earned-stages"
        self.mon = self.add(0, "Mew", ["Swords Dance", "Endure", "Pound", "Recycle"], slot=3)
        self.foe = self.add(1, "Mew", ["Safeguard", "Pound"], slot=3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=get_max_hp(self.mon) // 4 + 1)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.players[0].trainer.add_item(self.item, 1)
        self.command("hold", "3=" + self.item)
        self.launch()
        for _ in range(3):
            self.turn("Swords Dance", "Safeguard", rebuild=True)
        self.assertEqual(self.session.battle.participants[0].active[0].boosts["attack"], 6)
        self.turn("Endure", "Pound A1", rebuild=True)
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(holder.boosts["attack"], 6)
        self.assertNotIn("atk", holder.boosts)
        self.assertEqual(self.items(), ["", ""])
        before = self.session.battle.participants[1].active[0].hp
        self.turn("Pound B1", "Safeguard", rebuild=True)
        self.assertLess(self.session.battle.participants[1].active[0].hp, before)
        self.history(True)


def add_stat(item, mode):
    """Give every exact inventory/ability/fault case its own counted result."""
    def test(self):
        """Run the ordinary parser, action, checkpoint and independent SQL checks."""
        self.check_stat(item, mode)
    key = "".join(char for char in (item + mode).lower() if char.isalnum())
    setattr(ItemRepairCases, "test_repair_" + key, test)


for item in (*PINCH, *REACTIVE, *SEEDS):
    for mode in ("normal", "contrary", "simple", "suppressed", "rollback"):
        add_stat(item, mode)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("item-repairs-922-928"), IsolatedBattleLogs():
                names = [key for key in ItemRepairCases.__dict__ if key.startswith("test_repair_")]
                selected = os.environ.get("PF2_ITEM_REPAIR_SELECT")
                suite = unittest.TestSuite(ItemRepairCases(key) for key in names if not selected or selected in key)
                result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        if os.environ.get("PF2_ITEM_REPAIR_EVIDENCE"):
            Path(os.environ["PF2_ITEM_REPAIR_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
