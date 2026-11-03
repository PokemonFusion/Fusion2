"""The next five damaging Z sources and Calm Mind through owned commands."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import z_special_sources_cases as damaging


PAIRS = (("Firium Z", "Magmar", "Fire Blast", "Dachsbun"),
         ("Firium Z", "Growlithe", "Flare Blitz", "Dachsbun"),
         ("Waterium Z", "Gyarados", "Hydro Pump", "Vaporeon"),
         ("Electrium Z", "Pikachu", "Thunder", "Jolteon"),
         ("Groundium Z", "Gastrodon", "Earth Power", "Flygon"))


class NextZSourceCases(damaging.SpecialZSourceCases):
    """Reuse the earlier real payment/effect/refusal matrix with explicit new data."""

    def calm_mind(self, facet):
        """Clear negatives, apply ordinary boosts and pay one source PP/budget."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.battle.z_moves import ZMoves
        from pokemon.names import normalize_name

        self.mon = (self.acquire("Ralts", "Calm Mind") if facet == "native" else
                    self.fixture_native("Ralts", ["Calm Mind", "Growl"], 3))
        self.foe = self.fixture_native("Mew", ["Safeguard", "Magic Room", "Embargo"], 1, side=1)
        crystal = "Normalium Z" if facet == "wrong_crystal" else "Psychium Z"
        if facet != "missing":
            self.buy(crystal, price=10000, quantity=1)
            self.record("hold", "3=" + crystal)
        self.launch("single")
        user = self.session.battle.participants[0].active[0]
        if facet in {"magicroom", "embargo"}:
            with patch.object(self.session, "maybe_run_turn"):
                self.record("attack", "A1 Growl B1")
                self.record("attack", "B1 " + ("Magic Room" if facet == "magicroom" else "Embargo A1"), side=1)
            self.session.execute_persistent_turn()
        user = self.session.battle.participants[0].active[0]
        # Explicit checkpoint prerequisites; actual Calm Mind supplies all useful boosts.
        user.boosts.update(attack=-2, defense=2, special_attack=-3, special_defense=-1)
        if facet == "zero_pp":
            ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=0)
            user.moves[0].pp = 0
        if facet == "sleep":
            user.setStatus("slp", source=user, battle=self.session.battle)
            user.sleep_turns = 3
        before = self.observation()
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "A1 Calm Mind=A1")
            if facet in {"missing", "wrong_crystal", "zero_pp"}:
                self.assertEqual(self.observation(), before)
                return
            pending = self.observation()
            self.record("zmove", "A1 Calm Mind=A1")
            self.assertEqual(self.observation(), pending)
            self.record("attack", "B1 Safeguard B1", side=1)
        self.rebuild()
        self.rebuild()
        before = self.observation()
        if facet == "checkpoint_fault":
            original = self.session.storage.set

            def refuse(key, value):
                """Fail after the actual source/effect writes, before checkpoint commit."""
                if key == "data":
                    raise RuntimeError("Calm Mind isolated checkpoint refusal")
                return original(key, value)

            with patch.object(self.session.storage, "set", side_effect=refuse):
                with self.assertRaisesRegex(RuntimeError, "Calm Mind isolated"):
                    self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
        self.session.battle.rng = random.Random(12)
        self.session.execute_persistent_turn()
        user = self.session.battle.participants[0].active[0]
        spent = facet != "sleep"
        self.assertEqual(self.session.battle.z_used, {"A"} if spent else set())
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - int(spent))
        self.assertEqual((user.boosts["attack"], user.boosts["defense"], user.boosts["special_attack"], user.boosts["special_defense"]),
                         (0, 2, 1, 1) if spent else (-2, 2, -3, -1))
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        damaging.core.EVIDENCE.append({"case": self.id(), "event": "accepted-calm-mind-bonus-and-source",
                                       "facet": facet, "after": self.observation()})
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if spent else set())
        if spent:
            before = self.observation()
            self.record("zmove", "A1 Calm Mind=A1")
            self.assertEqual(self.observation(), before)
        self.session.end()
        self.session = None
        self.assertEqual(normalize_name(damaging.core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item), "psychiumz")


for pair in PAIRS:
    for facet in damaging.FACETS:
        def test(self, pair=pair, facet=facet):
            """Use the named damaging source's ordinary command/control matrix."""
            self.flow(pair, facet)
        setattr(NextZSourceCases, "test_next_" + pair[2].lower().replace(" ", "") + "_" + facet, test)
for facet in ("native", "active", "magicroom", "embargo", "sleep", "zero_pp", "missing", "wrong_crystal", "checkpoint_fault"):
    def test(self, facet=facet):
        """Use the status source's actual command, bonus, PP and durable side budget."""
        self.calm_mind(facet)
    setattr(NextZSourceCases, "test_next_calmmind_" + facet, test)


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs

    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            damaging.core.load_runtime()
            with OrdinaryPlayerFixtures("next-six-z-sources-932"), IsolatedBattleLogs():
                from commands.player import cmd_battle_zmove, cmd_battle_item, cmd_learn_evolve, cmd_movesets
                damaging.core.acquisition.COMMANDS.update({
                    "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                    "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                    "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
                    "movesets": (cmd_movesets, cmd_movesets.CmdMovesets)})
                damaging.PASSIVE.update({"Magmar": ("Smokescreen", "B1"), "Growlithe": ("Agility", "A1"),
                                        "Gyarados": ("Dragon Dance", "A1"), "Gastrodon": ("Harden", "A1")})
                damaging.IMMUNE_REPLY.update({"Dachsbun": "Work Up", "Vaporeon": "Acid Armor", "Flygon": "Sand Attack"})
                names = [name for name in NextZSourceCases.__dict__ if name.startswith("test_next_")]
                selected = os.environ.get("PF2_Z_NEXT_SELECT")
                result = unittest.TextTestRunner(verbosity=2, failfast=True).run(unittest.TestSuite(
                    NextZSourceCases(name) for name in names if not selected or selected in name))
    finally:
        if os.environ.get("PF2_Z_NEXT_EVIDENCE"):
            Path(os.environ["PF2_Z_NEXT_EVIDENCE"]).write_text(
                json.dumps(damaging.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf8")
    raise SystemExit(not result.wasSuccessful())
