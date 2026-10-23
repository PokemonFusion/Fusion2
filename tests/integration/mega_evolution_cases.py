"""Ordinary Mega declarations and real whole-turn/SQL recovery in private schemas."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import item_availability_cases as acquisition

EVIDENCE = []


class MegaEvolutionCases(unittest.TestCase):
    """Keep source authoring and native fixture setup separate from ordinary input."""

    command = acquisition.AcquisitionCases.command
    reply = acquisition.AcquisitionCases.reply
    state = acquisition.AcquisitionCases.state

    def buy(self, *args, **kwargs):
        """Retain the real menu/wallet/bag acquisition receipt for this named case."""
        start = len(acquisition.EVIDENCE)
        result = acquisition.AcquisitionCases.buy(self, *args, **kwargs)
        EVIDENCE.extend(
            dict(row, case=self._testMethodName) for row in acquisition.EVIDENCE[start:]
        )
        return result

    def setUp(self):
        """Create native owners, finite source and ordinary controller transports."""
        acquisition.AcquisitionCases.setUp(self)
        self.native("Eevee", 4)
        self.native("Pikachu", 5)
        self.foe = self.native("Venusaur", 1, self.players[1])
        self.native("Eevee", 2, self.players[1])
        self.native("Pikachu", 3, self.players[1])
        self.pvp_search = patch(
            "evennia.search_object",
            lambda query: [p for p in self.players if str(p.id) == str(query).lstrip("#")],
        )
        self.pvp_search.start()
        self.addCleanup(self.pvp_search.stop)
        self.installed_objects = []

    def tearDown(self):
        """End only this case's battle and close its menus before schema deletion."""
        acquisition.AcquisitionCases.tearDown(self)
        acquisition.ObjectDB.objects.filter(pk__in=self.installed_objects).delete()

    def native(self, species, slot, player=None):
        """Prepare native species and actual Tackle without learning/form shortcuts."""
        player = player or self.player
        species = "Venusaur" if species == "Mew" else species
        entry = resolve_dex_entry(POKEDEX, species)
        mon = create_owned_pokemon(
            species,
            player.trainer,
            50,
            nature="Hardy",
            ability=entry.raw["abilities"]["0"],
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Tackle", "Growl"],
        )
        PlacementService(player.storage).to_party(mon, slot=slot)
        self.mons.append(mon)
        return mon

    def equip(self, *, side=0, purchase=True):
        """Use a real store and +hold for the primary route; label opponent setup."""
        if purchase:
            self.buy("Venusaurite", price=10000, quantity=1)
        else:
            self.players[side].trainer.add_item("Venusaurite")
        self.command("hold", ("3" if side == 0 else "1") + "=Venusaurite", side=side)
        row = self.mon if side == 0 else self.foe
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=row.pk).values_list("held_item", flat=True).get(),
            "Venusaurite",
        )

    def launch(self, battle_format="single", *, kind="pvp"):
        """Use ordinary PvP commands or controlled production encounter selection."""
        if kind == "pvp":
            self.command("create", battle_format)
            self.command("join", self.player.key, side=1)
            self.command("start")
            self.session = self.player.ndb.battle_instance
        else:
            self.session = BattleSession(self.player)
            foe = create_battle_pokemon(
                "Magikarp", 50, is_wild=kind == "wild", move_names=["Splash"]
            )
            self.session._track_temp_opponent_team([foe])
            self.session._select_opponent = lambda: (
                foe,
                "Native fixture opponent",
                BattleType.WILD if kind == "wild" else BattleType.TRAINER,
                "Controlled ordinary encounter selection",
            )
            self.session.start()
        self.assertIsNotNone(self.session, self.player.messages)
        self.session.battle.rng = random.Random(12)
        return self.session

    def rebuild(self):
        """Discard live references and restore only the production SQL checkpoint."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for player in self.players:
            player.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.room.attributes.reset_cache()
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        return self.session

    def record(self, name, args="", *, side=0):
        """Save input/output and independent SQL plus runtime before/after."""
        before, start = self.observation(), len(self.players[side].messages)
        result = self.command(name, args, side=side)
        EVIDENCE.append(
            {
                "case": self._testMethodName,
                "command": "+" + name + " " + args,
                "side": side,
                "before": before,
                "after": self.observation(),
                "messages": list(map(str, self.players[side].messages[start:])),
            }
        )
        return result

    def observation(self):
        """Do not treat a callback assignment as a battle effect observation."""
        result = self.state()
        if self.session and self.session.battle:
            result["battle"] = self.session.logic.to_dict()
        return deepcopy(result)

    def turn(self):
        """Use actual +attack inputs, retaining one queued action per active actor."""
        with patch.object(self.session, "maybe_run_turn"):
            for name, pos in self.session.data.turndata.positions.items():
                if pos.pokemon.hp > 0:
                    self.record(
                        "attack",
                        name + " Tackle " + ("B1" if name.startswith("A") else "A1"),
                        side=int(name.startswith("B")),
                    )
        self.session.execute_persistent_turn()

    def test_purchase_hold_reserve_duplicate_waiting_rebuild_effect_and_return(self):
        """Buy one reusable stone, bind one move, rebuild Mega, end and return it."""
        self.equip()
        before = self.state()
        self.launch()
        self.record("mega")
        request = deepcopy(self.session.battle.mega_pending)
        self.record("mega")
        self.assertEqual(self.session.battle.mega_pending, request)
        self.assertFalse(self.session.state.declare)
        self.rebuild()
        self.assertEqual(self.session.battle.mega_pending, request)
        self.turn()
        pokemon = self.session.battle.participants[0].active[0]
        self.assertEqual(
            (
                pokemon.species,
                pokemon.types,
                str(
                    (getattr(pokemon.ability, "raw", {}) or {}).get("name")
                    or getattr(pokemon.ability, "name", pokemon.ability)
                ),
            ),
            ("Venusaur-Mega", ["Grass", "Poison"], "Thick Fat"),
        )
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 0)
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.mega_used, {"A"})
        battle = self.session.battle
        self.session.end()
        self.assertEqual(battle.participants[0].pokemons[0].species, "Venusaur")
        row = OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        self.assertEqual(
            (row["species"], row["ability"], row["held_item"]),
            ("Venusaur", "Overgrow", "Venusaurite"),
        )
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 1)
        self.assertEqual(self.state()["wallet"], before["wallet"])

    def test_checkpoint_fault_restores_full_input_budget_form_pp_rng_and_messages(self):
        """A failed whole-turn checkpoint allows exactly one clean retry."""
        self.equip()
        self.launch()
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Tackle A1", side=1)
        before = self.observation()
        rng = self.session.battle.rng.getstate()
        start = len(self.player.messages)
        original = self.session.storage.set

        def fail(key, value):
            """Fault only after transformation, moves and strict owned synchronization."""
            if key == "data":
                raise RuntimeError("Mega checkpoint fixture")
            return original(key, value)

        with patch.object(self.session.storage, "set", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "Mega checkpoint fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.session.battle.rng.getstate(), rng)
        self.assertFalse(any("Mega Evolved" in str(m) for m in self.player.messages[start:]))
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})

    def negative(self, variant):
        """Fresh identities, placement, provenance and held state govern eligibility."""
        self.equip()
        if variant == "bag_only":
            self.command("hold", "3=")
        self.launch()
        pokemon = self.session.battle.participants[0].active[0]
        if variant == "foreign":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                trainer_id=self.players[1].trainer.pk
            )
        elif variant == "egg":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        elif variant == "box":
            PlacementService(self.player.storage).to_box(self.mon)
        elif variant == "held_sql_removed":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="")
        elif variant == "held_runtime_removed":
            pokemon.item = None
        elif variant == "nickname_spoof":
            pokemon.name, pokemon.species, pokemon.base_species = "Venusaur", "Eevee", "Eevee"
        elif variant == "transformed":
            pokemon.transformed = True
        elif variant == "native_spoof":
            pokemon.native_origin = {"ref": pokemon.model_id, "species": "Eevee"}
        elif variant == "fainted":
            pokemon.hp = 0
        elif variant == "wrong_stone":
            pokemon.item = "Charizardite X"
        elif variant == "wrong_controller":
            self.player.db.battle_control = False
        elif variant == "stale_session":
            self.player.db.battle_id = "different-session"
        elif variant == "inactive_fusion":
            PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        elif variant == "unsupported_format":
            self.session.battle.participants[0].max_active = 3
        before = self.observation()
        self.record("mega")
        self.assertEqual(self.observation(), before)
        self.assertFalse(self.session.battle.mega_used)
        self.assertFalse(self.session.battle.mega_pending)
        if variant in {"foreign", "stale_session", "egg"}:
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                trainer_id=self.player.trainer.pk, is_egg=False
            )
            self.player.db.battle_id = self.session.battle_id

    def suppression(self, variant):
        """Suppressed matching held ownership still enables the guarded form."""
        self.equip()
        self.launch()
        pokemon = self.session.battle.participants[0].active[0]
        if variant == "klutz":
            pokemon.setAbility("Klutz", battle=self.session.battle)
        elif variant == "flag":
            pokemon.item_suppressed = True
        elif variant == "embargo":
            pokemon.volatiles["embargo"] = {"duration": 5}
        elif variant == "magicroom":
            self.session.battle.field.pseudo_weather["magicroom"] = {"duration": 5}
        self.record("mega")
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(pokemon.species, "Venusaur-Mega")
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(),
            "Venusaurite",
        )
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 0)

    def test_invalid_input_preserves_request_cancel_and_valid_item_release(self):
        """Only a legal non-MOVE choice or explicit cancel releases the request."""
        self.equip()
        self.launch("double")
        self.record("mega", "A1")
        request = deepcopy(self.session.battle.mega_pending)
        self.record("attack", "A1 Invented Move B1")
        self.record("attack", "A1 Tackle A1")
        self.record("switch", "A1 999")
        self.record("item", "A1 Invented Item=3")
        self.assertEqual(self.session.battle.mega_pending, request)
        self.assertFalse(self.session.state.declare)
        self.record("mega", "A1 cancel")
        self.assertFalse(self.session.battle.mega_pending)
        self.record("mega", "A1")
        self.player.trainer.add_item("Potion")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "A1 Potion=3")
        self.assertFalse(self.session.battle.mega_pending)
        self.rebuild()
        self.assertFalse(self.session.battle.mega_pending)
        self.assertEqual(self.session.state.declare["A1"]["item"], "Potion")

    def test_independent_opponents_and_no_second_use_after_bench_faint_rebuild(self):
        """Both teams may activate once; inactive/fainted form evidence stays spent."""
        self.equip()
        self.equip(side=1, purchase=False)
        self.launch("double")
        self.record("mega", "A1")
        self.record("mega", "B1", side=1)
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {"A", "B"})
        mon = self.session.battle.participants[0].active[0]
        mon.hp = 0
        mon.is_fainted = True
        self.rebuild()
        self.assertEqual(self.session.battle.mega_used, {"A", "B"})
        self.assertEqual(self.session.battle.participants[0].pokemons[0].species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.participants[0].pokemons[0].hp, 0)
        self.record("mega", "A2")
        self.assertEqual(self.session.battle.mega_used, {"A", "B"})

    def tera_order(self, first):
        """Separate eligible allies can reserve in either order and share no budget."""
        self.equip()
        self.launch("double")
        commands = [("mega", "A1"), ("tera", "A2")]
        if first == "tera":
            commands.reverse()
        for name, args in commands:
            self.record(name, args)
        self.assertEqual(set(self.session.battle.mega_pending), {"A"})
        self.assertEqual(set(self.session.battle.tera_pending), {"A"})
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(self.session.battle.tera_used, {"A"})
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.participants[0].active[1].terastallized, "Normal")

    def thick_fat(self, move):
        """Real attacks deal half damage, with suppression and Mold Breaker controls."""
        PlacementService(self.players[1].storage).to_box(self.foe)
        attacker = create_owned_pokemon(
            "Mew",
            self.players[1].trainer,
            50,
            nature="Hardy",
            ability="Synchronize",
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=[move],
        )
        PlacementService(self.players[1].storage).to_party(attacker, slot=1)
        self.mons.append(attacker)
        self.equip()
        self.launch()
        self.record("mega")
        holder = self.session.battle.participants[0].active[0]
        source = self.session.battle.participants[1].active[0]
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Growl B1")
            self.record("attack", move + " A1", side=1)
        self.session.execute_persistent_turn()
        damages = []
        for control in ("active", "suppressed", "mold_breaker"):
            holder.hp, source.hp = holder.max_hp, source.max_hp
            holder.status, holder.ability_suppressed = 0, control == "suppressed"
            if control == "mold_breaker":
                source.setAbility("Mold Breaker", battle=self.session.battle)
            self.session.battle.rng = random.Random(102)
            with patch.object(self.session, "maybe_run_turn"):
                self.record("attack", "Growl B1")
                self.record("attack", move + " A1", side=1)
            self.session.execute_persistent_turn()
            damage = holder.max_hp - holder.hp
            damages.append(damage)
            EVIDENCE.append(
                {
                    "case": self._testMethodName,
                    "effect": "Thick Fat",
                    "source_move": move,
                    "control": control,
                    "damage": damage,
                    "holder": holder.to_dict(),
                    "used": sorted(self.session.battle.mega_used),
                    "sql": self.state(),
                }
            )
        self.assertGreater(damages[0], 0)
        self.assertGreater(damages[1], damages[0] * 1.8)
        self.assertEqual(damages[1], damages[2])
        self.assertEqual(holder.species, "Venusaur-Mega")

    def test_saved_held_conflict_cannot_be_resurrected_by_turn_sync(self):
        """A changed saved stone fails the whole turn without granting a copy."""
        self.equip()
        self.launch()
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Tackle A1", side=1)
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="")
        with self.assertRaisesRegex(ValueError, "held ownership changed"):
            self.session.execute_persistent_turn()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("held_item", flat=True).get(),
            "",
        )
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 0)
        self.assertFalse(self.session.battle.mega_used)
        # Repair only the deliberately injected fixture conflict before cleanup.
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(held_item="Venusaurite")

    def test_hyper_training_stats_hp_status_pp_and_nickname_survive(self):
        """Form stats use battle level and trained IVs without changing native genetics."""
        from dataclasses import asdict
        from pokemon.helpers.pokemon_helpers import get_stats

        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            flags=["hypertrained:attack", "hypertrained:speed"], nickname="Garden Friend"
        )
        OwnedPokemon.flush_cached_instance(self.mon)
        self.equip()
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        genetics = (
            holder.level,
            list(holder.ivs),
            list(holder.evs),
            holder.nature,
            list(holder.hyper_training),
        )
        self.record("mega")
        self.turn()
        expected = get_stats(
            SimpleNamespace(
                species="Venusaur-Mega",
                level=holder.level,
                ivs=holder.ivs,
                evs=holder.evs,
                nature=holder.nature,
                hyper_training=holder.hyper_training,
            )
        )
        self.assertEqual(asdict(holder.base_stats), expected)
        self.assertEqual(holder.name, "Garden Friend")
        self.assertEqual(
            (holder.level, holder.ivs, holder.evs, holder.nature, holder.hyper_training), genetics
        )
        before = holder.to_dict()
        self.rebuild()
        restored = self.session.battle.participants[0].active[0]
        self.assertEqual(
            (restored.hp, restored.max_hp, restored.status, restored.name, restored.moves[0].pp),
            (
                before["hp"],
                before["max_hp"],
                before["status"],
                before["name"],
                before["moves"][0]["pp"],
            ),
        )
        self.assertEqual(asdict(restored.base_stats), expected)

    def test_legal_switch_cancels_request_and_activated_form_survives_switch_back(self):
        """A legal nonmove releases an unused request, while activated form persists."""
        self.equip()
        self.launch()
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "4")
            self.record("attack", "Tackle A1", side=1)
        self.assertFalse(self.session.battle.mega_pending)
        self.session.execute_persistent_turn()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "3")
            self.record("attack", "Tackle A1", side=1)
        self.session.execute_persistent_turn()
        self.record("mega")
        self.turn()
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "4")
            self.record("attack", "Tackle A1", side=1)
        self.session.execute_persistent_turn()
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].pokemons[0].species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.mega_used, {"A"})

    def battle_kind(self, kind):
        """The same ordinary Mega/attack path works in controlled Wild/Trainer sessions."""
        self.equip()
        self.launch(kind=kind)
        self.record("mega")
        self.record("attack", "Tackle B1")
        self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")

    def fusion(self, kind):
        """A current native Fusion retains effective level, trained stats and stone."""
        from dataclasses import asdict
        from pokemon.helpers.pokemon_helpers import get_stats

        self.equip()
        PlacementService(self.player.storage).reserve_for_fusion(self.mon)
        self.player.db.fusion_id, self.player.db.fusion_kind = str(self.mon.pk), kind
        self.player.db.fusion_species, self.player.db.morphology = "Venusaur", "Human"
        self.player.db.total_exp, self.player.db.trainer_xp = self.mon.total_exp, 1000
        self.player.db.fusion_battle_order = "first"
        with patch("utils.pokemon_utils._fusion_boost_enabled", return_value=True):
            self.launch("double")
        position = next(
            name
            for name, pos in self.session.data.turndata.positions.items()
            if str(pos.pokemon.model_id) == "owned:" + str(self.mon.pk)
        )
        holder = self.session.data.turndata.positions[position].pokemon
        effective = holder.level
        self.record("mega", position)
        with patch.object(self.session, "maybe_run_turn"):
            for name in self.session.data.turndata.positions:
                self.record(
                    "attack",
                    name + " Growl " + ("B1" if name.startswith("A") else "A1"),
                    side=int(name.startswith("B")),
                )
        self.session.execute_persistent_turn()
        self.assertEqual(holder.species, "Venusaur-Mega")
        ordinary = get_stats(
            SimpleNamespace(
                species="Venusaur-Mega",
                level=effective,
                ivs=holder.ivs,
                evs=holder.evs,
                nature=holder.nature,
                hyper_training=holder.hyper_training,
            )
        )
        expected = {
            key: value if key == "hp" else value * 11 // 10 for key, value in ordinary.items()
        }
        self.assertEqual(asdict(holder.base_stats), expected)
        self.assertEqual(holder.native_origin["stat_scale"], 110)
        if kind == "temporary":
            self.assertLess(effective, self.mon.level)
        else:
            self.assertEqual(effective, self.mon.level)
        self.rebuild()
        restored = next(
            mon
            for mon in self.session.battle.participants[0].pokemons
            if mon.model_id == holder.model_id
        )
        self.assertEqual((restored.species, restored.level), ("Venusaur-Mega", effective))
        self.assertEqual(asdict(restored.base_stats), asdict(holder.base_stats))
        self.session.end()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(),
            "Venusaur",
        )

    def test_current_ally_contention_reserves_only_one_side_request(self):
        """Genuinely competing SQL requests cannot erase the winning reservation."""
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections

        ally = create_owned_pokemon(
            "Venusaur",
            self.player.trainer,
            50,
            nature="Hardy",
            ability="Overgrow",
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Tackle", "Growl"],
        )
        PlacementService(self.player.storage).to_box(self.mons[1])
        PlacementService(self.player.storage).to_party(ally, slot=4)
        self.mons.append(ally)
        self.equip()
        self.player.trainer.add_item("Venusaurite")
        self.command("hold", "4=Venusaurite")
        self.launch("double")
        barrier = Barrier(2)

        def reserve(actor):
            """Synchronize separate connections before entering the production lock."""
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    self.session.choices_for(self.player).mega(actor=actor)
                    return True
                except ValueError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(reserve, ["A1", "A2"])), 1)
        self.assertEqual(len(self.session.battle.mega_pending), 1)
        winning = deepcopy(self.session.battle.mega_pending)
        self.rebuild()
        self.assertEqual(self.session.battle.mega_pending, winning)
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(
            sum(
                mon.species == "Venusaur-Mega"
                for mon in self.session.battle.participants[0].pokemons
            ),
            1,
        )

    def test_opt_in_counter_exit_purchase_equip_effect_cleanup_and_no_refill(self):
        """The actual reviewed counter supplies the accepted reusable copy."""
        from evennia.utils.create import create_object
        from pokemon.services.item_counter import ItemCounter

        hub = create_object(
            "typeclasses.rooms.FusionRoom", key="private Mega counter hub", nohome=True
        )
        counter = ItemCounter("world/mega_stone_counter.json")
        room = counter.install(hub)
        receipt = hub.attributes.get("counter_mega-stone-counter-v1")
        self.installed_objects.extend(
            [hub.pk, receipt["room"], receipt["entrance"], receipt["return_exit"]]
        )
        self.room, self.player.location = room, hub
        self.player.character.location = hub

        def move(destination, **kwargs):
            """Persist the real Exit destination while isolating ancillary movement hooks."""
            moved = self.player.character.move_to(destination, quiet=True, move_hooks=False)
            if moved:
                self.player.location = destination
            return moved

        self.player.move_to = move
        entrance = acquisition.ObjectDB.objects.get(pk=receipt["entrance"])
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.player, entrance, ""
        command.func()
        self.room = SimpleNamespace(
            id=room.pk,
            pk=room.pk,
            key=room.key,
            db=room.db,
            ndb=room.ndb,
            attributes=room.attributes,
            contents=self.players,
        )
        for player in self.players:
            player.location = self.room
        # Actual purchase, not AcquisitionCases.buy's separate stock authoring.
        before = self.state()
        self.command("store")
        for text in ("1", "Venusaurite 1", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state()["wallet"], before["wallet"] - 10000)
        self.assertEqual(self.state()["stock"]["Venusaurite"]["quantity"], 0)
        self.command("inventory")
        self.command("hold", "3=Venusaurite")
        counter.install(hub)
        self.assertEqual(self.state()["stock"]["Venusaurite"]["quantity"], 0)
        self.launch()
        self.record("mega")
        self.turn()
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")
        self.session.end()
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 1)
        EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "reviewed_Mega_counter_purchase_to_effect",
                "sql": self.state(),
                "socket_login": False,
                "movement_hooks": False,
            }
        )

    def slot_flow(self, label):
        """Each of A1/A2/B1/B2 is an independently controlled ordinary actor."""
        side = int(label.startswith("B"))
        self.equip(side=side, purchase=side == 0)
        mon = self.foe if side else self.mon
        if label.endswith("2"):
            pika = next(
                p
                for p in self.mons
                if p.species == "Pikachu" and p.trainer_id == self.players[side].trainer.pk
            )
            PlacementService(self.players[side].storage).to_box(pika)
            PlacementService(self.players[side].storage).to_party(mon, slot=6)
        self.launch("double")
        self.record("mega", label, side=1 - side)
        self.assertFalse(self.session.battle.mega_pending)
        self.record("mega", label, side=side)
        self.assertEqual(
            self.session.battle.mega_pending[label[0]]["pokemon"], "owned:" + str(mon.pk)
        )
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {label[0]})
        self.assertEqual(
            self.session.data.turndata.positions[label].pokemon.species, "Venusaur-Mega"
        )

    def move_order(self, policy):
        """New ability speed/priority is used in the activation turn, including Trick Room."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            ability="Chlorophyll", nickname="Garden Friend"
        )
        OwnedPokemon.objects.filter(pk=self.foe.pk).update(
            ivs=[0, 0, 0, 0, 0, 31], nickname="Guest Leaf"
        )
        for mon in (self.mon, self.foe):
            OwnedPokemon.flush_cached_instance(mon)
        self.equip()
        self.launch()
        holder = self.session.battle.participants[0].active[0]
        if policy == "prankster":
            holder.setAbility("Prankster", battle=self.session.battle)
        else:
            self.session.battle.field.weather = "sunnyday"
        if policy == "trickroom":
            self.session.battle.field.pseudo_weather["trickroom"] = {"duration": 5}
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Growl B1")
            self.record("attack", "Growl A1", side=1)
        original, trace = self.session.battle.use_move, []

        def observe(action, **kwargs):
            """Retain actual ordered attacks without replacing their execution."""
            trace.append((action.pokemon.name, action.priority, action.speed))
            return original(action, **kwargs)

        with patch.object(self.session.battle, "use_move", side_effect=observe):
            self.session.execute_persistent_turn()
        self.assertEqual(
            [row[0] for row in trace],
            (
                ["Garden Friend", "Guest Leaf"]
                if policy == "trickroom"
                else ["Guest Leaf", "Garden Friend"]
            ),
        )
        self.assertEqual([row[1] for row in trace], [0, 0])
        EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "same_turn_new_form_order",
                "policy": policy,
                "trace": trace,
            }
        )

    def test_legacy_confirmed_form_recovers_spent_budget_and_native_identity(self):
        """Old species evidence recovers a use without granting another activation."""
        from pokemon.battle.logic import BattleLogic

        self.equip()
        self.launch()
        self.record("mega")
        self.turn()
        payload = deepcopy(self.session.logic.to_dict())
        payload["state"].pop("mega_used")
        payload["state"].pop("mega_pending")
        for team in payload["data"]["teams"].values():
            for mon in team["pokemon"]:
                if mon:
                    for key in (
                        "mega_profile",
                        "mega_evolved",
                        "mega_guard_stone",
                        "native_origin",
                        "base_species",
                    ):
                        mon.pop(key, None)
        restored = BattleLogic.from_dict(payload)
        self.assertEqual(restored.battle.mega_used, {"A"})
        holder = restored.battle.participants[0].pokemons[0]
        self.assertEqual((holder.species, holder.base_species), ("Venusaur-Mega", "Venusaur"))
        self.assertEqual(holder.mega_profile["restore"]["species"], "Venusaur")

    def corrupt_checkpoint(self, control):
        """Corrupt provenance, restoration or ledgers cannot recharge a side."""
        from pokemon.battle.logic import BattleLogic

        self.equip()
        self.launch()
        self.record("mega")
        self.turn()
        payload = deepcopy(self.session.logic.to_dict())
        if control == "stats":
            payload["data"]["teams"]["A"]["pokemon"][0]["mega_profile"]["restore"]["stats"][
                "attack"
            ] += 1
        elif control == "owner":
            ref = payload["data"]["teams"]["A"]["pokemon"][0]["model_id"]
            payload["state"]["pokemon_control"][ref] = str(self.players[1].pk)
        elif control == "ledger":
            payload["state"]["mega_used"] = []
        elif control == "side":
            payload["state"]["mega_used"] = ["X"]
        with self.assertRaises(ValueError):
            BattleLogic.from_dict(payload)

    def test_stale_choices_and_raw_old_pending_do_not_activate(self):
        """Old callbacks fail; unbound flags cannot replace a valid reservation."""
        self.equip()
        self.launch()
        stale = self.session.choices_for(self.player)
        holder = self.session.battle.participants[0].active[0]
        holder.pending_mega = True
        self.turn()
        self.assertFalse(self.session.battle.mega_used)
        self.assertEqual(holder.species, "Venusaur")
        with self.assertRaisesRegex(ValueError, "earlier turn"):
            stale.mega()
        self.assertFalse(self.session.battle.mega_pending)

    def test_post_activation_failure_restores_input_and_failed_end_keeps_spent_use(self):
        """Effect and ending failures have explicit retry and no-recharge behavior."""
        from pokemon.battle.mega_evolution import MegaEvolution

        self.equip()
        self.launch()
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Tackle A1", side=1)
        original = MegaEvolution.activate.__func__

        def fail(cls, *args, **kwargs):
            """Raise after the real form/ability/budget mutation."""
            original(cls, *args, **kwargs)
            raise RuntimeError("post-Mega fixture")

        before = self.observation()
        with patch.object(MegaEvolution, "activate", classmethod(fail)):
            with self.assertRaisesRegex(RuntimeError, "post-Mega fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.session.execute_persistent_turn()
        battle = self.session.battle
        with patch.object(
            self.session, "_sync_player_pokemon_state", side_effect=RuntimeError("end fixture")
        ):
            with self.assertRaisesRegex(RuntimeError, "end fixture"):
                self.session.end()
        self.assertEqual(battle.mega_used, {"A"})
        self.assertTrue(self.session.state.ending)
        self.record("mega")
        self.assertEqual(battle.mega_used, {"A"})
        self.session.end()
        self.assertEqual(
            OwnedPokemon.objects.filter(pk=self.mon.pk).values_list("species", flat=True).get(),
            "Venusaur",
        )

    def test_reservation_write_failure_has_no_pending_state_or_success(self):
        """A post-write error rewinds the declaration and its saved Attribute."""
        self.equip()
        self.launch()
        before, start = self.observation(), len(self.player.messages)
        original = self.session.storage.set

        def fail(key, value):
            """Fail after the real state write, retaining the production rollback."""
            original(key, value)
            raise RuntimeError("reservation write fixture")

        with patch.object(self.session.storage, "set", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "reservation write fixture"):
                self.record("mega")
        self.assertEqual(self.observation(), before)
        self.assertFalse(any("reserved" in str(m) for m in self.player.messages[start:]))

    def test_faint_revive_switch_reentry_and_new_battle_keep_correct_budget(self):
        """Revival retains Mega without replay; a separately started battle resets it."""
        self.equip()
        self.launch()
        self.record("mega")
        self.turn()
        holder = self.session.battle.participants[0].active[0]
        activation_messages = sum("Mega Evolved into" in str(m) for m in self.player.messages)
        holder.hp, holder.is_fainted = 0, True
        self.session.battle.run_faint()
        self.session._sync_player_pokemon_state(strict=True)
        self.session._sync_active_battle_state()
        self.player.trainer.add_item("Revive")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("item", "Revive=3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertGreater(holder.hp, 0)
        self.assertEqual(holder.species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.rebuild()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("switch", "3")
            self.record("attack", "Growl A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur-Mega")
        self.assertEqual(
            sum("Mega Evolved into" in str(m) for m in self.player.messages), activation_messages
        )
        self.session.end()
        self.launch()
        self.assertFalse(self.session.battle.mega_used)
        self.assertEqual(self.session.battle.participants[0].active[0].species, "Venusaur")
        self.record("mega")
        self.turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})

    def test_store_funds_disabled_stock_and_repeated_equip_return_are_safe(self):
        """The optional offer retains ordinary finite commerce and reusable ownership."""
        from pokemon.models.trainer import Trainer

        self.room.db.store_inventory = {"Venusaurite": {"price": 10000, "quantity": 1}}
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=9999)
        before = self.state()
        self.command("store")
        for text in ("1", "Venusaurite 1", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state(), before)
        self.room.db.is_item_shop = False
        self.command("store")
        self.assertEqual(self.state(), before)
        self.room.db.is_item_shop = True
        self.room.db.store_inventory = {"Venusaurite": {"price": 10000, "quantity": 0}}
        before = self.state()
        self.command("store")
        for text in ("1", "Venusaurite 1", "back", "q"):
            self.reply(text)
        self.assertEqual(self.state(), before)
        Trainer.objects.filter(pk=self.player.trainer.pk).update(money=20000)
        self.equip()
        self.command("hold", "3=Venusaurite")
        self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), 0)
        for text, quantity in (("3=", 1), ("3=", 1), ("3=Venusaurite", 0), ("3=", 1)):
            self.command("hold", text)
            self.assertEqual(self.player.trainer.get_item_quantity("Venusaurite"), quantity)

    def lock_owner_change(self, variant):
        """Changes after reservation abort all turn effects instead of using a foreign actor."""
        self.equip()
        self.launch()
        self.record("mega")
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Tackle A1", side=1)
        if variant == "owner":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                trainer_id=self.players[1].trainer.pk
            )
        elif variant == "egg":
            OwnedPokemon.objects.filter(pk=self.mon.pk).update(is_egg=True)
        elif variant == "box":
            PlacementService(self.player.storage).to_box(self.mon)
        before = self.state()
        with self.assertRaises(ValueError):
            self.session.execute_persistent_turn()
        self.assertEqual(self.state(), before)
        self.assertFalse(self.session.battle.mega_used)
        # Restore only deliberately corrupted setup before ending this fixture.
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            trainer_id=self.player.trainer.pk, is_egg=False
        )
        OwnedPokemon.flush_cached_instance(self.mon)
        if variant == "box":
            PlacementService(self.player.storage).to_party(
                OwnedPokemon.objects.get(pk=self.mon.pk), slot=3
            )

    def test_flee_cancels_only_its_actor_and_does_not_overwrite_a_queued_choice(self):
        """Normal RUN uses the same no-overwrite/cancel boundary as other choices."""
        self.equip()
        self.launch("double")
        self.record("mega", "A1")
        request = deepcopy(self.session.battle.mega_pending)
        self.record("flee", "B1")
        self.assertEqual(self.session.battle.mega_pending, request)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("flee", "A1")
        self.assertFalse(self.session.battle.mega_pending)
        self.assertIn("run", self.session.state.declare["A1"])
        before = deepcopy(self.session.state.declare)
        self.record("attack", "A1 Tackle B1")
        self.assertEqual(self.session.state.declare, before)
        self.rebuild()
        self.assertFalse(self.session.battle.mega_pending)
        self.assertEqual(self.session.battle.participants[0].pending_action.priority, 9)

    def test_compound_reservation_is_rejected_before_shared_runtime_or_sql_changes(self):
        """Normal declarations own their input transaction; outer operations cannot leak them."""
        from django.db import transaction

        self.equip()
        self.launch()
        before, start = self.observation(), len(self.player.messages)
        with transaction.atomic():
            self.record("mega")
        self.assertEqual(self.observation(), before)
        self.assertFalse(any("reserved" in str(m) for m in self.player.messages[start:]))

    def test_sleep_prevents_move_but_does_not_refund_successful_mega(self):
        """Pre-move Mega spends once even when ordinary prevention leaves PP unspent."""
        OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
        OwnedPokemon.flush_cached_instance(self.mon)
        self.equip()
        self.launch()
        self.record("mega")
        self.turn()
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(holder.species, "Venusaur-Mega")
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(holder.to_dict()["moves"][0]["pp"], 35)
        self.assertEqual(
            acquisition.ActiveMoveslot.objects.filter(pokemon=self.mon, slot=1)
            .values_list("current_pp", flat=True)
            .get(),
            35,
        )
        self.rebuild()
        self.assertEqual(self.session.battle.mega_used, {"A"})

    def test_immune_target_spends_normal_pp_and_keeps_mega_use(self):
        """A genuine Ghost immunity cannot undo a valid pre-move transformation."""
        PlacementService(self.players[1].storage).to_box(self.foe)
        ghost = create_owned_pokemon(
            "Gastly",
            self.players[1].trainer,
            50,
            nature="Hardy",
            ability="Levitate",
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=["Night Shade"],
        )
        PlacementService(self.players[1].storage).to_party(ghost, slot=1)
        self.mons.append(ghost)
        self.equip()
        self.launch()
        self.record("mega")
        foe = self.session.battle.participants[1].active[0]
        before = foe.hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Tackle B1")
            self.record("attack", "Night Shade A1", side=1)
        self.session.execute_persistent_turn()
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual((holder.species, holder.moves[0].pp), ("Venusaur-Mega", 34))
        self.assertEqual(foe.hp, before)
        self.assertEqual(self.session.battle.mega_used, {"A"})


def add_case(label, method, value):
    """Count each identity/suppression/order independently."""

    def test(self):
        """Use real production commands and SQL assertions for this named control."""
        getattr(self, method)(value)

    setattr(MegaEvolutionCases, "test_" + label, test)


for variant in (
    "bag_only",
    "foreign",
    "egg",
    "box",
    "held_sql_removed",
    "held_runtime_removed",
    "nickname_spoof",
    "transformed",
    "native_spoof",
    "fainted",
    "wrong_stone",
    "wrong_controller",
    "stale_session",
    "inactive_fusion",
    "unsupported_format",
):
    add_case("reject_" + variant, "negative", variant)
for variant in ("flag", "klutz", "embargo", "magicroom"):
    add_case("held_suppression_" + variant, "suppression", variant)
for first in ("mega", "tera"):
    add_case("separate_allies_" + first + "_first", "tera_order", first)
for move in ("Flamethrower", "Ice Beam"):
    add_case("thick_fat_" + move.replace(" ", "_"), "thick_fat", move)
for kind in ("wild", "trainer"):
    add_case("battle_format_" + kind, "battle_kind", kind)
for kind in ("permanent", "temporary"):
    add_case("current_fusion_" + kind, "fusion", kind)
for label in ("A1", "A2", "B1", "B2"):
    add_case("controlled_slot_" + label, "slot_flow", label)
for policy in ("sun_speed", "trickroom", "prankster"):
    add_case("new_move_order_" + policy, "move_order", policy)
for control in ("stats", "owner", "ledger", "side"):
    add_case("corrupt_checkpoint_" + control, "corrupt_checkpoint", control)
for control in ("owner", "egg", "box"):
    add_case("lock_rechecks_" + control, "lock_owner_change", control)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        acquisition.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import (
                cmd_battle_mega,
                cmd_battle_tera,
                cmd_pvp,
                cmd_battle_item,
                cmd_battle_switch,
            )
        from pokemon.battle.battleinstance import BattleSession
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.get_for_model(acquisition.ObjectDB)
        from pokemon.battle.handler import battle_handler
        from pokemon.battle.engine import BattleType
        from pokemon.dex import POKEDEX
        from pokemon.names import resolve_dex_entry
        from pokemon.models.core import OwnedPokemon
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.services.placement import PlacementService
        from pokemon.battle.pokemon_factory import create_battle_pokemon

        acquisition.COMMANDS.update(
            {
                "mega": (cmd_battle_mega, cmd_battle_mega.CmdBattleMega),
                "tera": (cmd_battle_tera, cmd_battle_tera.CmdBattleTera),
                "item": (cmd_battle_item, cmd_battle_item.CmdBattleItem),
                "switch": (cmd_battle_switch, cmd_battle_switch.CmdBattleSwitch),
                "create": (cmd_pvp, cmd_pvp.CmdPvpCreate),
                "join": (cmd_pvp, cmd_pvp.CmdPvpJoin),
                "start": (cmd_pvp, cmd_pvp.CmdPvpStart),
            }
        )
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(MegaEvolutionCases)
            )
        finally:
            if os.environ.get("PF2_MEGA_EVIDENCE"):
                Path(os.environ["PF2_MEGA_EVIDENCE"]).write_text(
                    json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
