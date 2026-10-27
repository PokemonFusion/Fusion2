"""Paid mint preferences through ordinary source/use and fresh owned consumers."""

import json
import os
import random
from pathlib import Path
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition
import exp_candy_cases as progression

EVIDENCE = []


class NatureMintCases(unittest.TestCase):
    """Use genuine finite purchases and field commands; capture client transport only."""

    tearDown = acquisition.AcquisitionCases.tearDown
    native = acquisition.AcquisitionCases.native
    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply
    race = progression.ExpCandyCases.race

    def setUp(self):
        """Keep setup separate from purchases, including a nonneutral genetic Nature."""
        acquisition.AcquisitionCases.setUp(self)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nature="Jolly",
            current_hp=1,
            friendship=203,
            status="psn",
            flags=["mint-preserved"],
            held_item="Leftovers",
        )
        self.refresh()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=get_max_hp(self.mon) - 7)
        for player in self.players:
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.room.pk)
        self.room.db.store_buy_only = True
        self.room.db.store_inventory = {
            name + " Mint": {"price": 20000, "quantity": 2} for name in NatureTraining.mint_names
        }

    def refresh(self):
        """Independently load all saved scalar fields and discard old stat caches."""
        FieldMedicineUse._refresh(
            self.mon, OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        )
        return self.mon

    def reconnect(self):
        """Open a new connection and reconstruct transport from the same owned records."""
        from django.db import connection
        from pokemon.models.storage import UserStorage
        from pokemon.services.ownership import fresh_owned

        character, identifier = self.player.character, self.player.pk
        character.attributes.reset_cache()
        ObjectDB.flush_cached_instance(character)
        OwnedPokemon.flush_cached_instance(self.mon)
        connection.close()
        self.player = acquisition.AcquisitionPlayer(
            ObjectDB.objects.get(pk=identifier),
            Trainer.objects.get(user_id=identifier),
            UserStorage.objects.get(user_id=identifier),
        )
        self.player.pk, self.player.location = identifier, self.room
        self.players[0] = self.player
        self.mon = fresh_owned(self.mon.pk)
        if hasattr(self, "move"):
            self.player.move_to = lambda destination, *args, **kwargs: self.move(
                self.player, destination
            )

    def state(self):
        """Read inventory, genetics, training, custody, move knowledge and exact PP."""
        result = acquisition.AcquisitionCases.state(self)
        result.update(
            learner=OwnedPokemon.objects.filter(pk=self.mon.pk).values().get(),
            placements=list(PokemonPlacement.objects.filter(pokemon=self.mon).values()),
            learned=list(self.mon.learned_moves.order_by("pk").values()),
            sets=list(
                MovesetSlot.objects.filter(moveset__pokemon=self.mon).order_by("pk").values()
            ),
            boosts=list(MovePPBoost.objects.filter(pokemon=self.mon).order_by("pk").values()),
        )
        return result

    def buy(self, item):
        """Pay authored price through the actual store/menu and discover it in inventory."""
        before = self.state()
        quantity = self.player.trainer.get_item_quantity(item)
        self.command("store")
        for text in ("1", item + " 1", "back", "q"):
            self.reply(text)
        after = self.state()
        self.assertEqual(self.player.trainer.get_item_quantity(item), quantity + 1)
        self.assertEqual(after["wallet"], before["wallet"] - 20000)
        self.assertEqual(after["stock"][item]["quantity"], before["stock"][item]["quantity"] - 1)
        self.assertIn(item, self.command("inventory"))

    def use(self, item, target="3"):
        """Retain actual parser input/output and fresh SQL before/after state."""
        before, offset = self.state(), len(self.player.messages)
        self.command("use", item + "=" + target)
        after = self.state()
        EVIDENCE.append(
            dict(
                case=self.id(),
                command="+use " + item + "=" + target,
                before=before,
                after=after,
                messages=self.player.messages[offset:],
            )
        )
        return before, after

    def assert_preserved(self, before, after):
        """Only the overlay, HP adjustment and one inventory debit may change."""
        for field, value in before["learner"].items():
            if field not in {"trained_stat_nature", "current_hp"}:
                self.assertEqual(after["learner"][field], value, field)
        for field in ("placements", "learned", "sets", "boosts", "pp", "wallet", "stock"):
            self.assertEqual(after[field], before[field], field)

    def assert_battle(self):
        """Rebuild an ordinary battle from saved training, run a turn, and clean it up."""
        expected, saved = get_stats(self.refresh()), self.state()["learner"]
        self.session = acquisition.BattleSession(self.player)
        foe = acquisition.create_battle_pokemon(
            "Magikarp", 100, is_wild=True, move_names=["Splash"]
        )
        self.session._track_temp_opponent_team([foe])
        self.session._select_opponent = lambda: (
            foe,
            "Mint fixture Magikarp",
            acquisition.BattleType.WILD,
            "Mint stats",
        )
        self.session.start()
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual({key: getattr(holder.base_stats, key) for key in expected}, expected)
        self.assertEqual(holder.nature, saved["nature"])
        self.assertEqual(holder.trained_stat_nature, saved["trained_stat_nature"])
        turn = self.session.battle.turn_count
        self.command("attack", "Tackle")
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        self.assertFalse(getattr(self.session.battle, "_callback_failures", []))
        self.session.end()
        self.session = None
        self.assertEqual(self.state()["learner"]["nature"], saved["nature"])
        self.assertEqual(
            self.state()["learner"]["trained_stat_nature"], saved["trained_stat_nature"]
        )

    def flow(self, nature):
        """Pay once for every non-equivalent preference, reconnect and use its real stats."""
        if nature == "Jolly":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(nature="Adamant")
        self.buy(nature + " Mint")
        before, rejected = self.use(nature + " Mint", "99")
        self.assertEqual(rejected, before)
        from django.db import transaction

        original = Trainer.remove_item

        def partial(trainer, *args):
            """Exercise the real paid write before refusing this exact mint."""
            original(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.use(nature + " Mint")
        self.assertEqual(self.state(), before)
        with self.assertRaisesRegex(RuntimeError, "outer per-mint"):
            with transaction.atomic():
                self.use(nature + " Mint")
                raise RuntimeError("outer per-mint")
        self.assertEqual(self.state(), before)
        before, after = self.use(nature + " Mint")
        self.assertEqual(after["learner"]["trained_stat_nature"], nature, self.player.messages[-4:])
        self.assertEqual(self.player.trainer.get_item_quantity(nature + " Mint"), 0)
        self.assert_preserved(before, after)
        self.reconnect()
        self.assertEqual(self.state(), after)
        self.assertEqual(get_stats(self.refresh()), get_stats(self.mon))
        self.assert_battle()
        # A second paid copy is useful stock, but identical modifiers never debit it.
        if not isinstance(self, NatureMintSourceCases):
            self.buy(nature + " Mint")
            before, after = self.use(nature + " Mint")
            self.assertEqual(after, before)

    def test_equivalent_genetics_and_repeated_training_do_not_spend(self):
        """All five neutral genetics reject Serious; identical paid modifiers reject repeats."""
        self.buy("Serious Mint")
        for genetic in ("Hardy", "Docile", "Serious", "Bashful", "Quirky"):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                nature=genetic, trained_stat_nature=None
            )
            before, after = self.use("Serious Mint")
            self.assertEqual(after, before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(nature="Adamant")
        self.use("Serious Mint")
        self.buy("Serious Mint")
        before, after = self.use("Serious Mint")
        self.assertEqual(after, before)

    def test_targets_selectors_eggs_boxes_and_ambiguous_names(self):
        """Shared field guards refuse before any paid overlay or inventory write."""
        self.buy("Adamant Mint")
        for target in ("", "99", "party", "Missing", "3/Atk", str(self.players[1].pk)):
            before, after = self.use("Adamant Mint", target)
            self.assertEqual(after, before)
        self.native("Mew", 4)
        before, after = self.use("Adamant Mint", "Mew")
        self.assertEqual(after, before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        before, after = self.use("Adamant Mint")
        self.assertEqual(after, before)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        PlacementService(self.player.storage).to_box(self.mon)
        before, after = self.use("Adamant Mint", str(self.mon.pk))
        self.assertEqual(after, before)

    def test_current_fusion_and_stale_fusion_handler(self):
        """Read the current stored Fusion identity, never an obsolete Attribute cache."""
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.buy("Modest Mint")
        before, after = self.use("Modest Mint", "fusion")
        self.assertEqual(after, before)
        self.player.db.fusion_id = str(self.mon.pk)
        self.assertEqual(
            self.use("Modest Mint", "fusion")[1]["learner"]["trained_stat_nature"], "Modest"
        )
        self.buy("Adamant Mint")
        self.player.character.attributes.add("fusion_id", "")
        before, after = self.use("Adamant Mint", "fusion")
        self.assertEqual(after, before)

    def test_fainted_and_low_hp_hyper_training_remain_independent(self):
        """Mints neither revive nor kill, nor edit actual genetic IVs/Hyper Training flags."""
        for hp, name in ((0, "Adamant"), (1, "Modest")):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                current_hp=hp, flags=["mint-preserved", "hypertrained:attack"]
            )
            self.buy(name + " Mint")
            before, after = self.use(name + " Mint")
            self.assertEqual(after["learner"]["current_hp"], hp)
            self.assert_preserved(before, after)

    def test_invalid_saved_genetics_hp_and_training_refuse(self):
        """No malformed saved inputs are repaired with a purchased mint."""
        self.buy("Adamant Mint")
        for fields in ({"nature": ""}, {"nature": "invented"}, {"current_hp": 999999}):
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                nature="Jolly",
                current_hp=1,
                **{
                    key: value
                    for key, value in fields.items()
                    if key not in {"nature", "current_hp"}
                },
            )
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(**fields)
            before, after = self.use("Adamant Mint")
            self.assertEqual(after, before)
        # Actual schema refuses invalid overlays rather than permitting a repair route.
        from django.db import IntegrityError, transaction

        for value in ("invented", "Hardy", "adamant"):
            with self.assertRaises(IntegrityError), transaction.atomic():
                OwnedPokemon.objects.filter(pk=self.mon.pk).update(trained_stat_nature=value)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(current_hp=-1)

    def test_battle_rejection_and_stale_saved_owner(self):
        """A battle lock and a changed source owner cannot consume a field item."""
        self.buy("Adamant Mint")
        self.player.db.battle_lock = "fixture-active"
        before, after = self.use("Adamant Mint")
        self.assertEqual(after, before)
        self.player.db.battle_lock = None
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(trainer_id=self.players[1].trainer.pk)
        before, after = self.use("Adamant Mint")
        self.assertEqual(after, before)

    def test_partial_debit_and_post_save_failure_roll_back(self):
        """Run actual writes before injecting errors at each paid boundary."""
        self.buy("Adamant Mint")
        before, original = self.state(), Trainer.remove_item

        def partial(trainer, *args):
            """Debit for real before reporting a failed spend."""
            original(trainer, *args)
            return False

        with patch.object(Trainer, "remove_item", partial):
            self.use("Adamant Mint")
        self.assertEqual(self.state(), before)
        save = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Raise after a real SQL overlay/HP save."""
            save(pokemon, *args, **kwargs)
            raise RuntimeError("post-mint fixture")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            with self.assertRaisesRegex(RuntimeError, "post-mint"):
                self.use("Adamant Mint")
        self.assertEqual(self.state(), before)

    def test_outer_rollback_does_not_publish_success_or_cached_training(self):
        """A containing operation can abort safely after the service returns success."""
        from django.db import transaction

        self.buy("Adamant Mint")
        before, offset = self.state(), len(self.player.messages)
        with self.assertRaisesRegex(RuntimeError, "outer mint"):
            with transaction.atomic():
                self.use("Adamant Mint")
                raise RuntimeError("outer mint")
        self.assertEqual(self.state(), before)
        self.assertFalse(
            any("mint stat preference is" in str(text) for text in self.player.messages[offset:])
        )
        self.assertIsNone(self.refresh().trained_stat_nature)

    def test_owned_legacy_checkpoint_recovers_current_training_and_refuses_mismatch(self):
        """An old owned checkpoint reads saved training; conflicting new state fails visibly."""
        from pokemon.battle.battledata import Pokemon
        from pokemon.nature_training import NatureTrainingError
        from utils.pokemon_utils import build_battle_pokemon_from_model

        self.buy("Modest Mint")
        self.use("Modest Mint")
        pokemon = build_battle_pokemon_from_model(self.refresh())
        state = pokemon.to_dict()
        state.pop("trained_stat_nature")
        restored = Pokemon.from_dict(state)
        self.assertEqual((restored.nature, restored.trained_stat_nature), ("Jolly", "Modest"))
        state["trained_stat_nature"] = "Adamant"
        with self.assertRaises(NatureTrainingError):
            Pokemon.from_dict(state)

    def test_actual_fusion_display_uses_trained_stats_and_separate_labels(self):
        """Party and trainer-sheet adapters read the same current owned Fusion."""
        from utils.display import _active_fusion_sheet, display_pokemon_sheet
        from utils.party_view import PartyView
        from utils.fusion import get_active_fusion_pokemon
        from utils.pokemon_utils import build_battle_pokemon_from_model

        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.db.fusion_id = str(self.mon.pk)
        self.player.db.fusion_species = "Mew"
        self.buy("Modest Mint")
        self.use("Modest Mint", "fusion")
        active = get_active_fusion_pokemon(self.player.character)
        battle = build_battle_pokemon_from_model(active)
        expected = {
            name: battle.getStat(key, True, True)
            for name, key in (
                ("hp", "hp"),
                ("attack", "atk"),
                ("defense", "def"),
                ("special_attack", "spa"),
                ("special_defense", "spd"),
                ("speed", "spe"),
            )
        }
        display = PartyView._fusion_display(active, self.player.db)
        self.assertEqual(get_stats(display), expected)
        self.assertEqual((display.nature, display.trained_stat_nature), ("Jolly", "Modest"))
        sheet = _active_fusion_sheet(self.player.character)
        self.assertEqual(sheet.stats, expected)
        self.assertEqual((sheet.nature, sheet.trained_stat_nature), ("Jolly", "Modest"))
        text = display_pokemon_sheet(self.player, self.mon)
        self.assertIn("Mint stats", text)
        self.assertIn("Modest", text)
        self.assertIn("genetic Nature remains Jolly", text)

    def test_everstone_plan_keeps_genetic_nature(self):
        """Use a paid preference then actual breeding rules for an Everstone parent."""
        from pokemon.services.breeding_rules import BreedingRules

        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Eevee", 3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            nature="Jolly", gender="F", held_item="Everstone"
        )
        father = self.native("Eevee", 4)
        OwnedPokemon.objects.filter(pk=father.pk).update(nature="Bold", gender="M")
        self.buy("Adamant Mint")
        self.use("Adamant Mint")
        FieldMedicineUse._refresh(father, OwnedPokemon.objects.filter(pk=father.pk).values().get())
        plan = BreedingRules.plan(self.refresh(), father, [[], []], rng=random.Random(77))
        self.assertEqual(plan["nature"], "Jolly")
        self.assertNotIn("trained_stat_nature", plan)

    def test_actual_evolution_keeps_genetic_toxtricity_branch(self):
        """Adamant training cannot turn a genetic Timid Toxel into the Amped form."""
        PlacementService(self.player.storage).to_box(self.mon)
        self.mon = self.native("Toxel", 3)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(nature="Timid")
        self.buy("Adamant Mint")
        self.use("Adamant Mint")
        self.command("evolve", str(self.mon.pk))
        row = self.state()["learner"]
        self.assertEqual(row["species"], "Toxtricity-Low-Key", self.player.messages[-4:])
        self.assertEqual(row["nature"], "Timid")
        self.assertEqual(row["trained_stat_nature"], "Adamant")


class NatureMintSourceCases(NatureMintCases):
    """The optional authored counter is a finite, idempotent public route in QA only."""

    def move(self, player, destination):
        """Adapt client transport around the real tagged character's room movement."""
        moved = player.character.move_to(destination, quiet=True, move_hooks=False)
        if moved:
            player.location = destination
        return moved

    def travel(self, key):
        """Traverse the actual authored Exit as an ordinary player."""
        exit_object = ObjectDB.objects.get(db_location_id=self.player.location.pk, db_key=key)
        command = exit_object.exit_command()
        command.caller, command.obj, command.args = self.player, exit_object, ""
        command.func()
        self.assertEqual(
            ObjectDB.objects.filter(pk=self.player.pk)
            .values_list("db_location_id", flat=True)
            .get(),
            exit_object.db_destination_id,
        )

    def setUp(self):
        """Install only in this random-schema fixture and prove the actual Exit links."""
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter

        super().setUp()
        self.counter = ItemCounter("world/nature_mint_counter.json")
        self.hub = create_object(
            "typeclasses.rooms.FusionRoom", key="mint-private-hub", nohome=True
        )
        self.room = self.counter.install(self.hub)
        self.addCleanup(self.remove_counter)
        for player in self.players:
            player.location = self.hub
            ObjectDB.objects.filter(pk=player.pk).update(db_location_id=self.hub.pk)
            player.move_to = lambda destination, *args, _player=player, **kwargs: self.move(
                _player, destination
            )

    def remove_counter(self):
        """Remove only this fixture's exact three authored objects before the next case."""
        from pokemon.services.battle_rewards import BattleRewards

        marker = "counter_" + self.counter.recipe()["key"]
        receipt = BattleRewards.stored_attribute(self.hub, marker)
        if receipt:
            ObjectDB.objects.filter(
                pk__in=[receipt["room"], receipt["entrance"], receipt["return_exit"]]
            ).delete()
            self.hub.attributes.remove(marker)

    def buy(self, item):
        """Traverse the real normal mints exit before paying the finite authored price."""
        if self.player.location.pk == self.hub.pk:
            self.travel("mints")
        super().buy(item)


def add_flow(nature):
    """Count every named mint's acquire-to-use/reconnect/battle independently."""

    def test(self):
        """A paid exact preference survives all normal stat reconstruction routes."""
        self.flow(nature)

    setattr(NatureMintCases, "test_paid_" + nature, test)


def add_race(nature):
    """One final copy can produce only one useful paid change on separate connections."""

    def test(self):
        """Race two real commands at the same owned target and finite bag copy."""
        if nature == "Jolly":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(nature="Adamant")
        self.buy(nature + " Mint")
        self.race(lambda: self.use(nature + " Mint"), lambda: self.use(nature + " Mint"))
        self.assertEqual(self.state()["learner"]["trained_stat_nature"], nature)
        self.assertEqual(self.player.trainer.get_item_quantity(nature + " Mint"), 0)

    setattr(NatureMintCases, "test_final_copy_" + nature, test)


for name in ("Adamant", "Bold", "Modest", "Calm", "Timid"):

    def source(self, selected=name):
        """Each source category funds a useful mint, is not refilled, and has a return exit."""
        self.flow(selected)
        before, count = self.state(), ObjectDB.objects.count()
        self.assertEqual(self.counter.install(self.hub).pk, self.room.pk)
        self.assertEqual(self.state(), before)
        self.assertEqual(ObjectDB.objects.count(), count)
        self.travel("back")

    setattr(NatureMintSourceCases, "test_source_" + name, source)
# Do not repeat unrelated inherited tests using single-copy source stock.
for name, function in list(vars(NatureMintCases).items()):
    if name.startswith("test_"):
        setattr(NatureMintSourceCases, name, None)
if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_or_create(app_label="objects", model="objectdb")
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import MovePPBoost, MovesetSlot
        from pokemon.models.storage import PokemonPlacement
        from pokemon.models.trainer import Trainer
        from pokemon.nature_training import NatureTraining
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.placement import PlacementService

        for name in NatureTraining.mint_names:
            add_flow(name)
            add_race(name)
        # The subclass inherited dynamic tests too; keep source tests independent.
        for name in NatureTraining.mint_names:
            setattr(NatureMintSourceCases, "test_paid_" + name, None)
            setattr(NatureMintSourceCases, "test_final_copy_" + name, None)
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.TestSuite(
                    [
                        unittest.defaultTestLoader.loadTestsFromTestCase(NatureMintCases),
                        unittest.defaultTestLoader.loadTestsFromTestCase(NatureMintSourceCases),
                    ]
                )
            )
        finally:
            if os.environ.get("PF2_NATURE_MINT_EVIDENCE"):
                Path(os.environ["PF2_NATURE_MINT_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
