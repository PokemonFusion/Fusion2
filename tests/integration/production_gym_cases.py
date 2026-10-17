"""Production gym launch, strategy, progression policy and recovery on PostgreSQL."""

from __future__ import annotations

import random
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView


class ProductionGymCases(unittest.TestCase):
    """Keep models, transactions, commands and engine turns real; capture transport."""

    def setUp(self):
        """Give each case a fresh ordinary trainer and a canonical fast doubles party."""
        self.profile = seed_production_gym_content().profile
        character = ObjectDB.objects.create(db_key="Tempo QA " + uuid4().hex[:8])
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1, money=100)
        self.player = PlayerView(character, trainer, UserStorage.objects.create(user=character))
        room = ObjectDB.objects.create(db_key="Tempo test room " + uuid4().hex[:8])
        self.room = SimpleNamespace(id=room.pk, key=room.key, db=room.db, ndb=room.ndb,
                                    attributes=room.attributes, contents=[self.player])
        self.player.location = self.room
        self.owned = [create_owned_pokemon(species, trainer, 50, ivs=[0] * 6, evs=[0] * 6,
                                          nature="Hardy", active_move_names=["Tackle"] if species == "Eevee" else ["Tackle", "Thunderbolt"])
                      for species in ("Jolteon", "Electrode", "Eevee")]
        self.session = None
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()

    def tearDown(self):
        """Release only the disposable case's session and transport patch."""
        if self.session and not getattr(self.session, "_ended", False):
            self.session.end()
        self.search.stop()
        seed_production_gym_content()

    def find(self, query):
        """Resolve only this ordinary player while retaining real ORM records."""
        return [self.player] if str(query).lstrip("#") == str(self.player.id) else []

    def command(self, args):
        """Run the registered player command with captured session output."""
        command = CmdGym()
        command.caller, command.args = self.player, args
        command.func()
        return self.player.messages[-1]

    def start(self):
        """Start from durable configuration through the production launch service."""
        self.session, encounter = GymChallenge(self.player, GYM_KEY).start()
        self.session.battle.rng = random.Random(5)
        return encounter

    def rebuild(self):
        """Drop transport references and reconstruct the actual saved room checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)

    def advance(self, move="Thunderbolt"):
        """Submit each player's actual legal attack declaration for a complete turn."""
        for actor in list(self.session.choices_for(self.player).positions()):
            if getattr(self.session, "_ended", False):
                break
            positions = self.session.data.turndata.positions
            target = next(name for name, position in positions.items()
                          if name.startswith("B") and position.pokemon and position.pokemon.hp > 0)
            learned = {entry.name for entry in positions[actor].pokemon.moves}
            chosen = move if move in learned else "Tackle"
            self.session.queue_move(chosen, target, caller=self.player, actor=actor)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)

    def win(self):
        """Win with ordinary move commands against the entire authored roster."""
        for _ in range(30):
            self.advance()
            if getattr(self.session, "_ended", False) or self.session.battle.battle_over:
                break
        else:
            self.fail("Production gym did not finish within 30 deterministic turns")
        self.assertTrue(GymVictory.objects.filter(player=self.player.character).exists(), self.player.messages[-15:])

    def progression(self):
        """Snapshot authoritative progression and inventory separately from battle resources."""
        self.player.trainer.refresh_from_db()
        for pokemon in self.owned:
            pokemon.refresh_from_db()
        return (self.player.trainer.money, self.player.db.trainer_xp, self.player.db.txp,
                [(pokemon.level, pokemon.total_exp, pokemon.evs) for pokemon in self.owned],
                list(self.player.trainer.inventory.values_list("item_name", "quantity")))

    def race(self, *actions):
        """Exercise competing calls on distinct PostgreSQL connections."""
        barrier = Barrier(len(actions))

        def worker(action):
            """Share only the barrier and restrict each connection to the test schema."""
            close_old_connections()
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                return pid, action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            futures = [pool.submit(worker, action) for action in actions]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(len({pid for pid, _ in results}), len(actions))
        return [result for _, result in results]

    def test_idempotent_and_concurrent_seed_preserves_progress_and_receipts(self):
        """Repeated installers reuse identities and never erase earned/pending awards."""
        self.player.trainer.add_badge(self.profile.badge)
        receipt = GymVictoryRewards(self.player).record(uuid4(), generate_gym_leader_encounter(self.profile).metadata)
        before = (self.profile.pk, self.profile.badge_id, self.profile.npc_trainer_id,
                  list(self.profile.npc_trainer.pokemon_templates.values_list("pk", flat=True)))
        results = self.race(lambda: seed_production_gym_content().profile.pk,
                            lambda: seed_production_gym_content().profile.pk)
        self.assertEqual(results, [before[0], before[0]])
        updated = seed_production_gym_content().profile
        self.assertEqual(before, (updated.pk, updated.badge_id, updated.npc_trainer_id,
                                 list(updated.npc_trainer.pokemon_templates.values_list("pk", flat=True))))
        self.assertEqual(updated.npc_trainer.pokemon_templates.count(), 3)
        self.assertEqual(self.player.trainer.badges.count(), 1)
        self.assertTrue(GymVictory.objects.filter(pk=receipt.pk, claimed_at__isnull=True).exists())
        for _ in range(2):
            encounter = generate_gym_leader_encounter(updated)
            self.assertTrue(all(mon.max_hp == get_max_hp(mon) for mon in encounter.team))

    def test_player_discovery_strategy_and_config_survive_rebuild(self):
        """Normal commands discover production content; both AI choices and room survive."""
        seed_alpha_gym_content()
        self.assertNotIn("alpha_gym", self.command("list"))
        self.assertIn(GYM_KEY, self.command("list"))
        self.assertIn("Trick Room", self.command("check " + GYM_KEY))
        self.assertIn("not available", self.command("challenge alpha_gym"))
        self.command("challenge " + GYM_KEY)
        self.session = self.player.ndb.battle_instance
        self.session.battle.rng = random.Random(5)
        npc = self.session.battle.participants[1]
        self.assertEqual(len(npc.pokemons), 3)
        self.session._auto_queue_ai_actions()
        self.assertEqual(len(npc.pending_action), 2)
        self.assertEqual([action.move.name for action in npc.pending_action].count("Trick Room"), 1)
        self.rebuild()
        self.advance(move="Tackle")
        self.assertTrue(self.session.battle.field.get_pseudo_weather("trickroom"))
        self.profile.ai_profile, self.profile.strategy_key, self.profile.reward_policy = "gym_leader", "", "legacy"
        self.profile.save()
        self.rebuild()
        self.assertEqual(self.session.battle.participants[1].ai_profile, "gym_trick_room")
        self.assertFalse(self.session.battle.award_xp or self.session.battle.award_txp or self.session.battle.award_prizes)
        self.assertTrue(self.session.battle.field.get_pseudo_weather("trickroom"))

    def test_full_first_clear_rematch_cooldown_and_no_farmable_progression(self):
        """First clear and rematch execute full engine battles with one total badge."""
        before = self.progression()
        self.start()
        self.win()
        victory = GymVictory.objects.get(player=self.player.character)
        self.assertEqual(victory.award_kind, "first_clear")
        self.assertIsNotNone(victory.claimed_at)
        self.assertEqual(self.progression(), before)
        self.assertEqual(self.player.trainer.badges.count(), 1)
        self.assertIn("cooldown", self.command("challenge " + GYM_KEY))
        victory.recorded_at -= timedelta(days=1, seconds=1)
        victory.save(update_fields=["recorded_at"])
        self.start()
        self.assertEqual(self.session.encounter_metadata["challenge_mode"], "rematch")
        self.rebuild()
        self.win()
        self.assertEqual(list(GymVictory.objects.filter(player=self.player.character).order_by("recorded_at")
                              .values_list("award_kind", flat=True)), ["first_clear", "rematch"])
        self.assertEqual(self.progression(), before)
        self.assertEqual(self.player.trainer.badges.count(), 1)
        self.assertIn("No unclaimed", self.command("claim"))
        self.assertIn("No unclaimed", self.command("claim"))

    def test_loss_concession_and_abort_award_nothing_and_allow_retry(self):
        """Non-victory terminal paths cannot later be replayed as a first clear."""
        before = self.progression()
        for mode in ("loss", "concede", "abort"):
            self.start()
            if mode == "loss":
                for pokemon in self.session.battle.participants[0].pokemons:
                    pokemon.hp = 0
                self.session.battle.run_faint()
                self.session._handle_battle_result(self.session.battle.participants[1])
                self.session.end()
            elif mode == "concede":
                command = CmdBattleConcede()
                command.caller, command.args = self.player, "yes"
                with patch("commands.player.cmd_battle_concede.get_system", return_value=SimpleNamespace(battle_manager=None)):
                    command.func()
            else:
                self.session.end()
            self.session._handle_battle_result(SimpleNamespace(team="A", player=self.player))
            self.assertFalse(GymVictory.objects.filter(player=self.player.character).exists())
            self.assertEqual(self.player.trainer.badges.count(), 0)
            self.assertEqual(self.progression(), before)
            for pokemon in self.owned:
                pokemon.heal()

    def test_pending_delivery_rollback_claim_and_replay(self):
        """A real badge write failure rolls back and ordinary +gym claim recovers it."""
        self.start()
        original = Trainer.add_badge

        def fail_after_badge(trainer, badge):
            """Raise after the actual many-to-many write to prove rollback."""
            original(trainer, badge)
            raise RuntimeError("injected post-badge failure")

        with patch.object(Trainer, "add_badge", fail_after_badge):
            self.win()
        victory = GymVictory.objects.get(player=self.player.character)
        self.assertIsNone(victory.claimed_at)
        self.assertEqual(victory.award_kind, "")
        self.assertEqual(self.player.trainer.badges.count(), 0)
        self.assertIn("pending", self.command("challenge " + GYM_KEY))
        self.assertIn("First clear complete", self.command("claim"))
        victory.refresh_from_db()
        self.assertEqual(victory.award_kind, "first_clear")
        self.assertEqual(self.player.trainer.badges.count(), 1)
        GymVictoryRewards(self.player).record(victory.pk, {**victory.metadata, "badge_id": -1})
        self.assertFalse(GymVictoryRewards(self.player).claim(victory.pk).awarded)
        self.assertEqual(GymVictory.objects.filter(player=self.player.character).count(), 1)

    def test_claim_marker_failure_retains_atomic_delivery_and_retry(self):
        """Claim-marker failure cannot leave a badge without a fulfilled receipt."""
        self.start()
        original = GymVictory.save

        def fail_claim(row, *args, **kwargs):
            """Keep initial ledger creation real and fail only the delivery marker."""
            if row.claimed_at is not None:
                raise RuntimeError("injected claim marker failure")
            return original(row, *args, **kwargs)

        with patch.object(GymVictory, "save", fail_claim):
            self.win()
        self.assertEqual(self.player.trainer.badges.count(), 0)
        self.assertIn("First clear complete", self.command("claim"))
        self.assertEqual(self.player.trainer.badges.count(), 1)

    def test_concurrent_claims_have_one_first_clear_and_immutable_results(self):
        """Different victories share the character lock and classify one first clear."""
        metadata = generate_gym_leader_encounter(self.profile).metadata
        ids = [GymVictoryRewards(self.player).record(uuid4(), metadata).pk for _ in range(2)]
        results = self.race(*(lambda key=key: GymVictoryRewards(self.player).claim(key) for key in ids))
        self.assertEqual(sum(result.awarded for result in results), 1)
        self.assertEqual(sorted(result.award_kind for result in results), ["first_clear", "rematch"])
        for key in ids:
            self.assertFalse(GymVictoryRewards(self.player).claim(key).awarded)
        self.assertEqual(self.player.trainer.badges.count(), 1)

    def test_concurrent_launches_start_only_one_battle(self):
        """Eligibility plus battle allocation is serialized on the same character row."""
        def launch():
            """Return the specific ordinary eligibility failure for the losing launch."""
            try:
                return GymChallenge(self.player, GYM_KEY).start()[0]
            except GymLeaderError as error:
                return str(error)

        results = self.race(launch, launch)
        sessions = [result for result in results if not isinstance(result, str)]
        self.assertEqual(len(sessions), 1, results)
        self.session = sessions[0]
        self.assertIn("current battle", next(result for result in results if isinstance(result, str)))

    def test_constructor_and_post_start_failure_roll_back_then_allow_retry(self):
        """No generated roster, lock or checkpoint survives either startup failure."""
        initial = EncounterPokemon.objects.count()
        for method in ("__init__", "start_trainer_encounter"):
            original = getattr(BattleSession, method)

            def fail_after(session, *args, **kwargs):
                """Fail after real writes and runtime registration have occurred."""
                original(session, *args, **kwargs)
                raise RuntimeError("injected startup failure")

            with patch.object(BattleSession, method, fail_after), self.assertRaises(RuntimeError):
                GymChallenge(self.player, GYM_KEY).start()
            self.assertEqual(EncounterPokemon.objects.count(), initial)
            self.assertIsNone(self.player.db.battle_id)
            self.assertIsNone(self.player.ndb.battle_instance)
            self.start()
            self.session.end()

    def test_invalid_configuration_and_small_party_allocate_nothing(self):
        """Invalid strategy and insufficient conscious actors fail before allocation."""
        initial = EncounterPokemon.objects.count()
        self.profile.strategy_key = "weather"
        self.profile.save(update_fields=["strategy_key"])
        with self.assertRaises(GymLeaderError):
            GymChallenge(self.player, GYM_KEY).start()
        seed_production_gym_content()
        for pokemon in self.owned[1:]:
            pokemon.current_hp = 0
            pokemon.save(update_fields=["current_hp"])
        with self.assertRaisesRegex(GymLeaderError, "two|2"):
            GymChallenge(self.player, GYM_KEY).start()
        self.assertEqual(EncounterPokemon.objects.count(), initial)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from django.db import close_old_connections, connection, connections
        from evennia.commands.cmdset import CmdSet
        from evennia.commands.command import Command
        from evennia.objects.models import ObjectDB

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player.cmd_battle_concede import CmdBattleConcede
            from commands.player.cmd_gym import CmdGym
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon, get_max_hp
        from pokemon.models.core import EncounterPokemon
        from pokemon.models.gym import GymVictory
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import Trainer
        from pokemon.services.alpha_gym_seed import seed_alpha_gym_content
        from pokemon.services.gym_challenges import GymChallenge
        from pokemon.services.gym_leaders import GymLeaderError, generate_gym_leader_encounter
        from pokemon.services.gym_rewards import GymVictoryRewards
        from pokemon.services.production_gym_seed import GYM_KEY, seed_production_gym_content

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProductionGymCases))
        raise SystemExit(not result.wasSuccessful())
