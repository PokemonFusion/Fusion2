"""Authored ordinary hunts/capture/teaching prove native signature access."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from z_signature_cases import SignatureZCases
from pokemon.battle.z_signature_pairs import CAPS
from pokemon.battle.z_profiles import ZProfiles
from pokemon.names import normalize_name


class NativeZCases(unittest.TestCase):
    """Fixture chart/stock setup never substitutes for the ordinary acquisition."""

    command = SignatureZCases.command
    reply = SignatureZCases.reply
    state = SignatureZCases.state
    native = SignatureZCases.native
    buy = SignatureZCases.buy
    record = SignatureZCases.record
    observation = SignatureZCases.observation
    launch = SignatureZCases.launch
    rebuild = SignatureZCases.rebuild
    fixture_native = SignatureZCases.fixture_native
    flow = SignatureZCases.flow

    def setUp(self):
        """Create only ordinary transports, a tagged chart and controlled stock."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """End this fixture's actual session and remove only its SQL schema."""
        core.MegaEvolutionCases.tearDown(self)

    def acquire(self, species, source):
        """Use +hunt, +item, +teach and the real moveset menu without staff input."""
        from pokemon.models.moves import ActiveMoveslot

        self.room.db.allow_hunting = True
        self.room.db.npc_chance, self.room.db.encounter_rate = 0, 100
        self.room.db.hunt_chart = [
            {"name": species, "min_level": 100, "max_level": 100, "weight": 1}
        ]
        self.buy("Master Ball", price=1000, quantity=1)
        before = set(
            core.OwnedPokemon.objects.filter(trainer=self.player.trainer).values_list(
                "pk", flat=True
            )
        )
        self.record("hunt")
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session)
        self.assertEqual(str(self.session.battle.participants[1].active[0].species), species)
        self.record("item", "Master Ball")
        self.assertEqual(self.player.trainer.get_item_quantity("Master Ball"), 0)
        caught = (
            core.OwnedPokemon.objects.filter(trainer=self.player.trainer)
            .exclude(pk__in=before)
            .get()
        )
        self.mons.append(caught)
        self.assertEqual(caught.species, species)
        self.session.end()
        self.session = None
        for placement in self.player.storage.placements.filter(location_type="party", slot=3):
            core.PlacementService(self.player.storage).to_box(placement.pokemon)
        core.PlacementService(self.player.storage).to_party(caught, slot=3)
        self.mon = caught
        self.record("teach", "3=" + source)
        if self.player.ndb._evmenu:
            self.reply("no")
        self.room.db.is_pokemon_center = True
        self.record("movesets")
        self.reply("3")
        self.reply("edit 1")
        self.reply(source)
        self.reply("back")
        self.reply("q")
        slots = list(ActiveMoveslot.objects.filter(pokemon=caught).select_related("move"))
        self.assertEqual(
            [normalize_name(slot.move.name) for slot in slots],
            [normalize_name(source)],
            self.player.messages[-8:],
        )
        core.OwnedPokemon.flush_cached_instance(caught)
        return caught

    def cap(self, species, item="Pikashunium Z", source="Thunderbolt"):
        """This native cap comes from a configured hunt and ordinary capture."""
        profile = ZProfiles.get(item, source)
        caught = self.acquire(species, profile.source)
        self.flow(profile, native=species, captured=caught)


for _species in CAPS:

    def _case(self, species=_species):
        """Qualify this exact cap's native access and paid Z player flow."""
        self.cap(species)

    setattr(NativeZCases, "test_" + normalize_name(_species), _case)

for _species, _item, _source in (
    ("Mimikyu-Totem", "Mimikium Z", "Play Rough"),
    ("Kommo-o-Totem", "Kommonium Z", "Clanging Scales"),
):

    def _case(self, species=_species, item=_item, source=_source):
        """Qualify a Totem through actual authored hunt/capture and source teaching."""
        self.cap(species, item, source)

    setattr(NativeZCases, "test_" + normalize_name(_species), _case)


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
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(NativeZCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
