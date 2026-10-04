"""Real ORM evolution/held-item tests, sharing the disposable lifecycle harness.

Run: python tests/integration/evolution_cases.py
PF2_TEST_POSTGRES_DSN enables concurrent-writer tests; no migrations are run.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import placement_cases as harness
from placement_cases import (
    ObjectDB,
    OwnedPokemon,
    PlacementCases,
    Trainer,
    connections,
    create_schema,
)

from pokemon.services.evolution import EvolutionError, EvolutionService, resolve_item


class EvolutionCases(unittest.TestCase):
    """Assert persisted outcomes and cached state after success and failure."""

    setUp = PlacementCases.setUp
    mon = PlacementCases.mon
    run_race = PlacementCases.run_race

    def lifecycle(self, species="Vulpix", **attrs):
        """Create one placed Pokemon and a caller with trusted room evidence."""
        mon = self.mon()
        mon.species = species
        for key, value in attrs.items():
            setattr(mon, key, value)
        mon.save()
        caller = SimpleNamespace(
            pk=self.user.pk, storage=self.storage, location=SimpleNamespace(db=SimpleNamespace(time_of_day="night"))
        )
        return mon, EvolutionService(caller)

    def quantity(self, key):
        """Read the actual inventory rows, not the character cache."""
        return self.trainer.get_item_quantity(key)

    def test_item_success_and_retry(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone", 2)
        self.assertEqual(service.evolve(mon, item="Fire Stone"), "Ninetales")
        self.assertIsNone(service.evolve(mon, item="FIRE STONE"))
        mon.refresh_from_db()
        self.assertEqual(mon.species, "Ninetales")
        self.assertEqual(self.quantity("firestone"), 1)

    def test_level_retry_cannot_skip_second_stage(self):
        mon, service = self.lifecycle("Bulbasaur", level=40)
        self.assertEqual(service.evolve(mon), "Ivysaur")
        self.assertIsNone(service.evolve(mon))
        self.assertEqual(mon.species, "Ivysaur")
        self.assertEqual(service.evolve(mon, target="Venusaur"), "Venusaur")

    def test_wrong_owner_egg_and_reserved_rejected(self):
        mon, service = self.lifecycle()
        other = ObjectDB.objects.create(db_key="Other")
        mon.is_egg = True
        mon.save()
        with self.assertRaises(EvolutionError):
            service.evolve(mon)
        mon.is_egg = False
        mon.save()
        service.caller.pk = other.pk
        with self.assertRaises(EvolutionError):
            service.evolve(mon)
        service.caller.pk = self.user.pk
        self.service.reserve_for_fusion(mon)
        with self.assertRaises(EvolutionError):
            service.evolve(mon, item="Fire Stone")
        self.assertEqual(mon.species, "Vulpix")

    def test_validation_failure_and_missing_item_change_nothing(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("waterstone")
        for item in ("Water Stone", "Fire", "Stone", "Fire Stone"):
            with self.assertRaises(EvolutionError):
                service.evolve(mon, item=item)
        self.assertEqual(mon.species, "Vulpix")
        self.assertEqual(self.quantity("waterstone"), 1)
        self.assertEqual(mon.flags, [])

    def test_evolution_save_failure_rolls_back_every_field_and_item(self):
        mon, service = self.lifecycle(nickname="Fluffy", current_hp=9)
        self.trainer.add_item("firestone")
        with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                service.evolve(mon, item="Fire Stone")
        self.assertEqual((mon.species, mon.nickname, mon.current_hp, mon.flags), ("Vulpix", "Fluffy", 9, []))
        self.assertEqual(self.quantity("firestone"), 1)
        self.assertEqual(service.evolve(mon, item="Fire Stone"), "Ninetales")

    def test_interruption_after_database_save_rolls_back_species_and_inventory(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone")
        original_save = OwnedPokemon.save

        def interrupted_save(pokemon, *args, **kwargs):
            original_save(pokemon, *args, **kwargs)
            raise KeyboardInterrupt("interrupted after write")

        with patch.object(OwnedPokemon, "save", interrupted_save):
            with self.assertRaises(KeyboardInterrupt):
                service.evolve(mon, item="Fire Stone")
        self.assertEqual(OwnedPokemon.objects.filter(pk=mon.pk).values_list("species", flat=True).get(), "Vulpix")
        self.assertEqual((mon.species, mon.flags), ("Vulpix", []))
        self.assertEqual(self.quantity("firestone"), 1)

    def test_failed_consumption_does_not_evolve(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone")
        with patch.object(Trainer, "remove_item", return_value=False):
            with self.assertRaises(EvolutionError):
                service.evolve(mon, item="Fire Stone")
        self.assertEqual(mon.species, "Vulpix")
        self.assertEqual(self.quantity("firestone"), 1)

    def test_held_evolution_consumes_held_item_only_and_rolls_back(self):
        mon, service = self.lifecycle("Gligar", held_item="Razor Fang")
        self.trainer.add_item("razorfang")
        with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                service.evolve(mon)
        self.assertEqual((mon.species, mon.held_item), ("Gligar", "Razor Fang"))
        self.assertEqual(service.evolve(mon), "Gliscor")
        self.assertEqual(mon.held_item, "")
        self.assertEqual(self.quantity("razorfang"), 1)

    def test_replace_remove_and_repeated_requests_conserve_items(self):
        mon, service = self.lifecycle(held_item="Sitrus Berry")
        self.trainer.add_item("oranberry", 2)
        service.hold(1, "Oran Berry")
        service.hold(1, "oranberry")
        self.assertEqual(mon.held_item, "Oran Berry")
        self.assertEqual(self.quantity("oranberry"), 1)
        self.assertEqual(self.quantity("sitrusberry"), 1)
        service.hold(1)
        service.hold(1)
        self.assertEqual(mon.held_item, "")
        self.assertEqual(self.quantity("oranberry"), 2)
        self.assertEqual(self.quantity("sitrusberry"), 1)

    def test_replace_and_remove_save_failure_roll_back(self):
        mon, service = self.lifecycle(held_item="Sitrus Berry")
        self.trainer.add_item("oranberry")
        for item in ("Oran Berry", None):
            with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("save failed")):
                with self.assertRaises(RuntimeError):
                    service.hold(1, item)
            self.assertEqual(mon.held_item, "Sitrus Berry")
            self.assertEqual(self.quantity("oranberry"), 1)
            self.assertEqual(self.quantity("sitrusberry"), 0)

    def test_return_failure_rolls_back_new_item(self):
        mon, service = self.lifecycle(held_item="Sitrus Berry")
        self.trainer.add_item("oranberry")
        with patch.object(Trainer, "add_item", side_effect=RuntimeError("return failed")):
            with self.assertRaises(RuntimeError):
                service.hold(1, "Oran Berry")
        self.assertEqual(mon.held_item, "Sitrus Berry")
        self.assertEqual(self.quantity("oranberry"), 1)

    def test_legacy_inventory_name_and_ambiguous_rows(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("fire stone")
        self.trainer.add_item("firestone")
        with self.assertRaisesRegex(EvolutionError, "Ambiguous"):
            service.evolve(mon, item="Fire Stone")
        self.trainer.remove_item("firestone")
        service.evolve(mon, item="Fire Stone")
        self.assertEqual(self.quantity("fire stone"), 0)

    def test_legacy_carried_item_rolls_back_then_returns_to_trainer(self):
        mon, service = self.lifecycle(held_item="Sitrus Berry")
        obj = ObjectDB.objects.create(db_key="Oran Berry")
        ObjectDB.objects.filter(pk=obj.pk).update(db_location=self.user)
        pk = obj.pk
        with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                service.hold(1, "Oran Berry")
        self.assertTrue(ObjectDB.objects.filter(pk=pk, db_location=self.user).exists())
        self.assertEqual(mon.held_item, "Sitrus Berry")
        service.hold(1, "Oran Berry")
        service.hold(1, "Oran Berry")
        self.assertFalse(ObjectDB.objects.filter(pk=pk).exists())
        service.hold(1)
        self.assertEqual(self.quantity("oranberry"), 1)
        self.assertEqual(self.quantity("sitrusberry"), 1)

    def test_carried_ambiguity_and_partial_names_do_not_delete(self):
        mon, service = self.lifecycle()
        for _ in range(2):
            obj = ObjectDB.objects.create(db_key="Oran Berry")
            ObjectDB.objects.filter(pk=obj.pk).update(db_location=self.user)
        for name in ("Oran", "Oran Berry"):
            with self.assertRaises(EvolutionError):
                service.hold(1, name)
        self.assertEqual(ObjectDB.objects.filter(db_location=self.user).count(), 2)
        self.assertEqual(mon.held_item, "")

    def test_item_resolver_rejects_colliding_full_names(self):
        from pokemon.dex import ITEMDEX

        duplicate = SimpleNamespace(name="Fire Stone", raw={"name": "Fire Stone"})
        with patch.dict(ITEMDEX, {"Duplicate": duplicate}):
            with self.assertRaises(EvolutionError):
                resolve_item("Fire Stone")

    def test_inventory_cache_only_published_after_commit(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone")
        with patch.object(Trainer, "_sync_character_inventory") as sync:
            with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("save failed")):
                with self.assertRaises(RuntimeError):
                    service.evolve(mon, item="Fire Stone")
            sync.assert_not_called()
            service.evolve(mon, item="Fire Stone")
            self.assertTrue(sync.called)

    def test_current_form_is_loaded_from_database_not_caller_cache(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone")
        mon.species = "Eevee"  # unsaved, stale shared instance
        self.assertEqual(service.evolve(mon, item="Fire Stone"), "Ninetales")
        self.assertEqual(mon.species, "Ninetales")

    def test_known_move_requires_active_slot_and_context_uses_persisted_state(self):
        from pokemon.models.moves import ActiveMoveslot, Move

        mon, service = self.lifecycle("Tangela")
        move, _ = Move.objects.get_or_create(name="Ancient Power")
        mon.learned_moves.add(move)
        with self.assertRaises(EvolutionError):
            service.evolve(mon)
        ActiveMoveslot.objects.create(pokemon=mon, move=move, slot=1)
        self.assertEqual(service.evolve(mon), "Tangrowth")

    def test_sylveon_fairy_move_and_friendship_context(self):
        from pokemon.models.moves import ActiveMoveslot, Move

        mon, service = self.lifecycle("Eevee", friendship=160)
        service.caller.location.db.time_of_day = "day"
        move, _ = Move.objects.get_or_create(name="Baby-Doll Eyes")
        ActiveMoveslot.objects.create(pokemon=mon, move=move, slot=1)
        self.assertEqual(service.evolve(mon), "Sylveon")

    def test_foreign_pokemon_is_rejected_even_when_passed_directly(self):
        mon, service = self.lifecycle()
        foreign_user = ObjectDB.objects.create(db_key="Foreign")
        foreign_trainer = Trainer.objects.create(user=foreign_user, trainer_number=Trainer.objects.count() + 1)
        from django.db import transaction

        from pokemon.models.storage import UserStorage
        from pokemon.services.placement import PlacementService

        foreign_storage = UserStorage.objects.create(user=foreign_user)
        with transaction.atomic():
            foreign = OwnedPokemon.objects.create(trainer=foreign_trainer, species="Vulpix", ivs=[0] * 6, evs=[0] * 6)
            PlacementService(foreign_storage).to_party(foreign)
        self.trainer.add_item("firestone")
        with self.assertRaises(EvolutionError):
            service.evolve(foreign, item="Fire Stone")
        self.assertEqual(self.quantity("firestone"), 1)
        self.assertEqual(foreign.species, "Vulpix")

    @unittest.skipUnless(
        harness._dsn and not __import__("os").environ.get("PF2_TEST_PGLITE"), "requires PostgreSQL row locks"
    )
    def test_concurrent_evolution_and_held_requests(self):
        mon, service = self.lifecycle()
        self.trainer.add_item("firestone", 2)
        results = self.run_race(
            lambda: service.evolve(mon, item="Fire Stone"), lambda: service.evolve(mon, item="Fire Stone")
        )
        self.assertCountEqual(results, ["Ninetales", None])
        self.assertEqual(self.quantity("firestone"), 1)
        self.trainer.add_item("oranberry", 2)
        self.run_race(lambda: service.hold(1, "Oran Berry"), lambda: service.hold(1, "Oran Berry"))
        self.assertEqual(self.quantity("oranberry"), 1)
        self.run_race(lambda: service.hold(1), lambda: service.hold(1))
        self.assertEqual(self.quantity("oranberry"), 2)


if __name__ == "__main__":
    try:
        create_schema()
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(EvolutionCases)
        )
    finally:
        connections.close_all()
        if harness._dsn:
            with harness.admin.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA "{harness._schema}" CASCADE')
            harness.admin.close()
        harness._temp.cleanup()
    raise SystemExit(not result.wasSuccessful())
