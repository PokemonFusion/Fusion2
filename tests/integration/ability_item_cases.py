"""Prove ordinary ability item commands with real disposable PostgreSQL rows."""

import json
import os
import sys
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView

EVIDENCE = []


class AbilityPlayer(PlayerView):
    """Adapt only session transport; use production player identity/storage."""

    def get_pokemon_by_id(self, identifier):
        """Expose the normal owned-ID lookup."""
        return User.get_pokemon_by_id(self, identifier)

    def get_active_pokemon_by_slot(self, slot):
        """Retain canonical party slots and gaps."""
        return User.get_active_pokemon_by_slot(self, slot)

    def get_active_party(self):
        """Use the canonical player's ordinary party view."""
        return User.get_active_party(self)

    def get_box(self, index):
        """Use the ordinary storage destination."""
        return User.get_box(self, index)

    def _pokemon_is_in_party(self, pokemon):
        """Use production deposit eligibility."""
        return User._pokemon_is_in_party(self, pokemon)

    def deposit_pokemon(self, identifier, index=1):
        """Exercise the shipped deposit transition."""
        return User.deposit_pokemon(self, identifier, index)

    def execute_cmd(self, text, **kwargs):
        """Capture the menu's exit look command at the session boundary."""
        self.messages.append("Menu exit: " + text)


class AbilityItemCases(unittest.TestCase):
    """Check both ability item field routes, canonical targets, persistence and atomic use."""

    def setUp(self):
        """Create a tagged ordinary owner with a genuinely gapped party."""
        self.character = ObjectDB.objects.create(db_key="ability-item-769-" + uuid4().hex, db_typeclass_path="pokemon.user.User")
        self.trainer, _ = Trainer.objects.get_or_create(user=self.character, defaults={"trainer_number": Trainer.objects.count() + 1})
        self.storage, _ = UserStorage.objects.get_or_create(user=self.character)
        StorageBox.objects.create(storage=self.storage, name="Ability Box")
        self.player = AbilityPlayer(self.character, self.trainer, self.storage)
        self.player.pk = self.character.pk
        self.mon = self.create_mon()
        self.mon.activemoveslot_set.filter(slot=2).update(slot=4)

    def tearDown(self):
        """Release any real menu on this disposable transport."""
        menu = self.player.ndb._evmenu
        if menu:
            menu.close_menu()

    def create_mon(self, slot=3, species="Eevee", level=50):
        """Use production creation and placement, not invented HP/EXP."""
        pokemon = create_owned_pokemon(species, self.trainer, level, nature="Hardy",
                                       ivs=[0] * 6, evs=[0] * 6, active_move_names=["Tackle", "Water Gun"])
        PlacementService(self.storage).to_party(pokemon, slot=slot)
        return pokemon

    def command(self, args, kind="use", player=None):
        """Run the real parser/command; do not substitute an item effect."""
        player = player or self.player
        command = COMMANDS[kind]()
        command.caller, command.args, command.cmdstring = player, args, "+" + kind
        command.parse()
        module = sys.modules[command.__module__]
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        return player.messages[-1] if player.messages else ""

    def state(self, pokemon=None, **fields):
        """Set explicit fixture state while leaving stale model caches intact."""
        OwnedPokemon.objects.filter(pk=(pokemon or self.mon).pk).update(**fields)

    def snapshot(self, pokemon=None):
        """Read persisted Pokemon, placement, bag, boost and move rows."""
        identifier = (pokemon or self.mon).pk
        return {
            "pokemon": OwnedPokemon.objects.filter(pk=identifier).values().first(),
            "placement": list(PokemonPlacement.objects.filter(pokemon_id=identifier).values()),
            "inventory_cache": dict(self.character.db.inventory or {}),
            "inventory": list(self.trainer.list_inventory().values("item_name", "quantity")),
            "learned": list(PokemonLearnedMove.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "active": list(ActiveMoveslot.objects.filter(pokemon_id=identifier).order_by("slot").values()),
            "boosts": list(MovePPBoost.objects.filter(pokemon_id=identifier).order_by("move_id").values()),
            "sets": list(MovesetSlot.objects.filter(moveset__pokemon_id=identifier).order_by("pk").values()),
        }

    def give(self, item, amount=1):
        """Fixture setup grants bag stock separately from ordinary acceptance."""
        self.trainer.add_item(item, amount)

    def record(self, label, args, pokemon=None):
        """Retain ordinary input/output and independent SQL before/after proof."""
        before, start = self.snapshot(pokemon), len(self.player.messages)
        self.command(args)
        EVIDENCE.append({"label": label, "command": "+use " + args, "before": before,
                         "after": self.snapshot(pokemon), "messages": self.player.messages[start:]})

    def prepare(self, species="Eevee", ability="Run Away", **fields):
        """Seed saved identity/ability independently, leaving stale cache values."""
        self.state(species=species, ability=ability, current_hp=12, status="psn",
                   friendship=203, held_item="Leftovers", flags=["ordinary-ability-fixture"], **fields)

    def assert_change(self, before, expected, item, quantity=0):
        """Require exactly the ability field and bag copy to change."""
        after = self.snapshot()
        for name, value in before["pokemon"].items():
            self.assertEqual(after["pokemon"][name], expected if name == "ability" else value, name)
        for name in ("placement", "learned", "active", "sets", "boosts"):
            self.assertEqual(after[name], before[name], name)
        self.assertEqual(self.trainer.get_item_quantity(item), quantity)

    def flow(self, item, initial, expected):
        """Run discovery/use/output/reload and production battle reconstruction."""
        from django.db import connections
        from utils.pokemon_utils import build_battle_pokemon_from_model

        self.prepare(ability=initial)
        self.give(item)
        self.assertIn(item, self.command("", "inventory"))
        self.assertIn(str(self.mon.pk), self.command("3", "party"))
        before = self.snapshot()
        self.record("ordinary-ability-use", item + "=3")
        self.assertIn(initial + " -> " + expected, self.player.messages[-1])
        self.assert_change(before, expected, item)
        self.assertIn(expected, self.command("3", "party"))
        connections.close_all()
        OwnedPokemon.flush_cached_instance(self.mon)
        self.assert_change(before, expected, item)
        runtime = build_battle_pokemon_from_model(OwnedPokemon.objects.get(pk=self.mon.pk))
        self.assertEqual(getattr(runtime.ability, "name", runtime.ability), expected)

    def test_capsule_slot_0_to_1_player_flow(self):
        """Capsule switches normal slot 0 to 1 and survives SQL/runtime reload."""
        self.flow("Ability Capsule", "Run Away", "Adaptability")

    def test_capsule_slot_1_to_0_player_flow(self):
        """Capsule also switches the second ordinary slot back to the first."""
        self.flow("Ability Capsule", "Adaptability", "Run Away")

    def test_patch_slot_0_to_hidden_player_flow(self):
        """Patch changes the first ordinary ability to the exact hidden slot."""
        self.flow("Ability Patch", "Run Away", "Anticipation")

    def test_patch_slot_1_to_hidden_player_flow(self):
        """Patch accepts either legal ordinary slot."""
        self.flow("Ability Patch", "Adaptability", "Anticipation")

    def test_patch_hidden_to_slot_0_player_flow(self):
        """Selected Gen-9 reversal deterministically chooses ordinary slot 0."""
        self.flow("Ability Patch", "Anticipation", "Run Away")

    def test_single_ordinary_with_hidden_patch_and_capsule_no_effect(self):
        """Pikachu can Patch in both directions but has no second Capsule slot."""
        self.prepare("Pikachu", "Static")
        self.give("Ability Capsule", 2)
        self.give("Ability Patch", 2)
        for expected in ("Lightning Rod", "Static"):
            before = self.snapshot()
            self.command("Ability Capsule=3")
            self.assertEqual(self.snapshot(), before)
            self.record("single-ordinary-patch", "Ability Patch=3")
            self.assertEqual(self.snapshot()["pokemon"]["ability"], expected)
        self.assertEqual(self.trainer.get_item_quantity("Ability Capsule"), 2)
        self.assertEqual(self.trainer.get_item_quantity("Ability Patch"), 0)

    def test_hidden_capsule_and_absent_hidden_are_no_effect(self):
        """Hidden Capsule and one-ability Mew/Gastly never consume stock."""
        for species, ability in (("Eevee", "Anticipation"), ("Mew", "Synchronize"), ("Gastly", "Levitate")):
            self.prepare(species, ability)
            for item in ITEMS:
                self.give(item)
                if species == "Eevee" and item == "Ability Patch":
                    continue
                before = self.snapshot()
                self.record("legal-no-effect", item + "=3")
                self.assertEqual(self.snapshot(), before)
                self.assertIn("had no effect", self.player.messages[-1])

    def test_special_slots_cannot_be_created_or_removed(self):
        """Own Tempo, Battle Bond and Power Construct are special, not hidden."""
        for species, ability in (("Rockruff", "Own Tempo"), ("Greninja", "Battle Bond"), ("Zygarde", "Power Construct")):
            self.prepare(species, ability)
            for item in ITEMS:
                self.give(item)
                before = self.snapshot()
                self.record("special-slot-no-effect", item + "=3")
                self.assertEqual(self.snapshot(), before)
        self.prepare("Rockruff", "Vital Spirit")
        self.command("Ability Patch=3")
        self.assertEqual(self.snapshot()["pokemon"]["ability"], "Steadfast")

    def test_native_regional_and_gender_forms_keep_their_own_slots(self):
        """Do not fall back from Rattata-Alola or Meowstic-F to base abilities."""
        for species, first, second, hidden, gender in (
                ("Rattata-Alola", "Gluttony", "Hustle", "Thick Fat", "M"),
                ("Meowstic-F", "Keen Eye", "Infiltrator", "Competitive", "F")):
            self.prepare(species, first, gender=gender)
            self.give("Ability Capsule")
            self.give("Ability Patch", 2)
            for item, expected in (("Ability Capsule", second), ("Ability Patch", hidden), ("Ability Patch", first)):
                self.record("native-form-slots", item + "=3")
                self.assertEqual(self.snapshot()["pokemon"]["ability"], expected)
                self.assertEqual(self.snapshot()["pokemon"]["species"], species)
        self.prepare("Rattata-Alola", "Run Away")
        self.give("Ability Patch")
        before = self.snapshot()
        self.command("Ability Patch=3")
        self.assertEqual(self.snapshot(), before)

    def test_unknown_battle_only_locked_and_gender_invalid_forms_reject(self):
        """Required-item/ability forms are not made eligible by changing a name."""
        for species, ability in (("Not A Species", "Run Away"), ("Gengar-Mega", "Shadow Tag"),
                                 ("Darmanitan-Zen", "Zen Mode"), ("Giratina-Origin", "Levitate"),
                                 ("Ogerpon-Wellspring", "Water Absorb"), ("Meowstic-F", "Keen Eye")):
            self.prepare(species, ability, gender="M")
            for item in ITEMS:
                self.give(item)
                before = self.snapshot()
                self.record("unsupported-form", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_nickname_foreign_empty_and_unknown_ability_cannot_grant_eligibility(self):
        """Never derive another species' eligibility from a display name or string."""
        for species, ability, nickname in (("Mew", "Synchronize", "Eevee"),
                                           ("Mew", "Run Away", "Eevee"),
                                           ("Eevee", "", "Mew"), ("Eevee", "Wonder Guard", "Eevee")):
            self.prepare(species, ability, nickname=nickname)
            for item in ITEMS:
                self.give(item)
                before = self.snapshot()
                self.record("nickname-or-invalid-ability", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_ambiguous_saved_or_destination_slots_are_rejected(self):
        """The name-only model must never guess between duplicate dex slot names."""
        from pokemon.data.evolution import lookup_species
        data = lookup_species("Eevee")
        for slots in ({"0": "Run Away", "1": "Run Away", "H": "Anticipation"},
                      {"0": "Run Away", "1": "Adaptability", "H": "Adaptability"}):
            self.prepare()
            for item in ITEMS:
                self.give(item)
                before = self.snapshot()
                with patch.dict(data.raw, {"abilities": slots}):
                    self.command(item + "=3")
                self.assertEqual(self.snapshot(), before)
                self.assertIn("ambiguous", self.player.messages[-1])

    def test_transformed_and_foreign_native_metadata_cannot_grant_eligibility(self):
        """Reject runtime transformations; only persisted native identity is legal."""
        for item in ITEMS:
            self.prepare()
            self.give(item)
            for attr, value in (("transformed", True), ("base_species", "Ditto")):
                setattr(self.mon, attr, value)
                try:
                    before = self.snapshot()
                    self.command(item + "=3")
                    self.assertEqual(self.snapshot(), before)
                finally:
                    delattr(self.mon, attr)

    def test_malformed_canonical_slot_data_cannot_spend_stock(self):
        """Fail closed if the canonical profile is incomplete or malformed."""
        from pokemon.data.evolution import lookup_species
        data = lookup_species("Eevee")
        self.prepare()
        for item in ITEMS:
            self.give(item)
            for slots in ({}, {"0": ""}, {"0": None}, {"0": "Run Away", "X": "Guts"}):
                before = self.snapshot()
                with patch.dict(data.raw, {"abilities": slots}):
                    self.command(item + "=3")
                self.assertEqual(self.snapshot(), before)
                self.assertIn("Invalid species ability slots", self.player.messages[-1])

    def test_fresh_species_and_ability_override_cached_forms(self):
        """A stale Eevee snapshot must use freshly saved Alolan slots and ability."""
        self.prepare()
        FieldMedicineUse._refresh(self.mon, self.snapshot()["pokemon"])
        self.prepare("Rattata-Alola", "Hustle")
        self.give("Ability Patch")
        self.record("fresh-native-form", "Ability Patch=3")
        self.assertEqual(self.snapshot()["pokemon"]["ability"], "Thick Fat")
        self.assertEqual(self.mon.species, "Rattata-Alola")

    def test_normalized_item_inventory_and_ability_names(self):
        """Exact normalized spellings are accepted without prefixes or free stock."""
        for item, expected in (("Ability Capsule", "Adaptability"), ("Ability Patch", "Anticipation")):
            self.prepare(ability="RUN-AWAY")
            InventoryEntry.objects.create(owner=self.trainer, item_name=item.upper(), quantity=1)
            self.record("normalized-bag-and-ability", item.upper().replace(" ", "-") + "=" + str(self.mon.pk))
            self.assertEqual(self.snapshot()["pokemon"]["ability"], expected)
            self.assertEqual(self.trainer.get_item_quantity(item), 0)
        for args in ("Ability=3", "Ability Cap=3", "Ability Pat=3"):
            before = self.snapshot()
            self.command(args)
            self.assertEqual(self.snapshot(), before)

    def test_missing_stock_no_selector_party_or_arbitrary_ability_argument(self):
        """Only stocked single-target native-slot transitions have a player route."""
        self.prepare()
        for item in ITEMS:
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.give(item)
            for suffix in ("3/1", "party", "3/Anticipation", "3 Anticipation", "", "Ability Patch"):
                before = self.snapshot()
                self.command(item + "=" + suffix)
                self.assertEqual(self.snapshot(), before)
            self.command(item)
            self.assertIn("Usage", self.player.messages[-1])

    def test_current_fusion_and_name_id_target_first_routes(self):
        """Both items accept only the actual current Fusion and ordinary target syntax."""
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.character.db.fusion_id = str(self.mon.pk)
        for item in ITEMS:
            for alias in ("fusion", "self", "me"):
                self.prepare()
                self.give(item)
                self.record("current-fusion-ability", item + "=" + alias)
                self.assertEqual(self.trainer.get_item_quantity(item), 0)
        PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)
        self.character.db.fusion_id = None
        for item in ITEMS:
            for args in (item + "=Eevee", "3=" + item, item + "=" + str(self.mon.pk)):
                self.prepare()
                self.give(item)
                self.command(args)
                self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_both_items_reject_eggs_boxed_and_inactive_fusion(self):
        """Use real deposit and reservation transitions, then reject stale targets."""
        for item in ITEMS:
            self.prepare(is_egg=True)
            self.give(item)
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.state(is_egg=False)
            self.assertIn("deposited", self.command(str(self.mon.pk), "deposit"))
            before = self.snapshot()
            self.record("post-deposit-rejection", item + "=" + str(self.mon.pk))
            self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).to_party(self.mon, slot=3)
            PlacementService(self.storage).reserve_for_fusion(self.mon)
            before = self.snapshot()
            for target in ("fusion", str(self.mon.pk)):
                self.command(item + "=" + target)
                self.assertEqual(self.snapshot(), before)
            PlacementService(self.storage).return_from_fusion(self.mon, preferred_slot=3)

    def test_ambiguous_gapped_and_foreign_targets_are_rejected(self):
        """Do not compact a party gap or silently select a same-name Pokemon."""
        self.create_mon(slot=6)
        other = ObjectDB.objects.create(db_key="ability-foreign-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        foreign = create_owned_pokemon("Eevee", trainer, 20)
        for item in ITEMS:
            self.prepare()
            self.give(item)
            for target in ("Eevee", "1", str(foreign.pk), "Missing"):
                before = self.snapshot()
                self.command(item + "=" + target)
                self.assertEqual(self.snapshot(), before)

    def test_fresh_owner_and_battle_guards_apply_inside_service(self):
        """Do not rely on an old caller trainer or only the command's battle check."""
        for item in ITEMS:
            self.prepare()
            self.give(item)
            before = self.snapshot()
            self.character.db.battle_lock = "ability-item-fixture"
            self.command(item + "=3")
            self.assertIsNone(FieldAbilityUse(self.player).use(item, "3"))
            self.assertEqual(self.snapshot(), before)
            self.character.db.battle_lock = None
            self.player.ndb.battle_instance = object()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.player.ndb.battle_instance = None
        other = ObjectDB.objects.create(db_key="ability-changed-owner-" + uuid4().hex)
        trainer = Trainer.objects.create(user=other, trainer_number=Trainer.objects.count() + 1)
        self.state(trainer_id=trainer.pk)
        for item in ITEMS:
            before = self.snapshot()
            self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)

    def test_fainted_targets_change_ability_without_healing_or_curing(self):
        """A legal field ability change never revives, heals or cures its target."""
        for item, expected in (("Ability Capsule", "Adaptability"), ("Ability Patch", "Anticipation")):
            self.prepare()
            self.state(current_hp=0)
            self.give(item)
            before = self.snapshot()
            self.record("fainted-ability-change", item + "=3")
            self.assert_change(before, expected, item)

    def test_failed_and_partial_debits_roll_back_both_items(self):
        """Roll back even when remove_item performs real SQL then reports failure."""
        original = Trainer.remove_item

        def partial(trainer, *args):
            """Inject failure after the actual debit."""
            original(trainer, *args)
            return False

        for item in ITEMS:
            for debit in (lambda *args: False, partial):
                self.prepare()
                self.give(item)
                before = self.snapshot()
                with patch.object(Trainer, "remove_item", debit):
                    self.record("failed-ability-debit", item + "=3")
                self.assertEqual(self.snapshot(), before)

    def test_post_sql_ability_save_failure_restores_rows_and_caches(self):
        """An exception after actual ability UPDATE cannot retain an effect/debit."""
        original = OwnedPokemon.save

        def fail_after_save(pokemon, *args, **kwargs):
            """Do the real SQL, then fail within the shared outer transaction."""
            original(pokemon, *args, **kwargs)
            raise RuntimeError("injected ability save failure")

        for item in ITEMS:
            self.prepare()
            self.give(item)
            before = self.snapshot()
            with patch.object(OwnedPokemon, "save", fail_after_save):
                with self.assertRaisesRegex(RuntimeError, "injected ability"):
                    self.command(item + "=3")
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.mon.ability, before["pokemon"]["ability"])

    def race(self, *actions):
        """Compete with real commands on independent synchronized connections."""
        from django.db import close_old_connections
        barrier = Barrier(len(actions))

        def run(action):
            """Give each worker its own database lifetime."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_last_copy_each_item_can_only_change_ability_once(self):
        """One copy cannot fund a second toggle back to the initial ability."""
        for item, expected in (("Ability Capsule", "Adaptability"), ("Ability Patch", "Anticipation")):
            self.prepare()
            self.give(item)
            before = self.snapshot()
            self.race(lambda: self.command(item + "=3"), lambda: self.command(item + "=3"))
            self.assert_change(before, expected, item)

    def test_last_copy_cannot_change_two_different_targets(self):
        """Different target locks still share the owner's inventory budget."""
        other = self.create_mon(slot=6)
        for item, expected in (("Ability Capsule", "Adaptability"), ("Ability Patch", "Anticipation")):
            self.prepare()
            self.state(other, ability="Run Away")
            self.give(item)
            self.race(lambda: self.command(item + "=3"), lambda: self.command(item + "=6"))
            abilities = sorted(self.snapshot(pokemon)["pokemon"]["ability"] for pokemon in (self.mon, other))
            self.assertEqual(abilities, sorted(("Run Away", expected)))
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_two_stocked_uses_serialize_two_legal_paid_transitions(self):
        """Two intentional toggles may return to slot 0, each with its own copy."""
        for item in ITEMS:
            self.prepare()
            self.give(item, 2)
            self.race(lambda: self.command(item + "=3"), lambda: self.command(item + "=3"))
            self.assertEqual(self.snapshot()["pokemon"]["ability"], "Run Away")
            self.assertEqual(self.trainer.get_item_quantity(item), 0)

    def test_competing_capsule_patch_recheck_current_slot(self):
        """Patch-first leaves Capsule unused; Capsule-first then Patch spends both."""
        self.prepare()
        for item in ITEMS:
            self.give(item)
        self.race(lambda: self.command("Ability Capsule=3"), lambda: self.command("Ability Patch=3"))
        self.assertEqual(self.snapshot()["pokemon"]["ability"], "Anticipation")
        self.assertEqual(self.trainer.get_item_quantity("Ability Patch"), 0)
        self.assertIn(self.trainer.get_item_quantity("Ability Capsule"), (0, 1))

    def test_patch_hidden_slot_survives_normal_item_evolution(self):
        """Eevee's changed H slot becomes Flareon's H slot, then Patch reverses."""
        self.prepare()
        self.give("Ability Patch", 2)
        self.give("Fire Stone")
        self.record("patch-before-evolution", "Ability Patch=3")
        self.command(str(self.mon.pk) + " Fire Stone", "evolve")
        row = self.snapshot()["pokemon"]
        self.assertEqual((row["species"], row["ability"]), ("Flareon", "Guts"))
        self.record("patch-after-evolution", "Ability Patch=3")
        self.assertEqual(self.snapshot()["pokemon"]["ability"], "Flash Fire")
        self.assertEqual(self.trainer.get_item_quantity("Fire Stone"), 0)

    def test_capsule_slot_evolution_fallback_and_no_effect_on_single_slot(self):
        """Retain existing evolution fallback when the evolved form lacks slot 1."""
        self.prepare()
        self.give("Ability Capsule", 2)
        self.give("Water Stone")
        self.record("capsule-before-evolution", "Ability Capsule=3")
        self.command(str(self.mon.pk) + " Water Stone", "evolve")
        row = self.snapshot()["pokemon"]
        self.assertEqual((row["species"], row["ability"]), ("Vaporeon", "Water Absorb"))
        before = self.snapshot()
        self.record("capsule-after-single-slot-evolution", "Ability Capsule=3")
        self.assertEqual(self.snapshot(), before)


ITEMS = ("Ability Capsule", "Ability Patch")


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from evennia.utils.evmenu import CmdEvMenuNode
            from utils.enhanced_evmenu import EnhancedEvMenu
            from commands.player.cmd_inventory import CmdInventory, CmdUseItem
            from commands.player.cmd_party import CmdDepositPokemon, CmdSetHoldItem
            from commands.player.cmd_sheet import CmdSheetPokemon
            from commands.player.cmd_learn_evolve import CmdEvolvePokemon
        from evennia.objects.models import ObjectDB
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp, get_stats
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost, MovesetSlot, PokemonLearnedMove
        from pokemon.models.storage import PokemonPlacement, StorageBox, UserStorage
        from pokemon.models.trainer import Trainer, InventoryEntry
        from pokemon.services.field_items import FieldMedicineUse
        from pokemon.services.field_abilities import FieldAbilityUse
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"use": CmdUseItem, "inventory": CmdInventory, "party": CmdSheetPokemon,
                    "deposit": CmdDepositPokemon, "hold": CmdSetHoldItem, "evolve": CmdEvolvePokemon}
        try:
            result = unittest.main(verbosity=2, exit=False).result
        finally:
            destination = os.environ.get("PF2_ABILITY_ITEM_EVIDENCE")
            if destination:
                Path(destination).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
