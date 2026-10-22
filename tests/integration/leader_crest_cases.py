"""Ordinary challenge/attack/progress/evolve flows on disposable PostgreSQL."""

import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

WALKTHROUGH = []


class PlayerView(SessionTransport):
    """Capture transport while using real complete-ID and party lookups."""

    def get_pokemon_by_id(self, value):
        """Use production owner validation."""
        return User.get_pokemon_by_id(self, value)

    def get_active_pokemon_by_slot(self, slot):
        """Use the normal player party lookup for Rare Candy."""
        return User.get_active_pokemon_by_slot(self, slot)

    def has_item(self, name, quantity=1):
        """Use real capture inventory checks."""
        return User.has_item(self, name, quantity)

    def remove_item(self, name, quantity=1):
        """Debit capture inventory through production ownership checks."""
        return User.remove_item(self, name, quantity)


class LeaderCrestCases(unittest.TestCase):
    """Exercise real battle receipts, complete player routes and failed writes."""

    def setUp(self):
        """Create a new owner, native Bisharp, room and authored leader NPC."""
        character = ObjectDB.objects.create(db_key="crest-player-" + uuid4().hex)
        self.trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        self.storage = UserStorage.objects.create(user=character)
        self.player = PlayerView(character, self.trainer, self.storage)
        self.player.pk = character.pk
        room = ObjectDB.objects.create(db_key="crest-room-" + uuid4().hex)
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, name=room.key,
                                    db=room.db, ndb=room.ndb, attributes=room.attributes, contents=[])
        self.player.location = self.room
        self.mon = create_owned_pokemon(
            "Bisharp", self.trainer, 52, ability="Defiant", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, held_item="Leftovers", active_move_names=["Brick Break"],
        )
        PlacementService(self.storage).to_party(self.mon, slot=3)
        self.npc_trainer = NPCTrainer.objects.create(name="Crest trainer " + uuid4().hex[:8])
        self.template = NPCPokemonTemplate.objects.create(
            npc_trainer=self.npc_trainer, species="Bisharp", level=5, template_key="leader",
            sort_order=1, ability="Defiant", held_item="Leader's Crest", nature="Hardy",
            ivs=[0] * 6, evs=[0] * 6, move_names=["Splash"],
        )
        npc = ObjectDB.objects.create(db_key=self.npc_trainer.name)
        ObjectDB.objects.filter(pk=npc.pk).update(db_location=room)
        self.npc = SimpleNamespace(id=npc.pk, pk=npc.pk, key=npc.key, db=npc.db, ndb=npc.ndb,
                                   attributes=npc.attributes, location=self.room)
        self.room.contents = [self.npc, self.player]
        self.npc.db.npc_trainer_id = self.npc_trainer.pk
        self.npc.db.trainer_challenge = {"enabled": True, "cooldown_seconds": 0}
        self.player.search = lambda name, candidates: self.npc
        self.search = patch("pokemon.battle.battleinstance.search_object", self.find)
        self.search.start()
        self.npc_search = patch("evennia.utils.search.search_object", self.find)
        self.npc_search.start()
        self.session = None
        self.trainer.add_item("Leader's Crest", 2)

    def tearDown(self):
        """End only this fixture's retained battle."""
        if self.session and self.session.battle_id in (self.room.db.battles or []):
            self.session.end()
        self.search.stop()
        self.npc_search.stop()

    def find(self, query):
        """Resolve real model-backed transport identities after reconnect."""
        return [obj for obj in (self.player, self.npc) if query == f"#{obj.id}"]

    def command(self, kind, args=""):
        """Invoke shipped parsing/func boundaries, adapting only system transport."""
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller, command.args, command.cmdstring = self.player, args, "+" + kind
        command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        return self.player.messages[-1]

    def row(self):
        """Bypass the shared identity map."""
        return OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()

    def progress(self, mon=None):
        """Read current private structured server evidence."""
        return LeaderCrestProgress.read(self.player, mon or self.mon)

    def start(self):
        """Enter through ordinary +challenge and real static encounter generation."""
        self.command("challenge", self.npc.key)
        self.session = self.player.ndb.battle_instance
        self.assertIsNotNone(self.session, self.player.messages)
        return self.session

    def rebuild(self):
        """Discard runtime references and reconstruct the production checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        self.player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    def attack(self):
        """Require the real move, faint/result path and saved turn to succeed."""
        self.last_battle = self.session.battle
        self.command("attack", "Brick Break")
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.last_battle.participants[1].pokemons[0].hp, 0)
        return self.last_battle

    def win(self):
        """Complete one fresh ordinary challenge with a real lethal move."""
        self.start()
        return self.attack()

    def start_wild(self, reserve=False):
        """Control encounter selection while retaining real wild rows and turns."""
        self.session = BattleSession(self.player)
        leader = create_battle_pokemon("Bisharp", 5, is_wild=True, move_names=["Splash"])
        EncounterPokemon.objects.filter(pk=leader.model_id.split(":", 1)[1]).update(held_item="Leader's Crest")
        leader.item = "Leader's Crest"
        team = [leader]
        if reserve:
            team.append(create_battle_pokemon("Snorlax", 5, is_wild=True, move_names=["Splash"]))
        self.session._pending_opponent_team = team
        self.session._track_temp_opponent_team(team)
        self.session._select_opponent = lambda: (leader, "Wild leader", BattleType.WILD, "Fixture wild encounter")
        self.session.start()
        return self.session

    def qualify(self, count=3):
        """Count real distinct victories without directly seeding progress."""
        for _ in range(count):
            self.win()
        self.assertEqual(len(self.progress().leaders), count)

    def level_up(self):
        """Use the normal field Rare Candy route, separate from qualifying KOs."""
        self.trainer.add_item("Rare Candy")
        self.command("use", "Rare Candy=3")
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)

    def unchanged_evolution(self, suffix=""):
        """Rejected/ineffective evolution cannot consume a Crest or mutate rows."""
        before = self.row()
        quantity = self.trainer.get_item_quantity("Leader's Crest")
        self.command("evolve", str(self.mon.pk) + suffix)
        self.assertEqual(self.row(), before)
        self.assertEqual(self.trainer.get_item_quantity("Leader's Crest"), quantity)

    def preserved(self):
        """Record all unrelated Pokemon scalars, PP, placement and mirrors."""
        row = self.row()
        for field in ("species", "ability", "flags"):
            row.pop(field)
        return (row, list(ActiveMoveslot.objects.filter(pokemon=self.mon).values()),
                list(self.storage.placements.filter(pokemon=self.mon).values()),
                list(self.mon.active_slots.values()), list(self.mon.stored_users.values_list("pk", flat=True)),
                list(self.mon.boxes.values_list("pk", flat=True)))

    def flow(self, held_crest):
        """Discover, qualify in three fights, level and evolve the same ID."""
        detail = self.command("itemdex", "Leader's Crest")
        self.assertIn("Held Items", detail)
        self.assertIn("required or consumed", detail)
        self.assertIn("Leader's Crest", self.command("inventory"))
        if held_crest:
            self.command("hold", "3=Leader's Crest")
        else:
            self.trainer.remove_item("Leader's Crest", 2)
        held = self.row()["held_item"]
        quantity = self.trainer.get_item_quantity("Leader's Crest")
        records = []
        for count in range(1, 4):
            self.start()
            if count == 2:
                self.rebuild()
            self.attack()
            progress = self.progress()
            self.assertEqual(len(progress.leaders), count)
            sheet = self.command("party", "3")
            self.assertIn(f"{count}/3 leader victories", sheet)
            records.append({"count": count, "level_floor": progress.level_floor,
                            "battle_id": self.last_battle.reward_delivery.battle_id})
            self.unchanged_evolution()
        self.assertEqual(self.row()["level"], self.progress().level_floor)
        self.level_up()
        sheet = self.command("party", "3")
        self.assertIn("ready for +evolve", sheet)
        identifier = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", strip_ansi(sheet))
        self.assertIsNotNone(identifier)
        before = self.preserved()
        output = self.command("evolve", identifier.group())
        self.assertIn("evolved into Kingambit", output)
        self.assertEqual(self.row()["species"], "Kingambit")
        self.assertEqual(self.preserved(), before)
        self.assertEqual(self.row()["held_item"], held)
        self.assertEqual(self.trainer.get_item_quantity("Leader's Crest"), quantity)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.mon = OwnedPokemon.objects.get(pk=self.mon.pk)
        self.assertIn("Kingambit", self.command("party", "3"))
        self.unchanged_evolution()
        WALKTHROUGH.append({"held_crest": held_crest, "held_after": held,
                            "bag_after": quantity, "victories": records, "id": identifier.group(),
                            "commands": ["+challenge <authored leader NPC>", "+attack Brick Break",
                                         "repeat for three victories", "+party 3", "+use Rare Candy=3",
                                         "+evolve " + identifier.group(), "+party 3 after SQL reload"],
                            "evolution_output": output, "same_identity_state_and_placement": True})

    def test_player_flow_without_own_crest(self):
        """Real challenge/attack/evolve flow needs no player-owned Crest."""
        self.flow(False)

    def test_player_flow_preserves_equipped_and_bag_crests(self):
        """An equipped Crest remains held by Kingambit and bag stock is unchanged."""
        self.flow(True)

    def test_one_battle_three_distinct_leaders_count_only_at_victory(self):
        """Different foe identities in one roster count separately at completion."""
        for index in (2, 3):
            NPCPokemonTemplate.objects.create(
                npc_trainer=self.npc_trainer, species="Bisharp", level=5, sort_order=index,
                template_key=str(index), ability="Defiant", held_item="Leader's Crest",
                ivs=[0] * 6, evs=[0] * 6, move_names=["Splash"],
            )
        self.start()
        for _ in range(2):
            self.attack()
            self.assertFalse(self.progress().leaders)
        self.rebuild()
        self.attack()
        self.assertEqual(len(self.progress().leaders), 3)

    def test_stale_checkpoint_and_completed_receipt_replay_do_not_count_twice(self):
        """A pre-attack snapshot and repeated end cannot duplicate a real leader."""
        self.start()
        data, state = self.session.data.to_dict(), self.session.state.to_dict()
        self.attack()
        self.assertEqual(len(self.progress().leaders), 1)
        # Recreate an old session only inside this test room; receipts stay real.
        self.session._ended = False
        self.session.logic = BattleLogic.from_dict({"data": data, "state": state})
        own = self.session.battle.participants[0]
        own.player = self.player
        self.session._bind_reward_delivery()
        # The normal room state was cleaned, so replay the old checkpoint first.
        self.session._persist_turn_state()
        self.player.ndb.battle_instance = self.session
        self.player.db.battle_lock = self.player.db.battle_id = self.session.battle_id
        self.player.db.battle_control = True
        self.room.db.battles = [self.session.battle_id]
        self.command("attack", "Brick Break")
        self.assertEqual(len(self.progress().leaders), 1)
        self.assertNotIn(self.session.battle_id, self.room.db.battles or [])

    def test_fake_flags_and_bag_item_do_not_grant_eligibility(self):
        """Actual private receipts are required even at level 100."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(level=100, flags=["kingambit:3", "leader:3"])
        self.unchanged_evolution()
        self.unchanged_evolution(" Leader's Crest")
        self.assertFalse(self.progress().leaders)

    def test_two_victories_and_early_level_up_are_insufficient(self):
        """The next required level is based on the third KO, not the first."""
        self.qualify(2)
        self.level_up()
        self.unchanged_evolution()
        self.win()
        self.assertEqual(self.progress().level_floor, self.row()["level"])
        self.unchanged_evolution()
        self.level_up()
        self.assertIn("evolved into Kingambit", self.command("evolve", str(self.mon.pk)))

    def test_third_ko_exp_can_supply_the_required_level(self):
        """The finishing blow's normal EXP can satisfy its own next-level gate."""
        self.qualify(2)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(total_exp=exp_for_level(53) - 1)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.win()
        self.assertEqual(self.progress().level_floor, 52)
        self.assertEqual(self.row()["level"], 53)
        self.assertIn("evolved into Kingambit", self.command("evolve", str(self.mon.pk)))

    def test_later_victories_do_not_raise_a_completed_threshold(self):
        """Three distinct identities saturate even after another level and win."""
        self.qualify()
        before = self.progress()
        self.level_up()
        self.win()
        self.assertEqual(self.progress(), before)
        self.assertIn("evolved into Kingambit", self.command("evolve", str(self.mon.pk)))

    def test_evidence_is_bound_to_the_actual_owned_pokemon_and_owner(self):
        """A second Bisharp and another trainer cannot borrow qualifying history."""
        self.qualify()
        self.level_up()
        second = create_owned_pokemon("Bisharp", self.trainer, 53, ivs=[0] * 6, evs=[0] * 6)
        with self.assertRaises(EvolutionError):
            EvolutionService(self.player).evolve(second)
        character = ObjectDB.objects.create(db_key="foreign-crest-" + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        foreign = PlayerView(character, trainer, UserStorage.objects.create(user=character))
        foreign.pk, foreign.location = character.pk, self.room
        before = self.row()
        with self.assertRaises(EvolutionError):
            EvolutionService(foreign).evolve(self.mon)
        self.assertEqual(self.row(), before)
        self.assertFalse(LeaderCrestProgress.read(foreign, self.mon).leaders)

    def test_wild_leader_win_uses_the_same_committed_qualification(self):
        """A real wild source and real finishing move qualify once."""
        self.start_wild()
        self.rebuild()
        self.attack()
        self.assertEqual(len(self.progress().leaders), 1)

    def test_flee_after_real_leader_ko_does_not_qualify(self):
        """Provisional leader defeat is discarded when the encounter is fled."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Smoke Ball")
        OwnedPokemon.flush_cached_instance(self.mon)
        self.start_wild(reserve=True)
        battle = self.attack()
        self.command("flee")
        self.assertTrue(battle._flee_result["success"])
        self.assertFalse(self.progress().leaders)

    def test_capture_after_real_leader_ko_does_not_qualify(self):
        """Capturing a remaining opponent is distinct from a committed KO victory."""
        self.trainer.add_item("Master Ball")
        self.start_wild(reserve=True)
        battle = self.attack()
        self.command("item", "Master Ball")
        self.assertTrue(battle.capture_succeeded, self.player.messages)
        self.assertFalse(self.progress().leaders)

    def test_scripted_or_no_progression_fight_does_not_qualify(self):
        """A controlled non-progressing encounter cannot manufacture history."""
        for scripted in (False, True):
            self.start()
            if scripted:
                self.session.battle.type = BattleType.SCRIPTED
            else:
                self.session.battle.award_xp = False
            self.attack()
            self.assertFalse(self.progress().leaders)

    def test_pvp_finishing_move_does_not_qualify(self):
        """A real opponent-owned Crest Bisharp supplies no leader encounter credit."""
        character = ObjectDB.objects.create(db_key="crest-pvp-" + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        opponent = PlayerView(character, trainer, UserStorage.objects.create(user=character))
        opponent.pk, opponent.location = character.pk, self.room
        create_owned_pokemon("Bisharp", trainer, 5, held_item="Leader's Crest",
                             ivs=[0] * 6, evs=[0] * 6, active_move_names=["Splash"])
        self.room.contents.append(opponent)
        self.session = BattleSession(self.player, opponent)
        self.session.start()
        battle = self.session.battle
        self.command("attack", "Brick Break")
        self.session.queue_move("Splash", caller=opponent)
        self.session.maybe_run_turn()
        self.assertEqual(battle.participants[1].pokemons[0].hp, 0)
        self.assertTrue(battle.battle_over)
        self.assertFalse(self.progress().leaders)

    def test_foreign_owned_reference_cannot_receive_personal_ko_credit(self):
        """Runtime references still require matching authoritative ownership."""
        character = ObjectDB.objects.create(db_key="crest-foreign-ref-" + uuid4().hex)
        trainer = Trainer.objects.create(user=character, trainer_number=Trainer.objects.count() + 1)
        other = create_owned_pokemon("Bisharp", trainer, 52, ivs=[0] * 6, evs=[0] * 6)
        self.start()
        self.session.battle.participants[0].active[0].model_id = "owned:" + str(other.pk)
        # Read candidate at the real faint boundary, before ordinary reward owner
        # validation rejects a foreign EXP recipient and rolls the turn back.
        observed = []
        original = LeaderCrestProgress.candidate

        def capture(battle, target):
            result = original(battle, target)
            observed.append(result)
            return result

        with patch.object(LeaderCrestProgress, "candidate", capture):
            self.command("attack", "Brick Break")
        self.assertTrue(observed)
        self.assertTrue(all(value is None for value in observed))
        self.assertFalse(self.progress().leaders)
        self.session.end()

    def test_wrong_encounter_identity_or_missing_crest_is_not_a_leader(self):
        """Neither wrong species nor no original Crest qualifies."""
        for species, item in (("Bisharp", ""), ("Pawniard", "Leader's Crest")):
            NPCPokemonTemplate.objects.filter(pk=self.template.pk).update(species=species, held_item=item)
            self.win()
            self.assertFalse(self.progress().leaders)

    def test_runtime_given_crest_cannot_manufacture_original_leader(self):
        """Server encounter identity is distinct from a moved-in runtime item."""
        NPCPokemonTemplate.objects.filter(pk=self.template.pk).update(held_item="")
        self.start()
        self.session.battle.participants[1].active[0].item = "Leader's Crest"
        self.attack()
        self.assertFalse(self.progress().leaders)

    def test_removed_crest_or_transformed_holder_does_not_qualify(self):
        """Runtime native identity and physical Crest are both required."""
        self.start()
        self.session.battle.participants[1].active[0].item = ""
        self.attack()
        self.assertFalse(self.progress().leaders)
        self.start()
        self.session.battle.participants[0].active[0].transformed = True
        self.attack()
        self.assertFalse(self.progress().leaders)

    def test_suppression_does_not_remove_physical_crest_identity(self):
        """The opponent's qualification is possession, not an active held effect."""
        self.start()
        self.session.battle.participants[1].active[0].item_suppressed = True
        self.attack()
        self.assertEqual(len(self.progress().leaders), 1)

    def test_another_owned_attacker_does_not_credit_benched_bisharp(self):
        """Personal final-blow attribution is independent of EXP Share."""
        other = create_owned_pokemon("Pangoro", self.trainer, 52, nature="Hardy",
                                     ivs=[0] * 6, evs=[0] * 6, active_move_names=["Brick Break"])
        PlacementService(self.storage).to_party(other, slot=1)
        self.player.db.exp_share = True
        self.win()
        self.assertFalse(self.progress().leaders)

    def test_no_attribution_residual_and_faint_replay_cannot_create_candidate(self):
        """Manually fainting an opponent grants no personal finishing-move proof."""
        self.start()
        foe = self.session.battle.participants[1].active[0]
        foe.hp = 0
        self.session.battle.run_faint()
        self.session.battle.run_faint()
        self.session.battle.check_win_conditions()
        self.session.end()
        self.assertFalse(self.progress().leaders)

    def test_aborted_or_lost_session_does_not_commit_provisional_ko(self):
        """A real first KO remains uncredited without a final victory."""
        NPCPokemonTemplate.objects.create(
            npc_trainer=self.npc_trainer, species="Snorlax", level=5, sort_order=2,
            template_key="reserve", ivs=[0] * 6, evs=[0] * 6, move_names=["Splash"],
        )
        self.start()
        self.attack()
        self.assertFalse(self.progress().leaders)
        self.session.end()
        self.assertFalse(self.progress().leaders)
        self.start()
        self.attack()
        for mon in self.session.battle.participants[0].pokemons:
            mon.hp = 0
        self.session.battle.run_faint()
        self.session.battle.check_win_conditions()
        self.session.end()
        self.assertFalse(self.progress().leaders)

    def test_failed_victory_record_retains_session_then_retry_counts_once(self):
        """An outage cannot delete the only committed KO/result evidence."""
        self.start()
        original = BattleRewards.record

        def fail_record(delivery, player, event, payload):
            """Inject only the new terminal effect's durable plan write."""
            if event == EVENT:
                raise RuntimeError("crest result record unavailable")
            return original(delivery, player, event, payload)

        with patch.object(BattleRewards, "record", fail_record):
            self.attack()
        self.assertIn(self.session.battle_id, self.room.db.battles)
        self.assertFalse(self.progress().leaders)
        self.rebuild()
        self.command("battle/retry")
        self.assertEqual(len(self.progress().leaders), 1)
        self.command("battle/retry")
        self.assertEqual(len(self.progress().leaders), 1)

    def test_failed_progress_or_claim_marker_rolls_back_then_retry(self):
        """Evidence and its once-only marker commit in the same transaction."""
        for stage in ("evidence", "marker", "pending"):
            self.start()
            before = self.progress()
            original = AttributeHandler.add
            failed_writes = []
            markers = []

            def fail(handler, key, value, *args, **kwargs):
                """Fail after the private write or before its final claim marker."""
                if stage == "evidence" and kwargs.get("category") == CATEGORY:
                    failed_writes.append("evidence")
                    original(handler, key, value, *args, **kwargs)
                    raise RuntimeError("crest evidence write failed")
                if (kwargs.get("category") == REWARDS_CATEGORY
                        and value.get("event") == EVENT and value.get("claimed")):
                    markers.append(key)
                    if stage == "marker":
                        original(handler, key, value, *args, **kwargs)
                        failed_writes.append("marker")
                        raise RuntimeError("crest claim marker failed")
                if stage == "pending" and markers and key == PENDING_KEY:
                    original(handler, key, value, *args, **kwargs)
                    failed_writes.append("pending")
                    raise RuntimeError("crest pending index write failed")
                return original(handler, key, value, *args, **kwargs)

            with patch.object(AttributeHandler, "add", fail):
                self.attack()
            self.assertTrue(failed_writes, (stage, self.player.messages))
            self.assertEqual(self.progress(), before)
            self.assertTrue(self.player.db.battle_lock)
            self.rebuild()
            self.command("battle/retry")
            self.assertEqual(len(self.progress().leaders), len(before.leaders) + 1)

    def test_checkpoint_failure_rolls_back_ko_and_progress_before_retry(self):
        """A failed complete-turn checkpoint cannot publish qualifying evidence."""
        self.start()
        original = self.session.storage.set

        def fail(key, value):
            if key == "state":
                raise RuntimeError("crest checkpoint unavailable")
            return original(key, value)

        # Persist actual player/AI inputs before injecting the complete-turn failure.
        with patch.object(self.session, "maybe_run_turn"):
            self.command("attack", "Brick Break")
        self.session._auto_queue_ai_actions()
        with patch.object(self.session.storage, "set", fail), self.assertRaises(RuntimeError):
            self.session.execute_persistent_turn()
        self.assertFalse(self.progress().leaders)
        self.assertFalse(BattleRewards.pending(self.player))
        self.command("battle/retry")
        self.assertEqual(len(self.progress().leaders), 1)

    def test_failed_evolution_save_preserves_evidence_and_every_saved_field(self):
        """Private qualification is not consumed by a failed transition."""
        self.qualify()
        self.level_up()
        before, evidence = self.row(), self.progress()
        original = OwnedPokemon.save

        def fail_after_save(mon, *args, **kwargs):
            original(mon, *args, **kwargs)
            raise RuntimeError("crest evolution save failed")

        with patch.object(OwnedPokemon, "save", fail_after_save):
            self.command("evolve", str(self.mon.pk))
        self.assertEqual(self.row(), before)
        self.assertEqual(self.progress(), evidence)
        self.assertEqual(self.mon.species, "Bisharp")
        self.assertIn("evolved into Kingambit", self.command("evolve", str(self.mon.pk)))

    def test_everstone_egg_reservation_and_battle_guard_remain(self):
        """Private readiness cannot bypass the shared lifecycle guards."""
        self.qualify()
        self.level_up()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Everstone")
        self.unchanged_evolution()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="", is_egg=True)
        self.unchanged_evolution()
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=False)
        self.player.db.battle_lock = "fixture"
        self.unchanged_evolution()
        self.player.db.battle_lock = None
        PlacementService(self.storage).reserve_for_fusion(self.mon)
        self.unchanged_evolution()

    def race(self, *actions):
        """Run real competing claims/evolutions on independent PG connections."""
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_concurrent_claims_of_one_real_victory_increment_once(self):
        """The original receipt lock protects duplicate recovery requests."""
        self.start()
        with patch.object(LeaderCrestProgress, "apply", side_effect=RuntimeError("retain pending claim")):
            self.attack()
        key = next(key for key in BattleRewards.pending(self.player)
                   if self.player.attributes.get(key, category=REWARDS_CATEGORY)["event"] == EVENT)
        delivery = BattleRewards(key.split(":", 1)[0])
        self.assertCountEqual(self.race(lambda: delivery.claim(self.player, key),
                                        lambda: delivery.claim(self.player, key)), [True, False])
        self.assertEqual(len(self.progress().leaders), 1)
        self.session.end()

    def test_concurrent_qualified_evolutions_keep_identity_and_consume_nothing(self):
        """The existing evolution receipt and storage lock serialize completion."""
        self.qualify()
        self.level_up()
        action = lambda: EvolutionService(self.player).evolve(self.mon)
        self.assertCountEqual(self.race(action, action), ["Kingambit", None])
        self.assertEqual(self.row()["species"], "Kingambit")
        self.assertEqual(self.trainer.get_item_quantity("Leader's Crest"), 2)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (cmd_battle_attack, cmd_battle_flee, cmd_battle_item, cmd_battle_retry, cmd_challenge,
                                         cmd_inventory, cmd_learn_evolve, cmd_party, cmd_pokedex, cmd_sheet)
        from django.db import close_old_connections, connections
        from evennia.objects.models import ObjectDB
        from evennia.typeclasses.attributes import AttributeHandler
        from evennia.utils.ansi import strip_ansi
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.logic import BattleLogic
        from pokemon.battle.engine import BattleType
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import EncounterPokemon, OwnedPokemon
        from pokemon.models.stats import exp_for_level
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import UserStorage
        from pokemon.models.trainer import NPCPokemonTemplate, NPCTrainer, Trainer
        from pokemon.services.battle_rewards import BattleRewards, CATEGORY as REWARDS_CATEGORY, PENDING_KEY
        from pokemon.services.evolution import EvolutionError, EvolutionService
        from pokemon.services.leader_crest import CATEGORY, EVENT, LeaderCrestProgress
        from pokemon.services.placement import PlacementService
        from pokemon.user import User

        COMMANDS = {"challenge": (cmd_challenge, cmd_challenge.CmdChallenge),
                    "attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                    "flee": (cmd_battle_flee, cmd_battle_flee.CmdBattleFlee),
                    "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                    "battle/retry": (cmd_battle_retry, cmd_battle_retry.CmdBattleRetry),
                    "evolve": (cmd_learn_evolve, cmd_learn_evolve.CmdEvolvePokemon),
                    "party": (cmd_sheet, cmd_sheet.CmdSheetPokemon),
                    "hold": (cmd_party, cmd_party.CmdSetHoldItem),
                    "inventory": (cmd_inventory, cmd_inventory.CmdInventory),
                    "itemdex": (cmd_pokedex, cmd_pokedex.CmdItemdexSearch),
                    "use": (cmd_inventory, cmd_inventory.CmdUseItem)}
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LeaderCrestCases))
        print("LEADER_CREST_PLAYER_WALKTHROUGH " + json.dumps(WALKTHROUGH))
        raise SystemExit(not result.wasSuccessful())
