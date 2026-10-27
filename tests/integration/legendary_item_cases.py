"""Ordinary nickname/equip/battle routes for seven native legendary boosters."""

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
PROFILES = {
    "Adamant Orb": ("Dialga", "Dialga", "Flash Cannon"),
    "Adamant Crystal": ("Dialga", "Dialga-Origin", "Flash Cannon"),
    "Lustrous Orb": ("Palkia", "Palkia", "Surf"),
    "Lustrous Globe": ("Palkia", "Palkia-Origin", "Surf"),
    "Griseous Orb": ("Giratina", "Giratina", "Shadow Ball"),
    "Griseous Core": ("Giratina", "Giratina-Origin", "Shadow Ball"),
    "Soul Dew": ("Latias", "Latias", "Psychic"),
}


class LegendaryItemCases(unittest.TestCase):
    """Reuse accepted player transport while testing actual power consumers."""

    command = transport.IncenseCases.command
    snapshot = transport.IncenseCases.snapshot
    hold = transport.IncenseCases.hold
    saved_item = transport.IncenseCases.saved_item
    stop = transport.IncenseCases.stop
    rebuild = transport.IncenseCases.rebuild
    turn = native_transport.NativeStatItemCases.turn
    tearDown = native_transport.NativeStatItemCases.tearDown

    def setUp(self):
        """Create tagged ordinary players without touching any human session."""
        room = ObjectDB.objects.create(db_key="legendary-item-854-room-" + uuid4().hex)
        self.room = SimpleNamespace(
            id=room.pk,
            pk=room.pk,
            key=room.key,
            db=room.db,
            ndb=room.ndb,
            attributes=room.attributes,
            contents=[],
        )
        self.players, self.owned, self.session = [], [], None
        for _ in range(2):
            character = ObjectDB.objects.create(
                db_key="legendary-item-854-player-" + uuid4().hex,
                db_typeclass_path="pokemon.user.User",
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

    def prepare(self, item, facet):
        """Separate source/stock prerequisites from actual nickname-menu input."""
        self.item, self.facet = item, facet
        native, self.expected_form, self.secondary = PROFILES[item]
        foreign = facet in {"foreign", "prefix", "copied"}
        species = "Mew" if foreign else "Latios" if facet.startswith("latios") else native
        if species == "Latios":
            self.expected_form = species
        ability = (
            "Synchronize"
            if foreign
            else "Levitate" if species in {"Latias", "Latios"} else "Pressure"
        )
        moves = ["Dragon Pulse", self.secondary, "Swift", "Safeguard"]
        if facet == "copied":
            moves = ["Transform", "Dragon Pulse", "Swift", "Safeguard"]
        encounter = create_encounter_pokemon(
            species=species,
            level=50,
            source_kind="wild",
            ability=ability,
            nature="Hardy",
            ivs=[0] * 6,
            evs=[0] * 6,
            current_hp=1,
            move_names=moves,
        )
        target = Pokemon(
            species,
            level=50,
            hp=1,
            max_hp=get_max_hp(encounter),
            model_id="encounter:" + str(encounter.pk),
        )
        result = finalize_wild_capture(
            target_poke=target, player=self.player, trainer=self.player.trainer
        )
        caught = OwnedPokemon.objects.get(pk=result.owned_pokemon_id.split(":", 1)[1])
        foe = native if facet == "copied" else "Mew"
        foe_ability = (
            "Levitate" if foe == "Latias" else "Pressure" if foe != "Mew" else "Synchronize"
        )
        opponent = create_owned_pokemon(
            foe,
            self.players[1].trainer,
            50,
            nature="Calm",
            ability=foe_ability,
            ivs=[0] * 6,
            evs=[252, 0, 0, 0, 252, 0],
            active_move_names=(
                ["Dragon Pulse", "Safeguard"]
                if facet == "copied"
                else ["Safeguard", "Magic Room", "Embargo"]
            ),
        )
        self.owned = [caught, opponent]
        for player, mon in zip(self.players, self.owned):
            PlacementService(player.storage).to_party(mon, slot=3)
        if facet != "missing":
            self.player.trainer.add_item(item, 2)
        EVIDENCE.append(
            {
                "label": "separate-fixture-prerequisites",
                "item": item,
                "facet": facet,
                "native": species,
                "foreign_control": foreign,
                "stock_grant": 0 if facet == "missing" else 2,
                "source": "New tagged encounter plus production capture finalization; not wild/ball-command acquisition",
                "before_nickname": self.snapshot(),
            }
        )
        before = self.snapshot()
        self.assertTrue(start_capture_nickname(self.player))
        nickname = native + ("-Imposter" if facet == "prefix" else "") if foreign else "Buddy"
        inputs = ["no"] if facet == "default" else ["yes", nickname]
        for value in inputs:
            command = CmdEvMenuNode()
            command.caller, command.raw_string, command.session = self.player, value, None
            command.func()
        self.assertIsNone(self.player.ndb._evmenu)
        self.assertEqual(CaptureNicknames(self.player).pending(), [])
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=caught.pk).values_list("nickname", flat=True).get(),
            "" if facet == "default" else nickname,
        )
        EVIDENCE.append(
            {
                "label": "ordinary-capture-nickname-menu",
                "item": item,
                "facet": facet,
                "inputs": inputs,
                "before": before,
                "after": self.snapshot(),
                "messages": list(self.player.messages),
            }
        )

    def start(self, held):
        """Normally equip, enter native forms and retain authoritative owned identity."""
        self.stop()
        for index, mon in enumerate(self.owned):
            OwnedPokemon.flush_cached_instance(mon)
            self.owned[index] = OwnedPokemon.objects.get(pk=mon.pk)
            self.owned[index].heal()
        self.hold(held)
        self.session = BattleSession(self.player, self.players[1], rng=random.Random(853))
        self.session.start_pvp()
        self.session.battle.debug = True
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(str(holder.base_species), self.owned[0].species)
        expected = (
            self.expected_form if held and self.owned[0].species != "Mew" else self.owned[0].species
        )
        self.assertEqual(str(holder.species), expected)
        self.assertEqual(holder.item.raw["name"] if held else None, held or None)
        EVIDENCE.append(
            {
                "label": "native-form-entry",
                "item": self.item,
                "facet": self.facet,
                "held": held,
                "owned_species": self.owned[0].species,
                "owned_nickname": self.owned[0].nickname,
                "runtime": holder.to_dict(),
            }
        )

    def measure(self, held, move):
        """Read normal emitted power, HP and PP without substituting item effects."""
        self.start(held)
        if self.facet in {"magic", "embargo"}:
            self.turn("Safeguard", "Magic Room" if self.facet == "magic" else "Embargo")
            self.rebuild()
            self.rebuild()
            holder = self.session.battle.participants[0].active[0]
            self.assertIsNone(EffectContext.item(holder))
            self.assertEqual(self.saved_item(), held)
        elif self.facet == "copied":
            self.turn("Transform")
            holder = self.session.battle.participants[0].active[0]
            self.assertTrue(holder.transformed)
            self.assertEqual(str(holder.base_species), "Mew")
            self.assertEqual(str(holder.species), PROFILES[self.item][0])
        slot = next(
            slot
            for slot in self.owned[0].activemoveslot_set.all()
            if normalize_name(slot.move.name) == normalize_name(move)
        )
        pp = slot.current_pp
        holder, foe = [part.active[0] for part in self.session.battle.participants]
        hp = foe.hp
        record = self.turn(move, rebuild=self.facet == "checkpoint")
        self.assertEqual(len(record["damage_traces"]), 1, record["messages"])
        trace = record["damage_traces"][0]
        damage = hp - self.session.battle.participants[1].active[0].hp
        self.assertEqual(damage, int(trace[8]))
        self.assertGreater(damage, 0)
        self.assertEqual(trace[7], "False")
        if self.facet != "copied":
            self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)
        self.assertEqual(self.saved_item(), held)
        runtime = [part.active[0].to_dict() for part in self.session.battle.participants]
        self.stop()
        self.assertFalse(self.player.db.in_battle)
        self.assertFalse(self.player.db.battle_lock)
        saved = (
            OwnedPokemon.objects.filter(pk=self.owned[0].pk)
            .values("species", "nickname", "held_item")
            .get()
        )
        self.assertEqual(saved["species"], self.owned[0].species)
        self.assertEqual(saved["held_item"], held)
        EVIDENCE.append(
            {
                "label": "persisted-battle-end",
                "item": self.item,
                "facet": self.facet,
                "saved": saved,
                "after": self.snapshot(),
            }
        )
        return {"power": int(trace[1]), "damage": damage, "trace": trace, "runtime": runtime}

    def exercise(self, item, facet):
        """Pair exact native/foreign/type/suppression/reconnect/rollback controls."""
        self.prepare(item, facet)
        if facet in {"rollback", "missing"}:
            before, start = self.snapshot(), len(self.player.messages)
            injected = []
            original = OwnedPokemon.save

            def fail_held(mon, *args, **kwargs):
                """Inject only this tagged holder's post-debit save boundary."""
                if mon.pk == self.owned[0].pk and mon.held_item == item:
                    injected.append(mon.pk)
                    raise RuntimeError("legendary-item-854 held save fault")
                return original(mon, *args, **kwargs)

            with patch.object(OwnedPokemon, "save", fail_held if facet == "rollback" else original):
                self.command("hold", "3=" + item)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(injected, [self.owned[0].pk] if facet == "rollback" else [])
            if facet == "rollback":
                self.assertIn(
                    "Unable to change held item; Pokemon and inventory were unchanged.",
                    self.player.messages[start:],
                )
            EVIDENCE.append(
                {
                    "label": "expected-hold-" + facet,
                    "item": item,
                    "facet": facet,
                    "command": "+hold 3=" + item,
                    "before": before,
                    "after": self.snapshot(),
                    "injected_save_failures": len(injected),
                    "messages": self.player.messages[start:],
                }
            )
            if facet == "rollback":
                self.hold(item)
                self.hold("")
                self.assertEqual(self.player.trainer.get_item_quantity(item), 2)
            return
        move = (
            self.secondary
            if facet in {"secondary", "latios_secondary"}
            else "Swift" if facet == "nonmatching" else "Dragon Pulse"
        )
        baseline, held = self.measure("", move), self.measure(item, move)
        raw = resolve_dex_entry(MOVEDEX, move).power
        eligible = facet not in {"foreign", "prefix", "copied", "nonmatching", "magic", "embargo"}
        self.assertEqual(baseline["power"], raw)
        self.assertEqual(held["power"], int(raw * 1.2) if eligible else raw)
        if eligible:
            self.assertGreater(held["damage"], baseline["damage"])
        elif facet in {"foreign", "prefix", "copied", "nonmatching"}:
            # Forms can change stats; compare damage only when stats stayed matched.
            if facet != "nonmatching" or self.expected_form == self.owned[0].species:
                self.assertEqual(held["damage"], baseline["damage"])
        EVIDENCE.append(
            {
                "label": "matched-item-outcome",
                "item": item,
                "facet": facet,
                "move": move,
                "baseline": baseline,
                "held": held,
            }
        )


def add_case(item, facet):
    """Give each exact item and acceptance facet a separately counted case."""

    def test(self):
        """Run a normal player transition and retain effect/persistence evidence."""
        self.exercise(item, facet)

    setattr(LegendaryItemCases, "test_" + normalize_key(item) + "_" + facet, test)


def normalize_key(value):
    """Name test methods without importing application bootstrap early."""
    return "".join(char for char in value.lower() if char.isalnum())


for item in PROFILES:
    for facet in (
        "native",
        "secondary",
        "default",
        "foreign",
        "prefix",
        "nonmatching",
        "magic",
        "embargo",
        "checkpoint",
        "copied",
        "rollback",
        "missing",
    ):
        add_case(item, facet)
for facet in ("latios", "latios_secondary"):
    add_case("Soul Dew", facet)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_party, cmd_inventory, cmd_pokedex
        from evennia.objects.models import ObjectDB
        from evennia.utils.evmenu import CmdEvMenuNode
        from menus.capture_nickname import start_capture_nickname
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.effect_context import EffectContext
        from pokemon.battle.handler import battle_handler
        from pokemon.dex import ITEMDEX, MOVEDEX
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import normalize_name, resolve_dex_entry
        from pokemon.services.capture import finalize_wild_capture
        from pokemon.services.capture_nicknames import CaptureNicknames
        from pokemon.services.encounters import create_encounter_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        COMMANDS = {
            "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
            "hold": (cmd_party, cmd_party.CmdSetHoldItem),
            "inventory": (cmd_inventory, cmd_inventory.CmdInventory),
            "itemdex": (cmd_pokedex, cmd_pokedex.CmdItemdexSearch),
        }
        for name in (
            "ObjectDB",
            "BattleSession",
            "battle_handler",
            "ITEMDEX",
            "OwnedPokemon",
            "ActiveMoveslot",
            "PokemonPlacement",
            "PlacementService",
            "User",
            "COMMANDS",
            "resolve_dex_entry",
        ):
            setattr(transport, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(LegendaryItemCases)
            )
        finally:
            if os.environ.get("PF2_LEGENDARY_ITEM_EVIDENCE"):
                Path(os.environ["PF2_LEGENDARY_ITEM_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
