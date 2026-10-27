"""Fresh egg-roster reproductions through persistent normal player commands."""

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE, run


class EggRosterCases(BattlePlayerFixture):
    """Keep eggs in custody while checking battle rosters, switches and recovery."""

    def prepare(self):
        """Label an unhatched party egg and a genuine depleted reserve as setup."""
        from pokemon.models.core import OwnedPokemon

        self.egg = self.add(0, "Eevee", ["Tackle"], ability="Run Away", slot=1, level=1)
        OwnedPokemon.objects.filter(pk=self.egg.pk).update(is_egg=True)
        self.egg.refresh_from_db()
        self.live = self.add(0, "Quagsire", ["Tail Whip", "Water Gun"], ability="Damp", slot=3)
        self.reserve = self.add(0, "Mew", ["Safeguard"], ability="Synchronize", slot=5)
        OwnedPokemon.objects.filter(pk=self.reserve.pk).update(current_hp=0)
        self.reserve.refresh_from_db()
        self.foe = self.add(1, "Mew", ["Safeguard"], ability="Synchronize", slot=4)
        EVIDENCE.append({"case": self.id(), "label": "separate-egg-and-hp0-prerequisites",
                         "after": self.snapshot()})

    def test_mixed_roster_keeps_fainted_reserve_and_canonical_holes(self):
        """An egg in slot one cannot lead, switch, or poison the guarded whole roster."""
        from pokemon.battle.owned_battle_actor import OwnedBattleActor
        from pokemon.helpers.party_helpers import get_battle_switch_choices
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        before = OwnedPokemon.objects.filter(pk=self.egg.pk).values().get()
        self.launch()
        part = self.session.battle.participants[0]
        egg_ref = "owned:" + str(self.egg.pk)
        # Retain the actual pre-fix checkpoint/SQL even when this assertion fails.
        EVIDENCE.append({"case": self.id(), "label": "fresh-mixed-roster-observation",
                         "egg_ref": egg_ref, "after": self.snapshot()})
        for mon in part.pokemons:
            if mon.model_id == egg_ref:
                from pokemon.battle.owned_battle_actor import BattleOwnershipChanged
                with self.assertRaises(BattleOwnershipChanged) as error:
                    with OwnedBattleActor.locked(self.session.battle, part, mon, active=False):
                        pass
                EVIDENCE.append({"case": self.id(), "label": "fresh-owned-egg-guard-refusal",
                                 "error": str(error.exception), "after": self.snapshot()})
        self.assertNotIn(egg_ref, [p.model_id for p in part.pokemons])
        self.assertEqual(part.active[0].model_id, "owned:" + str(self.live.pk))
        self.assertIn("owned:" + str(self.reserve.pk), [p.model_id for p in part.pokemons])
        self.assertEqual(set(get_battle_switch_choices(self.players[0], part.pokemons)), {3, 5})
        for mon in part.pokemons:
            with OwnedBattleActor.locked(self.session.battle, part, mon, active=False):
                pass
        self.turn("Tail Whip", "Safeguard", rebuild=True)
        self.assertEqual(OwnedPokemon.objects.filter(pk=self.egg.pk).values().get(), before)

    def test_egg_only_refuses_normal_request_without_locking(self):
        """No usable party means no request or battle resources are created."""
        from pokemon.models.core import OwnedPokemon

        egg = self.add(0, "Eevee", ["Tackle"], slot=2, level=1)
        OwnedPokemon.objects.filter(pk=egg.pk).update(is_egg=True)
        egg.refresh_from_db()
        before = self.snapshot()
        self.command("create")
        self.assertFalse(self.room.db.pvp_requests)
        self.assertFalse(self.players[0].db.battle_lock)
        self.assertEqual(self.snapshot(), before)

    def test_revive_and_switch_use_original_party_slots(self):
        """Revive still finds a fainted reserve; an egg slot spends no choice or item."""
        from pokemon.helpers.pokemon_helpers import get_max_hp
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        self.players[0].trainer.add_item("Revive", 1)  # Separate labelled bag prerequisite.
        self.launch()
        before = self.snapshot()
        self.command("switch", "1")
        self.assertEqual(self.snapshot(), before)
        self.command("item", "Revive=5")
        self.command("attack", "Safeguard", 1)
        hp = OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=self.reserve.pk)
        self.assertEqual(hp, max(1, get_max_hp(self.reserve) // 2))
        self.assertEqual(self.players[0].trainer.get_item_quantity("Revive"), 0)
        self.command("switch", "5")
        self.command("attack", "Safeguard", 1)
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].active[0].model_id,
                         "owned:" + str(self.reserve.pk))
        self.turn("Safeguard", "Safeguard")

    def test_temporary_fusion_and_ordinary_actor_exclude_egg(self):
        """The player's genuine Fusion remains a selectable participant beside a party egg."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.helpers.party_helpers import get_battle_switch_choices

        self.prepare()
        fusion = self.add(0, "Venusaur", ["Growl"], ability="Overgrow", slot=6)
        OwnedPokemon.objects.filter(pk=fusion.pk).update(friendship=140)
        fusion.refresh_from_db()
        OwnedPokemon.flush_cached_instance(fusion)
        self.command("fusion", "6")
        self.assertEqual(str(self.players[0].db.fusion_id), str(fusion.pk))
        self.launch()
        part = self.session.battle.participants[0]
        choices = get_battle_switch_choices(self.players[0], part.pokemons)
        self.assertNotIn(1, choices)
        self.assertIn("owned:" + str(fusion.pk), [mon.model_id for mon in part.pokemons])
        self.command("switch", "fusion")
        self.command("attack", "Safeguard", 1)
        self.rebuild()
        self.turn("Growl", "Safeguard", rebuild=True)

    def test_boxed_egg_and_hatched_member_controls(self):
        """Boxing removes custody from the party; a labelled already-hatched row can battle."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.storage import PokemonPlacement

        self.prepare()
        self.command("deposit", str(self.egg.pk))
        self.assertEqual(PokemonPlacement.objects.get(pokemon=self.egg).location_type, "box")
        self.launch()
        self.turn("Tail Whip", "Safeguard")
        self.session.end()
        self.session = None
        # Positive setup control only: this does not claim to execute the real hatch wait.
        OwnedPokemon.objects.filter(pk=self.egg.pk).update(is_egg=False)
        self.egg.refresh_from_db()
        from pokemon.services.placement import PlacementService
        PlacementService(self.players[0].storage).to_party(self.egg, slot=1)
        self.launch()
        self.assertEqual(self.session.battle.participants[0].active[0].model_id, "owned:" + str(self.egg.pk))
        self.turn("Tackle", "Safeguard")

    def test_legacy_checkpoint_is_retained_and_cannot_replay_or_end(self):
        """Old egg rosters are quarantined; normal actions and concession preserve resources."""
        from copy import deepcopy
        from unittest.mock import patch
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.roster_eligibility import BattleRosterEligibility, BattleRosterRecoveryRequired

        self.prepare()
        # Explicit legacy-fixture construction reproduces the old builder only.
        # It is not acceptance evidence for the repaired normal startup route.
        with patch.object(BattleRosterEligibility, "models", side_effect=list):
            self.launch()
        original = deepcopy(self.session.storage.get("data"))
        try:
            self.rebuild()
            self.assertEqual(self.session.storage.get("data"), original)
            self.assertEqual(self.session.storage.get("roster_recovery")["egg_refs"], ["owned:" + str(self.egg.pk)])
            before = self.snapshot()
            for kind, args, side in (("attack", "Tackle", 0), ("attack", "Safeguard", 1),
                                     ("switch", "3", 0), ("concede", "yes", 0)):
                self.command(kind, args, side)
                self.assertEqual(self.snapshot(), before)
                self.assertIn("Ask staff", self.players[side].messages[-1])
            for operation in (self.session.execute_persistent_turn, self.session.end):
                with self.assertRaises(BattleRosterRecoveryRequired):
                    operation()
                self.assertEqual(self.snapshot(), before)
            EVIDENCE.append({"case": self.id(), "label": "legacy-checkpoint-quarantine",
                             "policy": "staff-recovery-no-replay-no-roster-or-custody-rewrite",
                             "original_checkpoint": original, "after": self.snapshot()})
        finally:
            # The surrounding private schema drops all fixture rows; do not bypass end guards.
            battle_handler.unregister(self.session)
            self.session = None

    def test_wild_and_trainer_startup_filter_the_same_roster(self):
        """Both encounter builders preserve the non-egg/fainted roster rules."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.engine import BattleType
        from pokemon.battle.pokemon_factory import create_battle_pokemon
        from pokemon.models.trainer import NPCTrainer, NPCPokemonTemplate
        from pokemon.services.trainer_encounters import generate_static_trainer_encounter

        self.prepare()
        for kind in ("wild", "trainer"):
            with self.subTest(kind=kind):
                self.session = BattleSession(self.players[0])
                if kind == "wild":
                    opponent = create_battle_pokemon("Magikarp", 10, is_wild=True, move_names=["Splash"])
                    self.session._track_temp_opponent_team([opponent])
                    self.session._select_opponent = lambda: (opponent, "Wild", BattleType.WILD, "Wild encounter")
                    self.session.start()
                else:
                    npc = NPCTrainer.objects.create(name="Egg roster NPC")
                    NPCPokemonTemplate.objects.create(npc_trainer=npc, species="Magikarp", level=10,
                        template_key="lead", sort_order=1, ivs=[0] * 6, evs=[0] * 6, move_names=["Splash"])
                    self.session.start_trainer_encounter(generate_static_trainer_encounter(npc))
                part = self.session.battle.participants[0]
                self.assertEqual([mon.model_id for mon in part.pokemons],
                                 ["owned:" + str(mon.pk) for mon in (self.live, self.reserve)])
                self.assertEqual(part.active[0].model_id, "owned:" + str(self.live.pk))
                self.command("attack", "Tail Whip")
                self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
                self.rebuild()
                self.session.end()
                self.session = None

    def test_doubles_leads_and_choices_exclude_egg_without_dropping_revive_bench(self):
        """Both living slots fill from non-eggs while the fainted member remains benched."""
        self.prepare()
        self.add(0, "Mew", ["Safeguard"], ability="Synchronize", slot=6)
        self.add(1, "Mew", ["Safeguard"], ability="Synchronize", slot=2)
        self.launch("double")
        self.assertEqual([len(part.active) for part in self.session.battle.participants], [2, 2])
        part = self.session.battle.participants[0]
        self.assertNotIn("owned:" + str(self.egg.pk), [mon.model_id for mon in part.pokemons])
        self.assertIn("owned:" + str(self.reserve.pk), [mon.model_id for mon in part.pokemons])
        turn = self.session.battle.turn_count
        self.command("attack", "A1 Tail Whip")
        self.command("attack", "A2 Safeguard")
        self.rebuild()
        self.command("attack", "B1 Safeguard", 1)
        self.command("attack", "B2 Safeguard", 1)
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)

    def test_party_becoming_eggs_before_start_keeps_request_and_resources(self):
        """Normal startup revalidates readiness rather than consuming a now-invalid request."""
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        self.command("create")
        self.command("join", self.players[0].key, 1)
        OwnedPokemon.objects.filter(trainer=self.players[0].trainer).update(is_egg=True)
        before = self.snapshot()
        self.command("start")
        self.assertIsNone(self.session)
        self.assertEqual(self.snapshot(), before)
        self.assertIn(self.players[0].id, self.room.db.pvp_requests)
        self.assertFalse(self.players[0].db.battle_id)

    def test_all_fainted_and_eggs_refuse_builder_and_request(self):
        """A positive-HP egg cannot make an otherwise fainted party battle ready."""
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.models.core import OwnedPokemon

        self.prepare()
        OwnedPokemon.objects.filter(pk=self.live.pk).update(current_hp=0)
        self.live.refresh_from_db()
        before = self.snapshot()
        self.command("create")
        self.assertFalse(self.room.db.pvp_requests)
        shell = object.__new__(BattleSession)
        with self.assertRaises(ValueError):
            shell._prepare_player_party(self.players[0])
        # Existing explicit scripted full-heal adapters remain available;
        # they still cannot admit an egg and do not heal the owned SQL rows.
        healed = shell._prepare_player_party(self.players[0], full_heal=True)
        self.assertEqual([mon.model_id for mon in healed],
                         ["owned:" + str(mon.pk) for mon in (self.live, self.reserve)])
        self.assertTrue(all(mon.hp == mon.max_hp for mon in healed))
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    run(EggRosterCases)
