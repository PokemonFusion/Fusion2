"""Exact signature player inputs, private SQL and meaningful intrinsic controls."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from z_status_cases import StatusZCases
from pokemon.battle.z_signature_pairs import SIGNATURE_PAIRS
from pokemon.names import normalize_name


IMMUNE = {
    "Normal": "Gastly",
    "Ghost": "Eevee",
    "Electric": "Diglett",
    "Dragon": "Clefairy",
    "Psychic": "Umbreon",
}


class SignatureZCases(unittest.TestCase):
    """Separate deliberate native/foe setup from ordinary crystal acquisition."""

    command = StatusZCases.command
    reply = StatusZCases.reply
    state = StatusZCases.state
    native = StatusZCases.native
    buy = StatusZCases.buy
    record = StatusZCases.record
    observation = StatusZCases.observation
    launch = StatusZCases.launch
    rebuild = StatusZCases.rebuild
    fixture_native = StatusZCases.fixture_native

    def setUp(self):
        """Only disposable ordinary controllers and tagged source fixtures."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """Commit the production end and clean only our local fixture objects."""
        core.MegaEvolutionCases.tearDown(self)

    def flow(self, profile, control="active", *, native=None, finish=True, captured=None):
        """Buy/hold/discover/queue/rebuild/execute/end/return for an exact signature."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.services.item_counter import ItemCounter

        item, source = profile.crystal, profile.source
        self.assertIn(
            {"item": item, "price": 10000, "quantity": 1},
            ItemCounter("world/z_crystal_counter.json").recipe()["offers"],
        )
        if self.session:
            self.session.end()
            self.session = None
        quantity = self.player.trainer.get_item_quantity(item)
        if quantity:
            self.player.trainer.remove_item(item, quantity)
        self.mon = captured or self.fixture_native(
            native or profile.native[0], [source, "Tackle"], 3
        )
        self.fixture_native("Eevee", ["Helping Hand", "Tail Whip"], 4)
        foe_native = (
            IMMUNE.get(profile.move_type, "Umbreon" if profile.move_type == "Dark" else "Mew")
            if control == "immune"
            else "Mew"
        )
        self.foe = self.fixture_native(foe_native, ["Splash", "Protect"], 1, side=1, level=100)
        self.fixture_native("Mew", ["Splash"], 2, side=1, level=100)
        core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Run Away")
        core.OwnedPokemon.flush_cached_instance(self.foe)
        if control == "immune" and profile.move_type not in IMMUNE:
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Wonder Guard")
            core.OwnedPokemon.flush_cached_instance(self.foe)
        if control == "sleep":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
            core.OwnedPokemon.flush_cached_instance(self.mon)
        if control == "sheerforce":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(ability="Sheer Force")
            core.OwnedPokemon.flush_cached_instance(self.mon)
        self.buy(item, price=10000, quantity=1)
        self.record("hold", "3=" + item)
        self.launch("double")
        battle = self.session.battle
        user, target = (part.active[0] for part in battle.participants)
        source_slot = next(
            slot
            for slot in ActiveMoveslot.objects.filter(pokemon=self.mon).select_related("move")
            if normalize_name(slot.move.name) == normalize_name(source)
        )
        initial_pp = source_slot.current_pp
        if profile.intrinsic == "clearterrain":
            battle.setTerrain("electricterrain", source=target)
        if profile.source == "Spectral Thief":
            target.boosts.update(attack=2, defense=2, special_attack=2)
        if profile.source == "Darkest Lariat":
            target.boosts["defense"] = 2
        if profile.category == "Status":
            user.boosts.update(attack=5, defense=-5)
        if profile.source == "Sparkling Aria":
            battle.apply_status_condition(target, "brn", source=user)
        before = self.observation()
        self.record("zmove", "A1")
        self.assertEqual(self.observation(), before)
        with patch.object(self.session, "maybe_run_turn"):
            self.record(
                "zmove", "A1 " + source + "=" + ("A1" if profile.target == "self" else "B1")
            )
            self.record("attack", "A2 Helping Hand A1")
            self.record(
                "attack", "B1 " + ("Protect B1" if control == "protect" else "Splash B1"), side=1
            )
            self.record("attack", "B2 Splash B2", side=1)
        self.assertIn("A", battle.z_pending, self.player.messages[-5:])
        self.rebuild()
        battle = self.session.battle
        battle.rng = random.Random(12)
        user, target = (part.active[0] for part in battle.participants)
        hp, peer_hp, own_hp = target.hp, battle.participants[1].active[1].hp, user.hp
        before = self.observation()
        self.session.execute_persistent_turn()
        damage, peer_damage = hp - target.hp, peer_hp - battle.participants[1].active[1].hp
        if profile.source == "Sparkling Aria":
            damage -= max(1, target.max_hp // 16)
        if profile.intrinsic == "guardian" and battle.field.terrain == "grassyterrain" and damage:
            # Tapu Bulu's actual native Surge heals grounded targets at residual.
            damage += max(1, target.max_hp // 16)
        spent = control != "sleep"
        self.assertEqual(battle.z_used, {"A"} if spent else set())
        self.assertEqual(
            ActiveMoveslot.objects.get(pk=source_slot.pk).current_pp, initial_pp - int(spent)
        )
        if profile.category == "Status":
            self.assertEqual(user.boosts["attack"], 6 if spent else 5)
            self.assertEqual(user.boosts["defense"], -3 if spent else -5)
            self.assertEqual(user.boosts["speed"], 2 if spent else 0)
            self.assertEqual(damage, 0)
        elif (
            control == "sleep"
            or control == "immune"
            and (profile.move_type in IMMUNE or not profile.ignore_ability)
        ):
            self.assertEqual(damage, 0)
        else:
            self.assertGreater(damage, 0)
        self.assertEqual(user.hp, own_hp, "No ordinary recoil may leak into a signature")
        self.assertFalse(user.volatiles.get("mustrecharge"))
        self.assertFalse(target.volatiles.get("trapped"))
        if profile.intrinsic == "paralysis":
            self.assertEqual(target.status, "par" if damage else 0)
        if profile.source == "Sparkling Aria":
            self.assertEqual(target.status, "brn")
        if profile.source == "Spectral Thief":
            self.assertEqual(target.boosts["attack"], 2)
            self.assertEqual(user.boosts["attack"], 0)
        if profile.intrinsic == "guardian" and control not in {"sleep", "immune"}:
            expected = max(1, ((3 * hp // 4) + 1) // 4 if control == "protect" else 3 * hp // 4)
            self.assertEqual(damage, expected)
        if profile.intrinsic == "soulblaze":
            bonus = int(bool(peer_damage) and control != "sheerforce")
            self.assertEqual(user.boosts["defense"], bonus)
            self.assertEqual(user.boosts["attack"], bonus)
            self.assertEqual(bool(peer_damage), spent)
        else:
            self.assertEqual(peer_damage, 0)
        if profile.intrinsic == "clearterrain":
            self.assertEqual(battle.field.terrain, None if damage else "electricterrain")
        if profile.intrinsic == "psychicterrain":
            self.assertEqual(battle.field.terrain, "psychicterrain" if damage else None)
        effect = {
            "damage": damage,
            "peer_damage": peer_damage,
            "hp_before": hp,
            "user": user.to_dict(),
            "target": target.to_dict(),
            "terrain": battle.field.terrain,
        }
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "signature-Z-effect",
                "item": item,
                "native": native or profile.native[0],
                "source": source,
                "control": control,
                "before": before,
                "after": self.observation(),
                "effect": effect,
            }
        )
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if spent else set())
        self.assertEqual(self.session.battle.field.terrain, effect["terrain"])
        if finish:
            self.session.end()
            self.session = None
            self.assertEqual(
                normalize_name(core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item),
                normalize_name(item),
            )
            self.record("hold", "3=")
            self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        return effect

    def signature(self, profile):
        """Every signature has actual useful/prevented/protected/immune controls."""
        active = self.flow(profile)
        protected = self.flow(profile, "protect")
        if profile.power and active["damage"]:
            self.assertEqual(protected["damage"], max(1, active["damage"] // 4))
        self.flow(profile, "sleep")
        if profile.category != "Status":
            self.flow(profile, "immune")

    def test_soulblaze_sheer_force_removes_bonus_and_boosts_actual_damage(self):
        """Use the real ability consumer, with one five-stat bonus at most."""
        from pokemon.battle.z_profiles import ZProfiles

        profile = ZProfiles.get("Kommonium Z", "Clanging Scales")
        normal = self.flow(profile)
        sheer = self.flow(profile, "sheerforce")
        self.assertGreater(sheer["damage"], normal["damage"])
        self.assertGreater(sheer["peer_damage"], normal["peer_damage"])

    def test_real_disguise_break_then_rebuilt_busted_holder_uses_signature(self):
        """An owned intact Mimikyu earns Busted eligibility through real damage."""
        self.disguise("Mimikyu")

    def test_real_totem_disguise_break_retains_the_matching_native_holder(self):
        """The Totem's actual broken disguise remains bound to its intact owner."""
        self.disguise("Mimikyu-Totem")

    def disguise(self, species):
        """Exercise actual damage, ability form change, reconnect and paid input."""
        from pokemon.models.moves import ActiveMoveslot

        self.mon = self.fixture_native(species, ["Play Rough", "Splash"], 3)
        self.foe = self.fixture_native("Mew", ["Bite", "Splash"], 1, side=1, level=100)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(nickname="Button")
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.buy("Mimikium Z", price=10000, quantity=1)
        self.record("hold", "3=Mimikium Z")
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "Splash A1")
            self.record("attack", "Bite A1", side=1)
        self.session.execute_persistent_turn()
        user = self.session.battle.participants[0].active[0]
        busted = "Mimikyu-Busted-Totem" if species == "Mimikyu-Totem" else "Mimikyu-Busted"
        self.assertEqual(str(user.species), busted)
        self.assertEqual(user.name, "Button")
        self.rebuild()
        user = self.session.battle.participants[0].active[0]
        self.assertEqual(str(user.species), busted)
        for reserve in ("5", "3"):
            with patch.object(self.session, "maybe_run_turn"):
                self.record("switch", reserve)
                self.record("attack", "Splash B1", side=1)
            self.session.execute_persistent_turn()
            self.rebuild()
        user = self.session.battle.participants[0].active[0]
        self.assertEqual(str(user.species), busted)
        self.assertEqual(user.name, "Button")
        hp = self.session.battle.participants[1].active[0].hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Play Rough=B1")
            self.record("attack", "Splash B1", side=1)
        self.assertIn("A", self.session.battle.z_pending, self.player.messages[-4:])
        self.session.execute_persistent_turn()
        self.assertLess(self.session.battle.participants[1].active[0].hp, hp)
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, 9)
        self.rebuild()
        self.session.end()
        self.session = None
        self.assertEqual(core.OwnedPokemon.objects.get(pk=self.mon.pk).species, species)

    def test_other_explicit_ordinary_native_holders(self):
        """All five alternative ordinary Lycanroc/Tapu holders get player routes."""
        from pokemon.battle.z_profiles import ZProfiles

        for item, source in (("Lycanium Z", "Stone Edge"), ("Tapunium Z", "Nature's Madness")):
            profile = ZProfiles.get(item, source)
            for native in profile.native[1:]:
                self.flow(profile, native=native)

    def test_all_signatures_reject_a_nicknamed_foreign_native_before_queue(self):
        """Owning the item/source and matching nickname cannot forge native access."""
        for profile in SIGNATURE_PAIRS:
            if self.session:
                self.session.end()
                self.session = None
            self.mon = self.fixture_native(
                "Pikachu" if profile.native[0] == "Eevee" else "Eevee", [profile.source], 3
            )
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(nickname=profile.native[0])
            core.OwnedPokemon.flush_cached_instance(self.mon)
            self.buy(profile.crystal, price=10000, quantity=1)
            self.record("hold", "3=" + profile.crystal)
            self.launch()
            before = self.observation()
            self.record(
                "zmove", profile.source + "=" + ("A1" if profile.target == "self" else "B1")
            )
            self.assertEqual(self.observation(), before)

    def test_signature_terrain_fault_rolls_back_damage_pp_field_rng_and_output(self):
        """Fail after the actual Genesis terrain effect, then retry the full input."""
        from pokemon.battle.z_effects import ZEffects

        self.mon = self.fixture_native("Mew", ["Psychic"], 3)
        self.foe = self.fixture_native("Mew", ["Splash"], 1, side=1, level=100)
        self.buy("Mewnium Z", price=10000, quantity=1)
        self.record("hold", "3=Mewnium Z")
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Psychic=B1")
            self.record("attack", "Splash B1", side=1)
        before, rng = self.observation(), self.session.battle.rng.getstate()
        start = len(self.player.messages)
        original = ZEffects.hit

        def fail(*args):
            """The production damage and field mutation have already occurred."""
            original(*args)
            raise RuntimeError("signature terrain fixture")

        with patch.object(ZEffects, "hit", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "signature terrain fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.session.battle.rng.getstate(), rng)
        self.assertFalse(any("unleashed" in str(m) for m in self.player.messages[start:]))
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.field.terrain, "psychicterrain")
        self.assertEqual(self.session.battle.z_used, {"A"})


for _profile in SIGNATURE_PAIRS:

    def _case(self, profile=_profile):
        """Qualify one frozen exact native/source/signature contract."""
        self.signature(profile)

    setattr(SignatureZCases, "test_" + normalize_name(_profile.crystal), _case)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet

        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_zmove
        core.acquisition.COMMANDS["zmove"] = cmd_battle_zmove, cmd_battle_zmove.CmdBattleZMove
        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(SignatureZCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
