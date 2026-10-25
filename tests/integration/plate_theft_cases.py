"""Ordinary owned-player Plate removal commands in disposable PostgreSQL."""

import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
import incense_cases as transport
import native_stat_item_cases as native_transport


EVIDENCE = transport.EVIDENCE
PLATES = (
    "Draco Plate", "Dread Plate", "Earth Plate", "Fist Plate", "Flame Plate",
    "Icicle Plate", "Insect Plate", "Iron Plate", "Meadow Plate", "Mind Plate",
    "Pixie Plate", "Sky Plate", "Splash Plate", "Spooky Plate", "Stone Plate",
    "Toxic Plate", "Zap Plate",
)


class PlateTheftCases(unittest.TestCase):
    """Pair actual nickname, equip, transfer and durable battle checkpoints."""

    fixture_tag = "plate-855"
    native_family = "Arceus"
    native_abilities = {"Arceus": "Multitype", "Mew": "Synchronize", "Hypno": "Insomnia",
                        "Gastrodon": "Sticky Hold"}

    command = transport.IncenseCases.command
    snapshot = transport.IncenseCases.snapshot
    hold = transport.IncenseCases.hold
    saved_item = transport.IncenseCases.saved_item
    stop = transport.IncenseCases.stop
    rebuild = transport.IncenseCases.rebuild
    turn = native_transport.NativeStatItemCases.turn
    tearDown = native_transport.NativeStatItemCases.tearDown

    def setUp(self):
        """Create separate tagged ordinary characters, never an existing session."""
        room = ObjectDB.objects.create(db_key=self.fixture_tag + "-room-" + uuid4().hex)
        self.room = SimpleNamespace(
            id=room.pk, pk=room.pk, key=room.key, db=room.db, ndb=room.ndb,
            attributes=room.attributes, contents=[],
        )
        self.players, self.owned, self.session = [], [], None
        for _ in range(2):
            character = ObjectDB.objects.create(
                db_key=self.fixture_tag + "-player-" + uuid4().hex, db_typeclass_path="pokemon.user.User",
            )
            character.permissions.add("Player")
            player = transport.IncensePlayer(character, character.trainer, character.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
        self.player = self.players[0]
        self.room.contents = self.players
        self.search = patch(
            "pokemon.battle.battleinstance.search_object",
            lambda query: [p for p in self.players if str(p.id) == str(query).lstrip("#")],
        )
        self.search.start()

    def capture(self, side, species, nickname, moves):
        """Separate tagged source setup from real capture nickname-menu inputs."""
        player = self.players[side]
        ability = self.native_abilities[species]
        encounter = create_encounter_pokemon(
            species=species, level=50, source_kind="wild", ability=ability,
            nature="Bold", ivs=[0] * 6, evs=[252, 0, 252, 0, 0, 0],
            current_hp=1, move_names=moves,
        )
        target = Pokemon(species, level=50, hp=1, max_hp=get_max_hp(encounter),
                         model_id="encounter:" + str(encounter.pk))
        result = finalize_wild_capture(target_poke=target, player=player, trainer=player.trainer)
        mon = OwnedPokemon.objects.get(pk=result.owned_pokemon_id.split(":", 1)[1])
        self.owned.append(mon)
        PlacementService(player.storage).to_party(mon, slot=3)
        self.assertTrue(start_capture_nickname(player))
        inputs = ["no"] if nickname is None else ["yes", nickname]
        start = len(player.messages)
        for value in inputs:
            command = CmdEvMenuNode()
            command.caller, command.raw_string, command.session = player, value, None
            command.func()
        self.assertEqual(CaptureNicknames(player).pending(), [])
        self.assertIsNone(player.ndb._evmenu)
        self.assertEqual(OwnedPokemon.objects.filter(pk=mon.pk).values_list("nickname", flat=True).get(), nickname or "")
        EVIDENCE.append({
            "label": "ordinary-capture-nickname-menu", "item": self.item, "facet": self.facet,
            "side": side, "species": species, "inputs": inputs,
            "messages": player.messages[start:], "after": self.snapshot(),
        })

    def prepare(self, item, facet, move):
        """Give legal moves to native species; grant stock only as labelled setup."""
        self.item, self.facet = item, facet
        native_holder = facet.startswith("native") or facet.endswith("_native")
        native_source = facet.startswith("source_native")
        holder = "Arceus" if native_holder else "Gastrodon" if facet == "sticky" else "Mew"
        source = "Arceus" if native_source else "Hypno" if move == "Switcheroo" else "Mew"
        nickname = None if facet.endswith("default") else (
            "Arceus" if facet in {"foreign", "magic_foreign", "embargo_foreign", "checkpoint_foreign", "sticky"}
            else "Arceus-Imposter" if facet == "prefix" else "Buddy"
        )
        source_name = "Arceus" if facet == "source_foreign" else "Buddy"
        holder_idle = "Rain Dance" if holder == "Gastrodon" else "Safeguard"
        self.idle = holder_idle
        self.capture(0, holder, nickname, [holder_idle, "Surf"])
        source_moves = (
            [move, "Magic Room", "Embargo", "Safeguard"] if source == "Mew"
            else [move, "Magic Room", "Safeguard"] if source == "Hypno"
            else [move, "Safeguard"]
        )
        self.capture(1, source, None if facet == "source_native_default" else source_name, source_moves)
        if facet != "missing":
            self.player.trainer.add_item(item, 2)
        if facet in {"occupied", "swap", "native_swap", "source_native_swap"}:
            self.players[1].trainer.add_item("Shed Shell", 2)
        EVIDENCE.append({
            "label": "separate-fixture-prerequisites", "item": item, "facet": facet,
            "source": "Tagged encounter and production capture finalization; not wild/ball commands",
            "stock_grant": 0 if facet == "missing" else 2,
            "source_item_grant": 2 if facet in {"occupied", "swap", "native_swap", "source_native_swap"} else 0,
            "after": self.snapshot(),
        })

    def items(self):
        """Read SQL and runtime independently; explicit empty slots must survive."""
        saved = [OwnedPokemon.objects.filter(pk=m.pk).values_list("held_item", flat=True).get() for m in self.owned]
        if self.session:
            runtime = [p.active[0] for p in self.session.battle.participants]
            self.assertEqual([EffectContext.key(p.item) for p in runtime], [normalize_name(v) for v in saved])
        # Checkpoint restoration may store the dex identifier's display spelling.
        # Compare canonical item identity; raw SQL strings remain in snapshots.
        return [resolve_dex_entry(ITEMDEX, value).raw["name"] if value else "" for value in saved]

    def start(self):
        """Equip from bags using +hold and start the real persistent PvP lifecycle."""
        for index, mon in enumerate(self.owned):
            OwnedPokemon.flush_cached_instance(mon)
            self.owned[index] = OwnedPokemon.objects.get(pk=mon.pk)
            self.owned[index].heal()
        self.hold(self.item)
        if self.facet in {"occupied", "swap", "native_swap", "source_native_swap"}:
            self.command("hold", "3=Shed Shell", 1)
            self.assertEqual(self.items()[1], "Shed Shell")
        self.session = BattleSession(self.player, self.players[1], rng=random.Random(853))
        self.session.start_pvp()
        self.session.battle.debug = True
        for part, mon in zip(self.session.battle.participants, self.owned):
            self.assertEqual(str(part.active[0].base_species), mon.species)
        holder = self.session.battle.participants[0].active[0]
        if self.owned[0].species != self.native_family:
            self.assertEqual(str(holder.species), self.owned[0].species)
        else:
            self.assertEqual(str(holder.species), resolve_dex_entry(ITEMDEX, self.item).raw["forcedForme"])

    def exercise(self, item, facet, move="Thief"):
        """Check actual effect, PP debit, no bag changes, reconnect and battle end."""
        self.prepare(item, facet, move)
        if facet in {"rollback", "missing"}:
            before, start = self.snapshot(), len(self.player.messages)
            original, injected = OwnedPokemon.save, []

            def fail_held(mon, *args, **kwargs):
                """Fail only this tagged holder's save after the stock debit."""
                if mon.pk == self.owned[0].pk and mon.held_item == item:
                    injected.append(mon.pk)
                    raise RuntimeError(self.fixture_tag + " held-save fault")
                return original(mon, *args, **kwargs)

            with patch.object(OwnedPokemon, "save", fail_held if facet == "rollback" else original):
                self.command("hold", "3=" + item)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(injected, [self.owned[0].pk] if facet == "rollback" else [])
            if facet == "rollback":
                self.assertIn("Unable to change held item; Pokemon and inventory were unchanged.", self.player.messages[start:])
            EVIDENCE.append({"label": "expected-hold-" + facet, "item": item, "facet": facet,
                             "command": "+hold 3=" + item, "injected_failures": len(injected),
                             "before": before, "after": self.snapshot(), "messages": self.player.messages[start:]})
            return
        self.start()
        bag_before = self.snapshot()["bags"]
        if facet.startswith(("magic", "embargo")):
            self.turn(self.idle, "Magic Room" if facet.startswith("magic") else "Embargo")
            self.rebuild()
            self.rebuild()
            self.assertIsNone(EffectContext.item(self.session.battle.participants[0].active[0]))
            self.assertEqual(self.items(), [item, ""])
        holder = self.session.battle.participants[0].active[0]
        hp_before = holder.hp
        slot = next(s for s in self.owned[1].activemoveslot_set.all() if normalize_name(s.move.name) == normalize_name(move))
        pp_before = ActiveMoveslot.objects.get(pk=slot.pk).current_pp
        pp_cost = getattr(self, "removal_pp_cost", 1)
        record = self.turn(self.idle, move, rebuild=facet.startswith("checkpoint"))
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp_before - pp_cost)
        damage = hp_before - self.session.battle.participants[0].active[0].hp
        if move in {"Thief", "Knock Off"}:
            self.assertGreater(damage, 0)
            self.assertLess(damage, hp_before)
        protected = facet.startswith(("native", "source_native")) or facet.endswith("native") or facet in {"sticky", "occupied"}
        source_item = "Shed Shell" if facet in {"occupied", "swap", "native_swap", "source_native_swap"} else ""
        expected = [item, source_item] if protected else ["", source_item] if move == "Knock Off" else [source_item, item]
        self.assertEqual(self.items(), expected, record["messages"])
        self.assertEqual(self.snapshot()["bags"], bag_before)
        before_restore = self.snapshot()
        self.rebuild()
        self.rebuild()
        self.assertEqual(self.items(), expected)
        self.assertEqual(self.snapshot()["bags"], bag_before)
        runtime = [part.active[0].to_dict() for part in self.session.battle.participants]
        self.stop()
        self.assertEqual(self.items(), expected)
        for player, mon in zip(self.players, self.owned):
            self.assertFalse(player.db.in_battle)
            self.assertFalse(player.db.battle_lock)
            saved = OwnedPokemon.objects.filter(pk=mon.pk).values("species", "nickname").get()
            self.assertEqual(saved, {"species": mon.species, "nickname": mon.nickname})
        self.assertEqual(self.snapshot()["bags"], bag_before)
        EVIDENCE.append({
            "label": "accepted-removal-outcome", "item": item, "facet": facet, "move": move,
            "protected": protected, "damage": damage, "pp_before": pp_before,
            "pp_cost": pp_cost,
            "pp_after": ActiveMoveslot.objects.get(pk=slot.pk).current_pp,
            "held_after": expected, "queued_rebuilds": record["queued_rebuilds"],
            "post_turn_rebuilds": 2, "before_restore": before_restore,
            "restored_runtime": runtime, "after_end": self.snapshot(),
            "messages": record["messages"],
        })
        # Return transferred or protected items via ordinary field commands.
        # Knock Off intentionally removed the Plate; it cannot reappear in a bag.
        for side in (0, 1):
            self.command("hold", "3=", side)
        self.assertEqual(self.items(), ["", ""])
        expected_plate_stock = [1, 0] if move == "Knock Off" and not protected else [2, 0] if protected else [1, 1]
        self.assertEqual([p.trainer.get_item_quantity(item) for p in self.players], expected_plate_stock)
        if source_item:
            self.assertEqual(sum(p.trainer.get_item_quantity("Shed Shell") for p in self.players), 2)
        EVIDENCE.append({"label": "ordinary-postbattle-unhold", "item": item, "facet": facet,
                         "plate_stock": expected_plate_stock, "after": self.snapshot()})


def add_case(item, facet, move="Thief"):
    """Keep every exact item/control separately counted and replayable."""
    def test(self):
        """Run the ordinary command route with independent persistence assertions."""
        self.exercise(item, facet, move)
    key = "".join(c for c in (item + facet + move).lower() if c.isalnum())
    setattr(PlateTheftCases, "test_" + key, test)


for item in PLATES:
    for facet in ("foreign_default", "foreign", "prefix", "native_default", "native",
                  "source_foreign", "checkpoint_foreign", "rollback", "missing"):
        add_case(item, facet)
    for facet in ("source_native", "source_native_default"):
        add_case(item, facet, "Trick")  # Arceus legally learns Trick, not Thief.
for move in ("Knock Off", "Trick", "Switcheroo"):
    for facet in ("foreign", "native", "swap", "native_swap"):
        add_case("Flame Plate", facet, move)
add_case("Flame Plate", "source_native_swap", "Trick")
for move in ("Thief", "Knock Off", "Trick", "Switcheroo"):
    for facet in ("magic_foreign", "magic_native"):
        add_case("Flame Plate", facet, move)
for facet in ("embargo_foreign", "embargo_native", "occupied", "sticky"):
    add_case("Flame Plate", facet)


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
        for name in ("ObjectDB", "BattleSession", "battle_handler", "ITEMDEX", "OwnedPokemon",
                     "ActiveMoveslot", "PokemonPlacement", "PlacementService", "User",
                     "COMMANDS", "resolve_dex_entry"):
            setattr(transport, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(PlateTheftCases))
        finally:
            if os.environ.get("PF2_PLATE_THEFT_EVIDENCE"):
                Path(os.environ["PF2_PLATE_THEFT_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
