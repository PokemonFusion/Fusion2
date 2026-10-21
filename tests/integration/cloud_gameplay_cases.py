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

    def test_center_heals_reserved_fusion_hp_status_sleep_and_boosted_pp(self):
        """Active forms heal even with a full party or participation disabled."""
        fusion = self.owned
        self.storage.reserve_for_fusion(fusion)
        self.player.db.fusion_id = str(fusion.pk)
        self.player.db.fusion_species = fusion.species
        for index in range(6):
            self.pokemon(f"Party {index+1}")
        inactive = self.pokemon("Inactive boxed form")
        placements = list(self.storage.placements.order_by("pokemon_id").values())
        inactive.current_hp, inactive.status = 1, "par"
        inactive.save()
        for kind in ("permanent", "temporary"):
            for order in ("normal", "first"):
                for participates in (True, False):
                    with self.subTest(kind=kind, order=order, participates=participates):
                        self.player.db.fusion_kind = kind
                        self.player.db.fusion_battle_order = order
                        self.player.db.fusion_participates = participates
                        fusion.current_hp, fusion.status, fusion.sleep_turns = 1, "slp", 2
                        fusion.save()
                        fusion.activemoveslot_set.update(current_pp=1)
                        fusion.pp_boosts.update_or_create(move=fusion.activemoveslot_set.get().move,
                                                          defaults={"bonus_pp": 3})
                        self.assertIn("fully healed", self.command(CmdHeal))
                        fusion.refresh_from_db()
                        self.assertEqual((fusion.current_hp, fusion.status, fusion.sleep_turns),
                                         (get_max_hp(fusion), "", None))
                        self.assertEqual(fusion.activemoveslot_set.get().current_pp, 28)
                        self.assertEqual(list(self.storage.placements.order_by("pokemon_id").values()), placements)
                        inactive.refresh_from_db()
                        self.assertEqual((inactive.current_hp, inactive.status), (1, "par"))

    def test_center_heals_fusion_only_but_battle_guard_still_blocks_it(self):
        """A reserved form alone is healable without bypassing a battle lock."""
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.owned.current_hp = 1
        self.owned.save()
        self.player.db.battle_lock = 19
        self.assertIn("cannot do that during battle", self.command(CmdHeal))
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.current_hp, 1)
        self.player.db.battle_lock = None
        self.assertIn("fully healed", self.command(CmdHeal))
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.current_hp, get_max_hp(self.owned))

    def test_fusion_overlay_does_not_renumber_the_canonical_party(self):
        """A reserved Fusion uses a free display slot without shifting other members."""
        self.gapped_party()
        self.storage.reserve_for_fusion(self.owned)
        self.player.db.fusion_id = str(self.owned.pk)
        self.player.db.fusion_kind = "permanent"
        self.player.db.fusion_species = "Squirtle"
        text = self.command(CmdSheetPokemon)
        self.assertIn("[YOU / FUSION]", text)
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

    def test_storage_and_moveset_menus_retain_numbered_sheet_slots(self):
        """Real placements with gaps drive both menu labels and their mutations."""
        second, sixth = self.gapped_party()
        text, _ = pokestore.node_deposit(self.player)
        self.assertIn("2. Second Pal", text)
        self.assertIn("6. Sixth Pal", text)
        for invalid in ("0", "1", "3", "7", "-1"):
            self.messages.clear()
            moveset_manager.node_start(self.player, invalid)
            self.assertIn("Invalid choice.", self.messages)
            self.assertIsNone(getattr(self.player.ndb, "ms_pokemon", None))
        moveset_manager.node_start(self.player, "6")
        self.assertEqual(self.player.ndb.ms_pokemon.pk, sixth.pk)
        self.player.deposit_pokemon = lambda pid, box: PokemonUser.deposit_pokemon(self.player, pid, box)
        self.player.get_pokemon_by_id = lambda pid: PokemonUser.get_pokemon_by_id(self.player, pid)
        self.player.get_box = lambda index: PokemonUser.get_box(self.player, index)
        self.player._pokemon_is_in_party = lambda mon: PokemonUser._pokemon_is_in_party(self.player, mon)
        pokestore.node_choose_box(self.player, "1", poke_id=str(sixth.pk))
        self.assertEqual(self.storage.get_party_slots(), [None, second, None, None, None, None])
        self.assertTrue(self.storage.get_stored_pokemon())

    def test_pokemon_sheet_level_progress_and_cap(self):
        """Production cards report zero at the level floor and stop at level 100."""
        for growth in ("medium_fast", "fast", "slow", "medium_slow", "fluctuating", "erratic"):
            with self.subTest(growth=growth):
                floor, ceiling = exp_for_level(70, growth), exp_for_level(71, growth)
                pokemon = SimpleNamespace(name="Progress", species="Squirtle", level=70,
                                          total_exp=floor, growth_rate=growth, hp=1)
                text = parse_ansi(display_pokemon_sheet(self.player, pokemon), strip_ansi=True)
                self.assertIn(f"(0% to next, {ceiling - floor} xp)", text)
                pokemon.total_exp = ceiling - 1
                self.assertIn("(99% to next, 1 xp)", parse_ansi(display_pokemon_sheet(self.player, pokemon), strip_ansi=True))
        self.owned.total_exp = exp_for_level(100, getattr(self.owned, "growth_rate", "medium_fast"))
        self.owned.level = 100
        self.owned.save()
        text = self.command(CmdSheetPokemon, "1")
        self.assertIn("MAX LEVEL", text)
        self.assertNotIn("% to next", text)

    def test_help_examples_execute_supported_field_items(self):
        """Published field-item examples work with actual inventory and moves."""
        self.player.get_active_pokemon_by_slot = lambda slot: PokemonUser.get_active_pokemon_by_slot(self.player, slot)
        self.player.trainer.add_item("PP Up", 1)
        self.assertEqual(self.owned.get_max_pp("Water Gun"), 25)
        self.assertIn("Usage: +use PP Up=", self.command(CmdUseItem, "PP Up"))
        self.assertIn("Choose a move", self.command(CmdUseItem, "PP Up=1"))
        self.assertIn("PP was increased", self.command(CmdUseItem, "1"))
        self.assertEqual(self.player.trainer.get_item_quantity("PP Up"), 0)
        self.assertGreater(self.owned.get_max_pp("Water Gun"), 25)
        self.player.trainer.add_item("PP Max", 1)
        self.assertIn("Choose a move", self.command(CmdUseItem, "PP Max=1"))
        self.assertIn("PP was increased", self.command(CmdUseItem, "Water Gun"))
        self.assertEqual(self.player.trainer.get_item_quantity("PP Max"), 0)
        self.player.trainer.add_item("Rare Candy", 1)
        self.assertIn("grew to level", self.command(CmdUseItem, "Rare Candy=1"))
        self.assertEqual(self.player.trainer.get_item_quantity("Rare Candy"), 0)
        self.player.trainer.add_item("Potion", 1)
        self.owned.current_hp = 1
        self.owned.save(update_fields=["current_hp"])
        text = self.command(CmdUseItem, "Potion=1")
        self.assertIn("Used Potion", text)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.current_hp, min(get_max_hp(self.owned), 21))
        self.assertEqual(self.player.trainer.get_item_quantity("Potion"), 0)
        self.assertIn("temporarily unavailable", self.command(CmdTradePokemon, "anything=anyone"))


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB
        from evennia.utils.ansi import parse_ansi

        with patch.object(evennia, "Command", Command):
            from commands.debug.command import CmdHeal
            from commands.player.cmd_account import CmdTradePokemon
            from commands.player.cmd_inventory import CmdUseItem
            from commands.player.cmd_party import CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheet, CmdSheetPokemon
        from menus import moveset_manager, pokestore
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.stats import exp_for_level
        from pokemon.models.storage import StorageBox, UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService
        from pokemon.user import User as PokemonUser
        from utils.display import display_pokemon_sheet

        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(CloudGameplayCases)
        )
        raise SystemExit(not result.wasSuccessful())
