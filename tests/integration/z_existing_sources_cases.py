"""Two explicit generic Z sources through purchased crystals and owned commands."""
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
from pokemon.names import normalize_name

PAIRS = (("Firium Z", "Charizard", "Flamethrower", "Vulpix"),
         ("Waterium Z", "Slowpoke", "Surf", "Vaporeon"))


class ExistingZSourceCases(unittest.TestCase):
    """Keep native acquisition separate from labelled opponent/condition fixtures."""

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
    setUp = NativeZCases.setUp
    tearDown = NativeZCases.tearDown

    def acquire(self, species, source):
        """Complete actual hunt/capture, nickname choice, teaching and active menu."""
        from pokemon.models.moves import ActiveMoveslot
        self.room.db.allow_hunting = True
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 100
        self.room.db.hunt_chart = [{"name": species, "min_level": 100, "max_level": 100, "weight": 1}]
        self.buy("Master Ball", price=1000, quantity=1)
        before = set(core.OwnedPokemon.objects.filter(trainer=self.player.trainer).values_list("pk", flat=True))
        self.record("hunt")
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session)
        self.assertEqual(str(self.session.battle.participants[1].active[0].species), species)
        self.record("item", "Master Ball")
        if self.player.ndb._evmenu:
            self.reply("no")
            core.EVIDENCE.append({"case": self._testMethodName, "event": "ordinary-capture-nickname", "input": "no"})
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 0)
        caught = core.OwnedPokemon.objects.filter(trainer=self.player.trainer).exclude(pk__in=before).get()
        self.mons.append(caught)
        self.session.end()
        self.session = None
        # Separate canonical-slot prerequisite, not a player placement claim.
        for placement in self.player.storage.placements.filter(location_type="party", slot=3):
            core.PlacementService(self.player.storage).to_box(placement.pokemon)
        core.PlacementService(self.player.storage).to_party(caught, slot=3)
        self.mon = caught
        self.record("teach", "3=" + source)
        if self.player.ndb._evmenu:
            self.reply("no")
        self.room.db.is_pokemon_center = True
        self.record("movesets")
        for answer in ("3", "edit 1", source, "back", "q"):
            self.reply(answer)
        slots = list(ActiveMoveslot.objects.filter(pokemon=caught).select_related("move"))
        self.assertEqual([normalize_name(slot.move.name) for slot in slots], [normalize_name(source)],
                         self.player.messages[-10:])
        core.OwnedPokemon.flush_cached_instance(caught)
        return caught

    def queue_turn(self, source, *, ordinary=False, reply="Leer"):
        """Use real declarations; control scheduling only, not battle outcomes."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack" if ordinary else "zmove",
                        "A1 " + source + (" B1" if ordinary else "=B1"))
            if self.session.battle.participants[0].max_active == 2:
                self.record("attack", "A2 Growl B1")
            self.record("attack", "B1 " + reply + (" A1" if reply in {"Leer", "Tail Whip"} else " B1"), side=1)
            if self.session.battle.participants[1].max_active == 2:
                self.record("attack", "B2 Growl A2", side=1)

    def flow(self, pair, facet):
        """Exercise the exact source, guards, target/effects, checkpoint and return."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.battle.z_moves import ZMoves
        item, native, source, immune = pair
        captured = facet == "native"
        self.mon = self.acquire(native, source) if captured else self.fixture_native(native, [source, "Growl"], 3)
        foe = immune if facet == "immune" else "Mew" if facet in {"magicroom", "embargo"} else "Shelgon"
        moves = ["Magic Room", "Safeguard"] if facet == "magicroom" else ["Embargo", "Safeguard"] if facet == "embargo" else ["Protect", "Leer"]
        if facet == "immune":
            moves = ["Tail Whip"]
        self.foe = self.fixture_native(foe, moves, 1, side=1, level=100)
        if facet == "sleep":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
            core.OwnedPokemon.flush_cached_instance(self.mon)
        if facet == "zero_pp":
            ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1).update(current_pp=0)
            core.OwnedPokemon.flush_cached_instance(self.mon)
        equipped = "Normalium Z" if facet == "wrong_crystal" else item
        if facet != "missing":
            self.buy(equipped, price=10000, quantity=1)
            self.record("hold", "3=" + equipped)
        core.EVIDENCE.append({"case": self._testMethodName, "event": "separate-source-prerequisites",
                              "item": item, "source": source, "facet": facet,
                              "native_acquisition": "ordinary hunt/capture/teach/moveset" if captured else "tagged native legal-move fixture",
                              "canonical_slot_setup": "tagged placement slot3", "foe": foe,
                              "condition_setup": facet if facet in {"sleep", "zero_pp"} else None,
                              "after": self.observation()})
        self.launch("single" if captured else "double")
        self.session.battle.debug = True
        if facet in {"missing", "wrong_crystal", "zero_pp", "invalid_target", "invalid_source", "transformed", "wrong_runtime"}:
            holder = self.session.battle.participants[0].active[0]
            original_species = holder.species
            if facet == "transformed":
                holder.transformed = True  # Labelled offline eligibility adapter.
            if facet == "wrong_runtime":
                holder.species = "Eevee"  # Labelled runtime/SQL identity conflict.
            before = self.observation()
            self.record("zmove", "A1 " + ("2" if facet == "invalid_source" else "1") + "=" + ("A9" if facet == "invalid_target" else "B1"))
            self.assertEqual(self.observation(), before)
            self.assertFalse(self.session.battle.z_pending)
            core.EVIDENCE.append({"case": self._testMethodName, "event": "rejected-before-action",
                                  "facet": facet, "item": item, "source": source, "unchanged": True})
            holder.transformed = False
            holder.species = original_species
            return
        if facet in {"magicroom", "embargo"}:
            with patch.object(self.session, "maybe_run_turn"):
                self.record("attack", "A1 Growl B1")
                self.record("attack", "A2 Growl B1")
                self.record("attack", "B1 Magic Room" if facet == "magicroom" else "B1 Embargo A1", side=1)
                self.record("attack", "B2 Growl A2", side=1)
            self.session.execute_persistent_turn()
            self.rebuild()
        holder, target = [part.active[0] for part in self.session.battle.participants]
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        discovery = self.observation()
        self.record("zmove", "A1")
        self.assertEqual(self.observation(), discovery)
        self.assertIn(source, "\n".join(map(str, self.player.messages[-2:])))
        self.queue_turn("1" if facet != "plain" else source, ordinary=facet == "plain",
                        reply="Protect" if facet == "protect" else "Safeguard" if facet in {"magicroom", "embargo"} else "Tail Whip" if facet == "immune" else "Leer")
        self.rebuild()
        self.rebuild()
        battle = self.session.battle
        battle.rng = random.Random(12)
        before = self.observation()
        targets = [mon for part in battle.participants for mon in part.active]
        hp = [mon.hp for mon in targets]
        if facet in {"checkpoint_fault", "payment_fault"}:
            start = len(self.player.messages)
            original = self.session.storage.set
            begin = ZMoves.begin.__func__
            def fail_save(name, value):
                """Fail only after this turn's real effects/owned synchronization."""
                if name == "data":
                    raise RuntimeError("two-source Z checkpoint fault")
                return original(name, value)
            def fail_payment(cls, *args):
                """Fail after the actual source PP and side-budget payment."""
                begin(cls, *args)
                raise RuntimeError("two-source Z payment fault")
            fault = patch.object(self.session.storage, "set", side_effect=fail_save) if facet == "checkpoint_fault" else patch.object(ZMoves, "begin", classmethod(fail_payment))
            with fault, self.assertRaisesRegex(RuntimeError, "two-source Z"):
                self.session.execute_persistent_turn()
            self.assertEqual(self.observation(), before)
            self.assertFalse(any("unleashed" in str(m) for m in self.player.messages[start:]))
        self.session.execute_persistent_turn()
        targets = [mon for part in self.session.battle.participants for mon in part.active]
        damage = [old - mon.hp for old, mon in zip(hp, targets)]
        used = facet != "sleep"
        z_used = used and facet != "plain"
        self.assertEqual(self.session.battle.z_used, {"A"} if z_used else set())
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, pp - int(used))
        if facet in {"sleep", "immune"}:
            self.assertTrue(all(value == 0 for value in damage))
        else:
            self.assertGreater(damage[1 if captured else 2], 0)
        if not captured and facet != "plain":
            self.assertEqual(damage[:2], [0, 0])
            self.assertEqual(damage[3], 0)
        if facet == "plain" and source == "Surf":
            self.assertGreater(damage[1], 0)
            self.assertGreater(damage[3], 0)
        if facet != "plain":
            self.assertFalse(targets[1 if captured else 2].status)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        outcome = {"case": self._testMethodName, "event": "accepted-two-source-effect", "item": item,
                   "source": source, "facet": facet, "damage_by_active_actor": damage,
                   "pp_before": pp, "pp_after": ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp,
                   "side_use": sorted(self.session.battle.z_used), "before": before, "after": self.observation()}
        core.EVIDENCE.append(outcome)
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if z_used else set())
        self.session.end()
        self.session = None
        self.assertEqual(normalize_name(core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item), normalize_name(item))
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        core.EVIDENCE.append({"case": self._testMethodName, "event": "accepted-end-unhold",
                              "item": item, "source": source, "facet": facet, "after": self.observation()})
        return damage[1 if captured else 2]


FACETS = ("native", "active", "protect", "sleep", "immune", "plain", "zero_pp", "missing", "wrong_crystal",
          "invalid_target", "invalid_source", "transformed", "wrong_runtime", "checkpoint_fault", "payment_fault", "magicroom", "embargo")
for pair in PAIRS:
    for facet in FACETS:
        def test(self, pair=pair, facet=facet):
            """Verify one independent ordinary declaration and persisted result."""
            self.flow(pair, facet)
        setattr(ExistingZSourceCases, "test_" + normalize_name(pair[0]) + "_" + facet, test)

if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_zmove, cmd_battle_item, cmd_learn_evolve, cmd_movesets
        core.acquisition.COMMANDS.update({
            "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
            "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
            "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
            "movesets": (cmd_movesets, cmd_movesets.CmdMovesets)})
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(ExistingZSourceCases))
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(json.dumps(core.EVIDENCE, indent=2, default=str)+"\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())

