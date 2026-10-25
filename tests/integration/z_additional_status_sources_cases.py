"""Six explicit status Z sources with real owned effects and source-PP payment."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from mega_stone_cases import MegaStoneCases
from z_native_cases import NativeZCases
from z_special_sources_cases import SpecialZSourceCases
from recovery_move_sources_cases import HalfRoll
from pokemon.names import normalize_name

PAIRS = (
    ("Normalium Z", "Starmie", "Recover"),
    ("Flyinium Z", "Pidgeot", "Roost"),
    ("Normalium Z", "Pelipper", "Protect"),
    ("Poisonium Z", "Clodsire", "Toxic"),
    ("Electrium Z", "Mareep", "Thunder Wave"),
    ("Grassium Z", "Bulbasaur", "Synthesis"),
)
PASSIVE = {
    "Starmie": ("Harden", "A1"),
    "Pidgeot": ("Agility", "A1"),
    "Pelipper": ("Stockpile", "A1"),
    "Clodsire": ("Amnesia", "A1"),
    "Mareep": ("Growl", "B1"),
    "Bulbasaur": ("Growl", "B1"),
}


class AdditionalStatusZSourceCases(unittest.TestCase):
    """Use labelled initial HP/stages; all useful effects execute through commands."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild
    fixture_native = MegaStoneCases.fixture_native
    acquire = SpecialZSourceCases.acquire
    setUp = NativeZCases.setUp
    tearDown = NativeZCases.tearDown

    def queue(self, source, target, *, ordinary=False, reply="Lock-On"):
        """Declare actual source/target and ordinary legal peer actions."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record(
                "attack" if ordinary else "zmove",
                "A1 " + source + (" " + target if ordinary else "=" + target),
            )
            if self.session.battle.participants[0].max_active == 2:
                self.record("attack", "A2 Splash A2")
            self.record(
                "attack",
                "B1 "
                + reply
                + (" A1" if reply in {"Lock-On", "Growl", "Sand Attack", "Powder Snow"} else " B1"),
                side=1,
            )
            if self.session.battle.participants[1].max_active == 2:
                self.record("attack", "B2 Splash B2", side=1)

    def flow(self, pair, facet):
        """Validate one bounded profile's real effect, refusal or turn rollback."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.battle.z_moves import ZMoves

        item, native, source = pair
        self_target = source not in {"Toxic", "Thunder Wave"}
        target_label = "A1" if self_target else "B1"
        passive, passive_target = PASSIVE[native]
        self.mon = (
            self.acquire(native, source)
            if facet == "native"
            else self.fixture_native(native, [source, passive], 3, level=100)
        )
        maximum = self.mon.get_max_hp()
        initial = maximum if facet == "full" else max(1, maximum // 4)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            current_hp=initial, **({"status": "slp", "sleep_turns": 3} if facet == "sleep" else {})
        )
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.fixture_native("Hoppip", ["Splash"], 4, level=5)
        self.fixture_native("Hoppip", ["Splash"], 2, side=1, level=5)
        immune = facet == "immune"
        foe = (
            "Espeon"
            if facet == "bounce"
            else (
                "Empoleon"
                if immune and source == "Toxic"
                else (
                    "Diglett"
                    if immune
                    else "Mew" if facet in {"magicroom", "embargo"} else "Regice"
                )
            )
        )
        reply = (
            "Morning Sun"
            if foe == "Espeon"
            else (
                "Growl"
                if foe == "Empoleon"
                else (
                    "Sand Attack"
                    if foe == "Diglett"
                    else (
                        "Safeguard"
                        if foe == "Mew"
                        else "Powder Snow" if source == "Protect" else "Lock-On"
                    )
                )
            )
        )
        moves = [reply] + (
            ["Magic Room", "Embargo"] if foe == "Mew" else ["Protect"] if foe == "Regice" else []
        )
        self.foe = self.fixture_native(foe, moves, 1, side=1, level=100)
        if facet == "bounce":
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Magic Bounce")
            core.OwnedPokemon.flush_cached_instance(self.foe)  # Labelled native hidden ability.
        if facet != "missing":
            equipped = (
                ("Firium Z" if item == "Normalium Z" else "Normalium Z")
                if facet == "wrong_crystal"
                else item
            )
            self.buy(equipped, price=10000, quantity=1)
            self.record("hold", "3=" + equipped)
        self.launch("single" if facet == "native" else "double")
        battle = self.session.battle
        user = battle.participants[0].active[0]
        user.boosts.update(attack=-2, defense=2, special_defense=-1)
        if facet == "taunt":
            battle.apply_volatile_status(user, "taunt", source=battle.participants[1].active[0])
        if facet == "healblock":
            battle.apply_volatile_status(user, "healblock", source=battle.participants[1].active[0])
        if facet == "zero_pp":
            ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=0)
            for move in user.moves:
                if normalize_name(move.name) == normalize_name(source):
                    move.pp = 0
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "separate-status-source-prerequisites",
                "item": item,
                "source": source,
                "facet": facet,
                "native_acquisition": facet == "native",
                "initial_hp": initial,
                "initial_stages": dict(user.boosts),
                "after": self.observation(),
            }
        )
        if facet in {
            "missing",
            "wrong_crystal",
            "zero_pp",
            "invalid_target",
            "invalid_source",
            "transformed",
            "wrong_runtime",
        }:
            old_species = user.species
            user.transformed = facet == "transformed"
            if facet == "wrong_runtime":
                user.species = "Eevee"
            before = self.observation()
            self.record(
                "zmove",
                "A1 "
                + ("4" if facet == "invalid_source" else "1")
                + "="
                + ("A9" if facet == "invalid_target" else target_label),
            )
            self.assertEqual(self.observation(), before)
            self.assertFalse(battle.z_pending)
            user.transformed = False
            user.species = old_species
            core.EVIDENCE.append(
                {
                    "case": self._testMethodName,
                    "event": "status-source-refused",
                    "source": source,
                    "facet": facet,
                }
            )
            return
        if facet == "repeat":
            self.queue(source, "A1", ordinary=True, reply="Powder Snow")
            self.session.execute_persistent_turn()
            self.rebuild()
            user = self.session.battle.participants[0].active[0]
            self.assertEqual(user.volatiles["stall"]["counter"], 3)
            user.boosts.update(attack=-2, defense=2, special_defense=-1)
        if facet in {"magicroom", "embargo"}:
            with patch.object(self.session, "maybe_run_turn"):
                self.record("attack", "A1 " + passive + " " + passive_target)
                self.record("attack", "A2 Splash A2")
                self.record(
                    "attack",
                    "B1 " + ("Magic Room" if facet == "magicroom" else "Embargo A1"),
                    side=1,
                )
                self.record("attack", "B2 Splash B2", side=1)
            self.session.execute_persistent_turn()
            self.rebuild()
            user = self.session.battle.participants[0].active[0]
            user.boosts.update(attack=-2, defense=2, special_defense=-1)
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        initial_hp = user.hp
        discovery = self.observation()
        self.record("zmove", "A1")
        self.assertEqual(self.observation(), discovery)
        self.assertIn(
            normalize_name(source), normalize_name("\n".join(map(str, self.player.messages[-2:])))
        )
        self.queue(
            "1" if facet != "plain" else source,
            target_label,
            ordinary=facet == "plain",
            reply="Protect" if facet == "protect" else reply,
        )
        self.rebuild()
        self.rebuild()
        before = self.observation()
        if facet in {"checkpoint_fault", "payment_fault"}:
            original = self.session.storage.set
            begin = ZMoves.begin.__func__

            def fail_save(name, value):
                """Fail after the real effect before its checkpoint commits."""
                if name == "data":
                    raise RuntimeError("new status source checkpoint fault")
                return original(name, value)

            def fail_payment(cls, *args):
                """Fail after actual PP and side budget payment."""
                begin(cls, *args)
                raise RuntimeError("new status source payment fault")

            fault = (
                patch.object(self.session.storage, "set", side_effect=fail_save)
                if facet == "checkpoint_fault"
                else patch.object(ZMoves, "begin", classmethod(fail_payment))
            )
            with fault, self.assertRaisesRegex(RuntimeError, "new status source"):
                self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
        self.session.battle.rng = HalfRoll(12) if facet == "repeat" else random.Random(12)
        self.session.execute_persistent_turn()
        battle = self.session.battle
        # A prevented shield can let the real foe faint this holder and trigger
        # an ordinary replacement. Verify the original owned source, not its slot.
        user = next(
            mon
            for mon in battle.participants[0].pokemons
            if mon.model_id == "owned:" + str(self.mon.pk)
        )
        target = next(
            mon
            for mon in battle.participants[1].pokemons
            if mon.model_id == "owned:" + str(self.foe.pk)
        )
        spent = facet not in {"sleep", "taunt", "healblock"}
        z_spent = spent and facet != "plain"
        self.assertEqual(
            ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - int(spent)
        )
        self.assertEqual(battle.z_used, {"A"} if z_spent else set())
        if z_spent:
            if source in {"Toxic", "Thunder Wave"}:
                self.assertEqual(
                    user.boosts["defense" if source == "Toxic" else "special_defense"],
                    3 if source == "Toxic" else 0,
                )
                if facet in {"immune", "protect", "magicroom", "embargo", "bounce"}:
                    # The legal faster Safeguard on the latter two controls
                    # prevents the base status while leaving the Z bonus paid.
                    self.assertFalse(target.status)
                    if facet == "bounce":
                        self.assertFalse(
                            user.status
                        )  # Native Poison/Electric reflected-status immunity.
                else:
                    self.assertEqual(target.status, "tox" if source == "Toxic" else "par")
            else:
                self.assertEqual(
                    (user.boosts["attack"], user.boosts["defense"], user.boosts["special_defense"]),
                    (0, 2, 0),
                )
        if source in {"Recover", "Roost", "Synthesis"}:
            expected = (
                initial_hp
                if not spent or facet == "full"
                else min(maximum, initial_hp + maximum // 2)
            )
            self.assertEqual(user.hp, expected)
        if source == "Roost":
            self.assertIn("Flying", user.types)
            self.assertNotIn("roost", user.volatiles)
        if source == "Protect":
            (
                self.assertLess(user.hp, initial_hp)
                if facet == "repeat" or not spent
                else self.assertEqual(user.hp, initial_hp)
            )
        self.assertFalse(getattr(battle, "_callback_failures", []))
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "new-status-source-effect",
                "source": source,
                "facet": facet,
                "item": item,
                "hp_before": initial_hp,
                "hp_after": user.hp,
                "user_stages": dict(user.boosts),
                "target_status": target.status,
                "pp_before": pp,
                "pp_after": ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp,
                "side_use": sorted(battle.z_used),
                "after": self.observation(),
            }
        )
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if z_spent else set())
        self.session.end()
        self.session = None
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)


FACETS = [
    "native",
    "active",
    "full",
    "sleep",
    "taunt",
    "plain",
    "zero_pp",
    "missing",
    "wrong_crystal",
    "invalid_target",
    "invalid_source",
    "transformed",
    "wrong_runtime",
    "checkpoint_fault",
    "payment_fault",
    "magicroom",
    "embargo",
]
for pair in PAIRS:
    extras = (
        ["immune", "protect", "bounce"]
        if pair[2] in {"Toxic", "Thunder Wave"}
        else ["repeat"] if pair[2] == "Protect" else ["healblock"]
    )
    for facet in FACETS + extras:

        def test(self, pair=pair, facet=facet):
            """One exact native source through current commands and complete real turns."""
            self.flow(pair, facet)

        setattr(AdditionalStatusZSourceCases, "test_" + normalize_name(pair[2]) + "_" + facet, test)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (
                cmd_battle_zmove,
                cmd_battle_item,
                cmd_learn_evolve,
                cmd_movesets,
            )
        core.acquisition.COMMANDS.update(
            {
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
                "movesets": (cmd_movesets, cmd_movesets.CmdMovesets),
            }
        )
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(AdditionalStatusZSourceCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
