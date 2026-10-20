"""Exercise item repairs with production models in a disposable PG schema."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres


class RemainingItemCases(unittest.TestCase):
    """Check exact target effects, atomic rollback, guards and PP identity."""

    def setUp(self):
        """Create only new models inside the connection-guarded test schema."""
        self.character = ObjectDB.objects.create(db_key="medicine-" + uuid4().hex)
        self.trainer = Trainer.objects.create(
            user=self.character, trainer_number=Trainer.objects.count() + 1
        )
        self.storage = UserStorage.objects.create(user=self.character)
        self.owned = create_owned_pokemon(
            "Mew",
            self.trainer,
            50,
            nature="Hardy",
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Tackle", "Watergun"],
        )
        PlacementService(self.storage).to_party(self.owned, slot=3)
        self.mon = build_battle_pokemon_from_model(self.owned)
        self.player = SimpleNamespace(
            trainer=self.trainer, db=self.character.db, storage=self.storage
        )
        self.actor = BattleParticipant("Medicine", [self.mon], player=self.player)
        foe = Pokemon("Wailord", hp=500, max_hp=500)
        self.opponent = BattleParticipant("Other", [foe])
        self.actor.active, self.opponent.active = [self.mon], [foe]
        self.battle = Battle(BattleType.WILD, [self.actor, self.opponent])

    def use(self, item, *, target=None, move=None):
        """Use the ordinary battle dispatcher and read the saved inventory."""
        self.trainer.add_item(item, 2)
        action = Action(
            self.actor,
            ActionType.ITEM,
            self.actor,
            item=item,
            pokemon=self.mon,
            target_pokemon=target or self.mon,
            item_move=move,
        )
        self.battle.execute_item(action)
        return action

    def test_existing_healing_and_cure_routes_persist(self):
        """All existing medicine routes share one validated durable effect."""
        for item, amount in [
            ("Potion", 20),
            ("Super Potion", 60),
            ("Hyper Potion", 120),
            ("Energy Powder", 60),
            ("Energy Root", 120),
            ("Max Potion", self.mon.max_hp),
        ]:
            self.mon.hp = 1
            self.use(item)
            self.owned.refresh_from_db()
            self.assertEqual(self.mon.hp, min(self.mon.max_hp, 1 + amount))
            self.assertEqual(self.owned.current_hp, self.mon.hp)
            self.assertEqual(self.trainer.get_item_quantity(item), 1)
        for item, status in [
            ("Antidote", "tox"),
            ("Burn Heal", "brn"),
            ("Ice Heal", "frz"),
            ("Awakening", "slp"),
            ("Paralyze Heal", "par"),
            ("Full Heal", "psn"),
            ("Heal Powder", "par"),
            ("Full Restore", "brn"),
        ]:
            self.mon.status = status
            self.use(item)
            self.owned.refresh_from_db()
            self.assertFalse(self.mon.status)
            self.assertEqual(self.owned.status, "")
            self.assertEqual(self.trainer.get_item_quantity(item), 1)

    def test_reserve_revives_exact_target_and_replay_does_not_debit_twice(self):
        """The living actor stays untouched while a canonical reserve revives."""
        reserve = create_owned_pokemon(
            "Eevee", self.trainer, 50, nature="Hardy", ivs=[0] * 6, evs=[0] * 6
        )
        PlacementService(self.storage).to_party(reserve, slot=6)
        target = build_battle_pokemon_from_model(reserve)
        self.actor.pokemons.append(target)
        actor_hp = self.mon.hp
        for item in ["Revive", "Max Revive", "Revival Herb"]:
            target.hp = 0
            target.is_fainted = True
            action = self.use(item, target=target)
            reserve.refresh_from_db()
            expected = target.max_hp // 2 if item == "Revive" else target.max_hp
            self.assertEqual((target.hp, reserve.current_hp), (expected, expected))
            self.assertFalse(target.is_fainted)
            self.assertEqual(self.mon.hp, actor_hp)
            self.battle.execute_item(action)
            self.assertEqual(self.trainer.get_item_quantity(item), 1)

    def test_pp_selected_slot_and_all_moves_use_boosted_caps(self):
        """Selected canonical move slots with gaps cannot refill another move."""
        slots = list(self.owned.activemoveslot_set.order_by("slot"))
        slots[1].slot = 4
        slots[1].save(update_fields=["slot"])
        MovePPBoost.objects.create(pokemon=self.owned, move=slots[1].move, bonus_pp=15)
        for item, expected in [
            ("Ether", [0, 10]),
            ("Max Ether", [0, 40]),
            ("Elixir", [10, 10]),
            ("Max Elixir", [35, 40]),
        ]:
            self.owned.activemoveslot_set.update(current_pp=0)
            self.mon = build_battle_pokemon_from_model(self.owned)
            self.actor.pokemons = self.actor.active = [self.mon]
            self.use(item, move="4" if "Ether" in item else None)
            self.assertEqual(
                list(
                    self.owned.activemoveslot_set.order_by("slot").values_list(
                        "current_pp", flat=True
                    )
                ),
                expected,
            )
            self.assertEqual(self.trainer.get_item_quantity(item), 1)

    def test_failed_durable_write_rolls_back_medicine_and_inventory(self):
        """No inventory debit or snapshot mutation can escape a failed save."""
        self.mon.hp = 1
        self.trainer.add_item("Energy Root", 1)
        action = Action(
            self.actor,
            ActionType.ITEM,
            self.actor,
            item="Energy Root",
            pokemon=self.mon,
            target_pokemon=self.mon,
        )
        with patch.object(OwnedPokemon, "save", side_effect=RuntimeError("isolated write failure")):
            self.battle.execute_item(action)
        self.assertEqual(self.mon.hp, 1)
        self.assertEqual(self.trainer.get_item_quantity("Energy Root"), 1)

    def test_failed_second_pp_write_rolls_back_all_slots_and_debit(self):
        """Elixirs commit the entire effect or none of it."""
        self.owned.activemoveslot_set.update(current_pp=0)
        self.trainer.add_item("Elixir", 1)
        count = 0
        original = ActiveMoveslot.save

        def fail_second(slot, *args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("isolated second slot failure")
            return original(slot, *args, **kwargs)

        with patch.object(ActiveMoveslot, "save", fail_second):
            self.battle.execute_item(
                Action(
                    self.actor,
                    ActionType.ITEM,
                    self.actor,
                    item="Elixir",
                    pokemon=self.mon,
                    target_pokemon=self.mon,
                )
            )
        self.assertEqual(
            list(self.owned.activemoveslot_set.values_list("current_pp", flat=True)), [0, 0]
        )
        self.assertEqual(self.trainer.get_item_quantity("Elixir"), 1)

    def test_boxed_egg_foreign_and_healthy_targets_do_not_consume(self):
        """Fresh placement and owner guards run again at execution."""
        self.mon.hp = 1
        for invalid in ["boxed", "egg", "foreign"]:
            with self.subTest(invalid=invalid):
                if invalid == "boxed":
                    PlacementService(self.storage).to_box(self.owned)
                elif invalid == "egg":
                    self.owned.is_egg = True
                    self.owned.save(update_fields=["is_egg"])
                else:
                    self.actor.pokemons = []
                before = self.trainer.get_item_quantity("Potion")
                self.use("Potion")
                self.assertEqual(self.mon.hp, 1)
                self.assertEqual(self.trainer.get_item_quantity("Potion"), before + 2)
                if invalid == "boxed":
                    PlacementService(self.storage).to_party(self.owned, slot=3)
        self.actor.pokemons = [self.mon]
        self.owned.is_egg = False
        self.owned.save(update_fields=["is_egg"])
        self.mon.hp = self.mon.max_hp
        before = self.trainer.get_item_quantity("Potion")
        self.use("Potion")
        self.assertEqual(self.trainer.get_item_quantity("Potion"), before + 2)

    def test_outer_turn_transaction_observes_revived_runtime_before_saving(self):
        """Turn faint processing and checkpoint saves must see the revival now."""
        from django.db import transaction

        reserve = create_owned_pokemon(
            "Eevee", self.trainer, 50, nature="Hardy", ivs=[0] * 6, evs=[0] * 6
        )
        PlacementService(self.storage).to_party(reserve, slot=6)
        reserve.current_hp = 0
        reserve.save(update_fields=["current_hp"])
        target = build_battle_pokemon_from_model(reserve)
        self.actor.pokemons.append(target)
        with transaction.atomic():
            self.use("Revival Herb", target=target)
            self.assertEqual(target.hp, target.max_hp)
            self.battle.run_faint()
            self.assertFalse(target.is_fainted)
            BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=self.battle))
        reserve.refresh_from_db()
        self.assertEqual(reserve.current_hp, target.max_hp)
        self.assertEqual(reserve.friendship, 55)

    def test_outer_turn_pp_restoration_precedes_subsequent_spending(self):
        """A late on-commit restore cannot overwrite PP spent later in the turn."""
        from django.db import transaction

        self.owned.activemoveslot_set.update(current_pp=0)
        self.mon = build_battle_pokemon_from_model(self.owned)
        self.actor.pokemons = self.actor.active = [self.mon]
        with transaction.atomic():
            self.use("Ether", move="Tackle")
            move = next(m for m in self.mon.moves if m.name.lower() == "tackle")
            self.assertEqual(move.pp, 10)
            self.battle.reduce_move_pp(self.mon, move, 1)
            self.assertEqual(move.pp, 9)
            BattleSession._sync_player_pokemon_state(SimpleNamespace(battle=self.battle))
        self.assertEqual(move.pp, 9)
        self.assertEqual(self.owned.activemoveslot_set.get(move__name="Tackle").current_pp, 9)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command

        with patch.object(evennia, "Command", Command):
            from pokemon.battle.battleinstance import BattleSession
        from evennia.objects.models import ObjectDB
        from pokemon.battle.battledata import Pokemon
        from pokemon.battle.engine import Action, ActionType, Battle, BattleParticipant, BattleType
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot, MovePPBoost
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.placement import PlacementService
        from utils.pokemon_utils import build_battle_pokemon_from_model

        unittest.main(verbosity=2)
