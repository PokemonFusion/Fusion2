"""Seven special-item removal rules through owned-player commands and SQL."""

import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import incense_cases as transport
import plate_theft_cases as removal


EVIDENCE = transport.EVIDENCE
PROFILES = {
    "Adamant Crystal": ("Dialga", "Dialga-Origin", "Pressure"),
    "Griseous Core": ("Giratina", "Giratina-Origin", "Pressure"),
    "Lustrous Globe": ("Palkia", "Palkia-Origin", "Pressure"),
    "Blue Orb": ("Kyogre", "Kyogre-Primal", "Drizzle"),
    "Red Orb": ("Groudon", "Groudon-Primal", "Drought"),
    "Rusted Sword": ("Zacian", "Zacian-Crowned", "Intrepid Sword"),
    "Rusted Shield": ("Zamazenta", "Zamazenta-Crowned", "Dauntless Shield"),
}


class OriginPrimalRustedTheftCases(unittest.TestCase):
    """Reuse real commands and conservation assertions without other families."""

    fixture_tag = "special-theft-857"
    native_abilities = {**removal.PlateTheftCases.native_abilities,
                        **{p[0]: p[2] for p in PROFILES.values()}}
    setUp = removal.PlateTheftCases.setUp
    tearDown = removal.PlateTheftCases.tearDown
    capture = removal.PlateTheftCases.capture
    items = removal.PlateTheftCases.items
    command = removal.PlateTheftCases.command
    snapshot = removal.PlateTheftCases.snapshot
    hold = removal.PlateTheftCases.hold
    saved_item = removal.PlateTheftCases.saved_item
    stop = removal.PlateTheftCases.stop
    turn = removal.PlateTheftCases.turn
    exercise = removal.PlateTheftCases.exercise

    @property
    def removal_pp_cost(self):
        """Account for actual native Pressure rather than forcing one-PP fixtures."""
        holder = self.session.battle.participants[0].active[0]
        return 2 if EffectContext.key(EffectContext.ability(holder)) == "pressure" else 1

    def prepare(self, item, facet, move):
        """Use native legal abilities/moves and separately labelled stock setup."""
        self.item, self.facet = item, facet
        self.native_family, self.active_form, _ = PROFILES[item]
        native_holder = facet.startswith("native") or facet.endswith("_native")
        native_source = facet.startswith("source_native")
        holder = self.native_family if native_holder else "Gastrodon" if facet == "sticky" else "Mew"
        source = self.native_family if native_source else "Hypno" if move == "Switcheroo" else "Mew"
        nickname = None if facet.endswith("default") else (
            self.native_family if facet in {"foreign", "magic_foreign", "embargo_foreign", "checkpoint_foreign", "sticky"}
            else self.native_family + "-Imposter" if facet == "prefix" else "Buddy"
        )
        self.idle = "Iron Defense" if holder == "Zacian" else "Rain Dance" if holder == "Gastrodon" else "Safeguard"
        self.capture(0, holder, nickname, [self.idle, "Swift"])
        self.capture(1, source, None if facet == "source_native_default" else
                     self.native_family if facet == "source_foreign" else "Buddy",
                     [move, "Safeguard"] if native_source else
                     [move, "Magic Room", "Embargo", "Safeguard"] if source == "Mew" else
                     [move, "Magic Room", "Safeguard"])
        if facet != "missing":
            self.player.trainer.add_item(item, 2)
        source_stock = 2 if facet in {"occupied", "swap", "native_swap", "source_native_swap"} else 0
        if source_stock:
            self.players[1].trainer.add_item("Shed Shell", source_stock)
        EVIDENCE.append({"label": "separate-fixture-prerequisites", "item": item, "facet": facet,
                         "native_family": self.native_family, "active_form": self.active_form,
                         "source": "Tagged encounter and production capture finalization; not wild/ball commands",
                         "stock_grant": 0 if facet == "missing" else 2,
                         "source_item_grant": source_stock, "after": self.snapshot()})

    def start(self):
        """Equip, enter the real PvP lifecycle and assert all seven form guards."""
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
            expected = self.active_form if mon.species == self.native_family and mon == self.owned[0] else mon.species
            self.assertEqual(str(part.active[0].species), expected)
        if self.owned[0].species == self.native_family:
            holder = self.session.battle.participants[0].active[0]
            ability = EffectContext.ability(holder)
            self.assertTrue(ability.raw)
            if self.native_family in {"Dialga", "Palkia"}:
                self.assertIn("onDeductPP", ability.raw)
            if self.native_family in {"Kyogre", "Groudon"}:
                self.assertEqual(self.session.battle.field.weather,
                                 "primordialsea" if self.native_family == "Kyogre" else "desolateland")
            if self.native_family in {"Zacian", "Zamazenta"}:
                stat = "attack" if self.native_family == "Zacian" else "defense"
                self.assertEqual(holder.boosts[stat], 1)

    def rebuild(self):
        """A checkpoint cannot repair missing callbacks or replay entry bonuses."""
        before = [(str(p.active[0].species), EffectContext.key(p.active[0].ability),
                   dict(p.active[0].boosts)) for p in self.session.battle.participants]
        weather = self.session.battle.field.weather
        removal.PlateTheftCases.rebuild(self)
        after = [(str(p.active[0].species), EffectContext.key(p.active[0].ability),
                  dict(p.active[0].boosts)) for p in self.session.battle.participants]
        self.assertEqual(before, after)
        self.assertEqual(self.session.battle.field.weather, weather)


def add_case(item, facet, move="Thief"):
    """Count each exact item and ordinary acceptance facet separately."""
    def test(self):
        """Verify command targeting, damage, PP, SQL and lifecycle conservation."""
        self.exercise(item, facet, move)
    key = "".join(c for c in (item + facet + move).lower() if c.isalnum())
    setattr(OriginPrimalRustedTheftCases, "test_" + key, test)


for item in PROFILES:
    for facet in ("foreign_default", "foreign", "prefix", "native_default", "native",
                  "source_foreign", "checkpoint_foreign", "rollback", "missing"):
        add_case(item, facet)
    for move in ("Knock Off", "Trick", "Switcheroo"):
        for facet in ("foreign", "native", "swap", "native_swap"):
            add_case(item, facet, move)
    for move in ("Thief", "Knock Off", "Trick", "Switcheroo"):
        for facet in ("magic_foreign", "magic_native"):
            add_case(item, facet, move)
    for facet in ("embargo_foreign", "embargo_native", "occupied", "sticky"):
        add_case(item, facet)
for item in ("Adamant Crystal", "Lustrous Globe"):
    for facet in ("source_native", "source_native_default", "source_native_swap"):
        add_case(item, facet, "Trick")  # Dialga and Palkia legally learn Trick.


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
        for module in (transport, removal):
            for name in ("ObjectDB", "BattleSession", "battle_handler", "ITEMDEX", "OwnedPokemon",
                         "ActiveMoveslot", "PokemonPlacement", "PlacementService", "User",
                         "COMMANDS", "resolve_dex_entry", "CmdEvMenuNode", "start_capture_nickname",
                         "CaptureNicknames", "create_encounter_pokemon", "Pokemon", "get_max_hp",
                         "finalize_wild_capture", "EffectContext", "normalize_name"):
                setattr(module, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(OriginPrimalRustedTheftCases))
        finally:
            if os.environ.get("PF2_ORIGIN_PRIMAL_RUSTED_EVIDENCE"):
                Path(os.environ["PF2_ORIGIN_PRIMAL_RUSTED_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
