"""Real capture/teach/Center/combination/equip preparation before Ultra activation."""

import importlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import necrozma_player_cases as native


class UltraPreparationCases(native.NecrozmaPlayerCases):
    """Native preparation grants no transformation, action, PP or mechanic budget."""

    def prepare(
        self,
        companion,
        *,
        level=50,
        photon_pp=None,
        battle_format="single",
        active_photon=True,
        combine_slot=2,
    ):
        """Capture real bases, teach legitimately, select Photon1, combine source2 and equip."""
        self.acquire_pair(companion, level=level)
        if level >= 50:
            self.record("teach", "3=Photon Geyser")
            if self.player.ndb._evmenu:
                self.reply("1")
            learned = list(self.host.learned_moves.values_list("name", flat=True))
            photon = next(
                (name for name in learned if normalize_name(name) == "photongeyser"), None
            )
            self.assertIsNotNone(photon, self.player.messages[-8:])
            others = [name for name in learned if normalize_name(name) != "photongeyser"][:3]
            self.assertTrue(others)
            self.record("movesets")
            selected = [photon, *others] if active_photon else others
            for reply in ("3", "1", ", ".join(selected), "back", "quit"):
                self.reply(reply)
            self.assertIsNone(self.player.ndb._evmenu, self.player.messages[-8:])
            source = ActiveMoveslot.objects.get(pokemon=self.host, slot=1)
            self.assertEqual(normalize_name(source.move.name) == "photongeyser", active_photon)
        self.combine(slot=combine_slot)
        self.buy("Ultranecrozium Z", price=100, quantity=1)
        self.record("hold", "3=Ultranecrozium Z")
        if photon_pp is not None:
            ActiveMoveslot.objects.filter(pokemon=self.host, slot=1).update(current_pp=photon_pp)
            native.core.EVIDENCE.append(
                dict(event="separate-Photon-PP-prerequisite", current_pp=photon_pp)
            )
        self.launch(battle_format)
        self.participant = self.session.battle.participants[0]
        self.actor = self.participant.active[0]
        self.assertEqual(self.actor.model_id, "owned:" + str(self.host.pk))

    def binding(self):
        """Read under actual fresh owner/storage/source locks without activation."""
        from pokemon.battle.ultra_eligibility import UltraEligibility

        return UltraEligibility.binding(self.session.battle, self.participant, self.actor)

    def positive(self, companion):
        """Both real forms keep a separate active native Photon and reusable crystal."""
        self.prepare(companion)
        before = self.observation()
        binding = self.binding()
        self.assertEqual(binding.photon_slot, 1)
        self.assertEqual(binding.pair["slot"], 2)
        self.assertGreater(binding.current_pp, 0)
        self.assertEqual(self.observation(), before)
        self.rebuild()
        self.participant = self.session.battle.participants[0]
        self.actor = self.participant.active[0]
        self.assertEqual(self.binding(), binding)
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.companion.pk).values().get(), self.partner_before
        )
        native.core.EVIDENCE.append(
            dict(
                event="ordinary-ultra-preparation-only",
                companion=companion,
                level=50,
                photon_slot=binding.photon_slot,
                form_slot=binding.pair["slot"],
                current_pp=binding.current_pp,
                capacity=binding.capacity,
                activated=False,
                socket=False,
            )
        )

    def test_dusk_native_level50_preparation_and_restore(self):
        """Existing level50 Photon works for actual Dusk Mane without a72 gate."""
        self.positive("Solgaleo")

    def test_dawn_native_level50_preparation_and_restore(self):
        """Existing level50 Photon works for actual Dawn Wings without a72 gate."""
        self.positive("Lunala")

    def test_below_native_photon_access_is_refused_without_grant_or_refill(self):
        """Actual lower-level captured sources do not gain Photon from the crystal."""
        self.prepare("Solgaleo", level=49)
        before = self.observation()
        with self.assertRaisesRegex(ValueError, "legitimate current native Photon"):
            self.binding()
        self.assertEqual(self.observation(), before)

    def test_zero_pp_is_preparable_and_physical_crystal_suppression_does_not_grant_ability(self):
        """Zero PP can prepare; Magic Room/Embargo do not suppress physical crystal ownership."""
        self.prepare("Lunala", photon_pp=0)
        self.rebuild()
        self.participant = self.session.battle.participants[0]
        self.actor = self.participant.active[0]
        self.assertEqual(self.binding().current_pp, 0)
        self.session.battle.field.pseudo_weather["magicroom"] = {"duration": 5}
        self.actor.volatiles["embargo"] = {"duration": 5}
        before = self.observation()
        self.assertEqual(self.binding().current_pp, 0)
        self.assertEqual(self.observation(), before)
        with patch.object(self.actor, "ability_suppressed", True):
            with self.assertRaisesRegex(ValueError, "native Prism Armor"):
                self.binding()

    def test_copied_replaced_and_legacy_unrecorded_abilities_do_not_unlock_ultra(self):
        """Actual ability replacement marks provenance, retained through serialization."""
        self.prepare("Solgaleo")
        self.binding()
        for value in (None, "changed"):
            with patch.object(self.actor, "native_ability_provenance", value):
                with self.assertRaisesRegex(ValueError, "native Prism Armor"):
                    self.binding()
        foe = self.session.battle.participants[1].active[0]
        self.actor.setAbility("Synchronize", battle=self.session.battle, source=foe)
        self.actor.setAbility("Prism Armor", battle=self.session.battle, source=foe)
        self.assertEqual(self.actor.native_ability_provenance, "changed")
        with self.assertRaisesRegex(ValueError, "native Prism Armor"):
            self.binding()
        self.rebuild()
        self.participant = self.session.battle.participants[0]
        self.actor = self.participant.active[0]
        self.assertEqual(self.actor.native_ability_provenance, "changed")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        native.core.load_runtime()
        from django.apps import apps
        from django.db import connection
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaResource
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import normalize_name
        from pokemon.services.placement_audit import audit_placements_v3

        with connection.schema_editor() as editor:
            importlib.import_module("pokemon.migrations.0041_placement_integrity_triggers").install(
                apps, editor
            )
            importlib.import_module("pokemon.migrations.0058_necrozma_integrity").install(
                apps, editor
            )
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (
                cmd_necrozma,
                cmd_battle_zmove,
                cmd_battle_concede,
                cmd_movesets,
                cmd_learn_evolve,
            )
        native.core.acquisition.COMMANDS.update(
            {
                "necrozma": (cmd_necrozma, cmd_necrozma.CmdNecrozma),
                "zmove": (cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove),
                "concede": (cmd_battle_concede, cmd_battle_concede.CmdBattleConcede),
                "movesets": (cmd_movesets, cmd_movesets.CmdMovesets),
                "teach": (cmd_learn_evolve, cmd_learn_evolve.CmdTeachMove),
            }
        )
        for name in (
            "apps",
            "OwnedPokemon",
            "ActiveMoveslot",
            "NecrozmaCombination",
            "NecrozmaResource",
            "PokemonPlacement",
            "audit_placements_v3",
        ):
            setattr(native, name, globals()[name])
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(UltraPreparationCases)
            )
        finally:
            if os.environ.get("PF2_ULTRA_EVIDENCE"):
                Path(os.environ["PF2_ULTRA_EVIDENCE"]).write_text(
                    json.dumps(native.core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
