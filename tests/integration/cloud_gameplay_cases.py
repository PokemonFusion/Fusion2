"""Cloud QA regressions against real models in a disposable PostgreSQL schema."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class CloudGameplayCases(unittest.TestCase):
    """Check command-visible slots, held-item routing and battle healing safety."""

    def setUp(self):
        """Seed one private trainer, storage and injured party member."""
        character = ObjectDB.objects.create(db_key="Cloud regression " + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=character)
        self.messages = []
        self.player = SimpleNamespace(
            id=character.pk, pk=character.pk, key=character.key, db=character.db, ndb=character.ndb,
            storage=self.storage, trainer=trainer, msg=self.messages.append,
            location=SimpleNamespace(db=SimpleNamespace(is_pokemon_center=True)),
        )
        self.owned = self.pokemon("First")

    def pokemon(self, nickname):
        """Create a production model and canonical placement through the factory."""
        pokemon = create_owned_pokemon(
            "Squirtle", self.player.trainer, 5, nature="Hardy", ivs=[0]*6, evs=[0]*6,
            active_move_names=["Water Gun"],
        )
        pokemon.nickname = nickname
        pokemon.save()
        return pokemon

    def command(self, cls, args=""):
        """Run the ordinary command parser and capture its player-facing output."""
        self.messages.clear()
        command = cls()
        command.caller, command.args, command.switches = self.player, args, []
        command.parse()
        command.func()
        return parse_ansi("\n".join(self.messages), strip_ansi=True)

    def gapped_party(self):
        """Leave canonical slots 1 and 3–5 empty, with members at 2 and 6."""
        second, sixth = self.pokemon("Second Pal"), self.pokemon("Sixth Pal")
        service = PlacementService(self.storage)
        box = StorageBox.objects.create(storage=self.storage, name="Regression Box")
        service.to_box(self.owned, box)
        service.to_party(sixth, 6)
        return second, sixth

    def test_center_heal_does_not_mutate_behind_persistent_or_live_battle(self):
        """HP, status and PP stay unchanged while locked; post-battle healing works."""
        self.owned.current_hp, self.owned.status = 3, "par"
        self.owned.save()
        self.owned.activemoveslot_set.update(current_pp=1)
        for lock, runtime in ((17, None), (None, SimpleNamespace(battle_id=17))):
            with self.subTest(lock=lock):
                self.player.db.battle_lock = lock
                self.player.ndb.battle_instance = runtime
                text = self.command(CmdHeal)
                self.assertIn("You cannot do that during battle.", text)
                self.owned.refresh_from_db()
                self.assertEqual((self.owned.current_hp, self.owned.status), (3, "par"))
                self.assertEqual(self.owned.activemoveslot_set.values_list("current_pp", flat=True).get(), 1)
        self.player.db.battle_lock = None
        self.player.ndb.battle_instance = None
        self.assertIn("fully healed", self.command(CmdHeal))
        self.owned.refresh_from_db()
        self.assertEqual((self.owned.current_hp, self.owned.status), (get_max_hp(self.owned), ""))
        self.assertEqual(self.owned.activemoveslot_set.values_list("current_pp", flat=True).get(), 25)

    def test_displayed_slots_match_hold_and_both_numbered_sheets(self):
        """A gap cannot redirect a displayed slot to a different Pokémon."""
        second, sixth = self.gapped_party()
        self.assertEqual(self.storage.get_party_slots(), [None, second, None, None, None, sixth])
        self.assertEqual(self.storage.get_party(), [second, sixth])
        text = self.command(CmdSheetPokemon)
        self.assertIn("2: Second Pal", text)
        self.assertIn("6: Sixth Pal", text)
        self.assertNotIn("1: Second Pal", text)
        self.player.trainer.add_item("Oran Berry", 2)
        self.assertIn("No Pokémon in that slot", self.command(CmdSetHoldItem, "1=Oran Berry"))
        self.assertEqual(self.player.trainer.get_item_quantity("Oran Berry"), 2)
        self.assertIn("Second Pal is now holding Oran Berry", self.command(CmdSetHoldItem, "2=Oran Berry"))
        second.refresh_from_db()
        sixth.refresh_from_db()
        self.assertEqual(second.held_item, "Oran Berry")
        self.assertEqual(sixth.held_item, "")
        for cls in (CmdSheet, CmdSheetPokemon):
            self.assertIn("Second Pal", self.command(cls, "2"))
            self.assertIn("Sixth Pal", self.command(cls, "6"))
            self.assertIn("That slot is empty", self.command(cls, "1"))
        text = self.command(CmdSheetPokemon, "all")
        self.assertIn("Second Pal", text)
        self.assertIn("Sixth Pal", text)

    def test_fusion_overlay_does_not_renumber_the_canonical_party(self):
        """A reserved Fusion uses a free display slot without shifting other members."""
        self.gapped_party()
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.player.db.fusion_species = "Squirtle"
        text = self.command(CmdSheetPokemon)
        self.assertIn("(fusion)", text)
        self.assertIn("2: Second Pal", text)
        self.assertIn("6: Sixth Pal", text)
        self.assertIn("Second Pal", self.command(CmdSheetPokemon, "2"))

    def test_empty_party_stays_empty(self):
        """Six empty positions do not produce a misleading party header."""
        service = PlacementService(self.storage)
        box = StorageBox.objects.create(storage=self.storage, name="Empty Party")
        service.to_box(self.owned, box)
        for cls in (CmdSheet, CmdSheetPokemon):
            self.assertIn("no Pokémon in your party", self.command(cls, "all" if cls is CmdSheetPokemon else "1"))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import parse_ansi

        with patch.object(evennia, "Command", Command):
            from commands.debug.command import CmdHeal
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.storage import StorageBox, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService

        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(CloudGameplayCases)
        )
        raise SystemExit(not result.wasSuccessful())
