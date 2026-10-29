"""Paired ordinary next actions after stat-item triggers and checkpoint restore."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from item_repair_cases import ItemRepairCases, PINCH, REACTIVE, SEEDS, EVIDENCE
from isolated_postgres import IsolatedPostgres


RESULTS = {}


class ItemNextActionCases(ItemRepairCases):
    """Observe actual moves without replacing accuracy, damage or turn ordering."""

    def add(self, side, species, moves, **kwargs):
        """Prepare four native known slots and a faster, surviving control opponent."""
        if side == 0:
            moves = ["Rain Dance"]
            if self.item in PINCH:
                moves.append("Endure")
            if self.item == "Throat Spray":
                moves.append("Screech")
            if "attack" in self.probe_stats:
                moves.append("Pound")
            if "special_attack" in self.probe_stats:
                moves.append("Confusion")
        else:
            moves = [self.move, "Rain Dance", "Magic Room"]
            if "defense" in self.probe_stats:
                moves.append("False Swipe")
            if "special_defense" in self.probe_stats:
                moves.append("Mud-Slap")
            kwargs["level"] = 55
        moves = list(dict.fromkeys(moves))
        self.assertLessEqual(len(moves), 4)
        return super().add(side, species, moves, **kwargs)

    def probe(self, stat):
        """Measure an actual move before residual healing, with real PP and SQL HP."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.names import normalize_name

        battle = self.session.battle
        holder, foe = [part.active[0] for part in battle.participants]
        source_side = int(stat in {"defense", "special_defense"})
        move = {"attack": "Pound", "special_attack": "Confusion",
                "defense": "False Swipe", "special_defense": "Mud-Slap",
                "speed": "Rain Dance"}[stat]
        model = self.foe if source_side else self.mon
        slot = next(slot for slot in ActiveMoveslot.objects.filter(pokemon=model).select_related("move")
                    if normalize_name(slot.move.name) == normalize_name(move))
        pp = slot.current_pp
        observed, order = [], []
        original = battle.use_move

        def observe(action, **kwargs):
            """Delegate untouched mechanics and capture only their actual results."""
            source = action.pokemon or action.actor.active[0]
            side = int(source is foe)
            target = holder if side else foe
            before = target.hp
            order.append(side)
            result = original(action, **kwargs)
            if side == source_side and normalize_name(action.move.name) == normalize_name(move):
                observed.append(before - target.hp)
            return result

        battle.rng = random.Random(928)
        ours = move + " B1" if stat in {"attack", "special_attack"} else "Rain Dance"
        theirs = move + " A1" if source_side else "Rain Dance"
        with patch.object(battle, "use_move", side_effect=observe):
            self.turn(ours, theirs)
        self.assertEqual(len(observed), 1)
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)
        for model, runtime in ((self.mon, holder), (self.foe, foe)):
            self.assertEqual(OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=model.pk), runtime.hp)
        self.assertEqual(sorted(order), [0, 1])
        return {"damage": observed[0], "holder_first": order[0] == 0,
                "move": move, "remaining_pp": pp - 1}

    def check_next_action(self, item, mode):
        """Trigger through normal commands, restore, then spend the next action."""
        effects = (PINCH[item] if item in PINCH else
                   REACTIVE[item][1] if item in REACTIVE else SEEDS[item][1])
        self.probe_stats = tuple(effects or {"attack": 2})
        self.setup_stat(item, mode)
        if item == "Starf Berry":
            # Explicit legal stage prerequisite makes Attack the sole eligible
            # Starf choice. Existing unit/SQL coverage handles random selection.
            holder = self.session.battle.participants[0].active[0]
            for stat in ("defense", "special_attack", "special_defense", "speed"):
                holder.boosts[stat] = 6
            EVIDENCE.append({"case": self.id(), "label": "separate-legal-stage-prerequisite",
                             "stages": dict(holder.boosts), "limit": "Prepared stages, not earned-move evidence"})
        bags = self.snapshot()["bags"]
        self.stat_trigger()
        self.rebuild()
        self.assertEqual(self.items(), [item if mode == "suppressed" else "", ""])
        probes = {stat: self.probe(stat) for stat in self.probe_stats}
        self.assertEqual(self.snapshot()["bags"], bags)
        self.history(mode == "normal")
        RESULTS.setdefault(item, {})[mode] = probes
        EVIDENCE.append({"case": self.id(), "label": "accepted-next-action-after-restore",
                         "item": item, "mode": mode, "probes": probes, "after": self.snapshot()})

    def test_next_zzz_compare_all_eighteen_pairs(self):
        """Compare real damage or order against the same legally suppressed item."""
        self.assertEqual(set(RESULTS), set((*PINCH, *REACTIVE, *SEEDS)))
        for item, modes in RESULTS.items():
            self.assertEqual(set(modes), {"normal", "suppressed"}, item)
            for stat, actual in modes["normal"].items():
                control = modes["suppressed"][stat]
                with self.subTest(item=item, stat=stat):
                    if stat == "speed":
                        self.assertFalse(control["holder_first"])
                        self.assertTrue(actual["holder_first"])
                    else:
                        self.assertGreater(min(actual["damage"], control["damage"]), 0)
                        if stat in {"attack", "special_attack"}:
                            self.assertGreater(actual["damage"], control["damage"])
                        else:
                            self.assertLess(actual["damage"], control["damage"])
        EVIDENCE.append({"case": self.id(), "label": "accepted-all-eighteen-paired-comparisons",
                         "comparisons": RESULTS})


def add_next_action(item, mode):
    """Give each independent SQL fixture its own counted result."""
    def test(self):
        """Resolve this exact item and its paired next-action observation."""
        self.check_next_action(item, mode)
    key = "".join(char for char in (item + mode).lower() if char.isalnum())
    setattr(ItemNextActionCases, "test_next_" + key, test)


for item in (*PINCH, *REACTIVE, *SEEDS):
    for mode in ("normal", "suppressed"):
        add_next_action(item, mode)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("item-next-action-922-924"), IsolatedBattleLogs():
                names = sorted(key for key in ItemNextActionCases.__dict__ if key.startswith("test_next_"))
                selected = os.environ.get("PF2_ITEM_NEXT_ACTION_SELECT")
                suite = unittest.TestSuite(ItemNextActionCases(key) for key in names if not selected or selected in key)
                result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        if os.environ.get("PF2_ITEM_NEXT_ACTION_EVIDENCE"):
            Path(os.environ["PF2_ITEM_NEXT_ACTION_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
