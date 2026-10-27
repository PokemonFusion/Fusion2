"""Bounded Z status bonuses and their ordinary base effects through player input."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from z_generic_cases import GenericZCases


FIXTURES = (
    ("Normalium Z", "Magikarp", "Splash"),
    ("Normalium Z", "Eevee", "Growl"),
    ("Normalium Z", "Scyther", "Swords Dance"),
    ("Icium Z", "Koffing", "Haze"),
    ("Darkinium Z", "Koffing", "Memento"),
    ("Ghostium Z", "Gastly", "Destiny Bond"),
    ("Flyinium Z", "Pidgeot", "Tailwind"),
    ("Ghostium Z", "Gastly", "Curse"),
    ("Ghostium Z", "Onix", "Curse"),
)


class StatusZCases(unittest.TestCase):
    """Keep fixture preparation distinct from ordinary human inputs and SQL proof."""

    command = GenericZCases.command
    reply = GenericZCases.reply
    state = GenericZCases.state
    native = GenericZCases.native
    buy = GenericZCases.buy
    record = GenericZCases.record
    observation = GenericZCases.observation
    launch = GenericZCases.launch
    rebuild = GenericZCases.rebuild
    fixture_native = GenericZCases.fixture_native

    def setUp(self):
        """Create only disposable native owners and ordinary transports."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """Use real end synchronization and clean only these disposable objects."""
        core.MegaEvolutionCases.tearDown(self)

    def flow(self, fixture, control="active", *, finish=True):
        """Acquire/equip, discover, queue/rebuild, observe exact bonus/base/PP effects."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.battle.z_profiles import ZProfiles

        item, native, source = fixture
        if self.session:
            self.session.end()
            self.session = None
        quantity = self.player.trainer.get_item_quantity(item)
        if quantity:
            self.player.trainer.remove_item(item, quantity)
        self.mon = self.fixture_native(native, [source, "Tackle"], 3)
        self.fixture_native("Eevee", ["Helping Hand", "Tail Whip"], 4)
        self.foe = self.fixture_native(
            "Mew", ["Splash", "Protect", "Taunt", "False Swipe"], 1, side=1, level=100
        )
        if control == "bounce":
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability="Magic Bounce")
            core.OwnedPokemon.flush_cached_instance(self.foe)
        if source in {"Haze", "Curse"}:
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
                current_hp=max(1, self.mon.get_max_hp() // 3)
            )
        if control == "sleep":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
        core.OwnedPokemon.flush_cached_instance(self.mon)
        if source == "Memento":
            self.fixture_native("Eevee", ["Tail Whip", "Tackle"], 2, side=1)
            reserve = next(
                row
                for row in self.mons
                if row.trainer_id == self.player.trainer.pk and row.species == "Pikachu"
            )
            core.OwnedPokemon.objects.filter(pk=reserve.pk).update(
                current_hp=1, status="slp", sleep_turns=3
            )
            core.OwnedPokemon.flush_cached_instance(reserve)
        self.buy(item, price=10000, quantity=1)
        self.record("hold", "3=" + item)
        self.launch("double")
        battle = self.session.battle
        user, target = (part.active[0] for part in battle.participants)
        if source == "Swords Dance":
            user.boosts.update(attack=-2, defense=2, speed=-3)
        if source == "Haze":
            user.boosts["attack"], target.boosts["defense"] = 2, -2
        initial = deepcopy(user.to_dict())
        profile = ZProfiles.get(item, source)
        self.assertIsNotNone(profile)
        before, start = self.observation(), len(self.player.messages)
        self.record("zmove", "A1")
        self.assertEqual(self.observation(), before)
        self.assertIn(item, "\n".join(map(str, self.player.messages[start:])))
        target_label = (
            "B1"
            if source in {"Growl", "Memento"} or source == "Curse" and native == "Gastly"
            else "A1"
        )
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "A1 1=" + target_label)
            self.record("attack", "A2 Helping Hand A1")
            self.record(
                "attack", "B1 " + ("Protect B1" if control == "protect" else "Splash B1"), side=1
            )
            self.record("attack", "B2 Tackle A2", side=1)
        self.assertIn("A", battle.z_pending, self.player.messages[-5:])
        self.rebuild()
        battle = self.session.battle
        battle.rng = random.Random(12)
        user = next(
            mon
            for mon in battle.participants[0].pokemons
            if mon.model_id == "owned:" + str(self.mon.pk)
        )
        target, ally = battle.participants[1].active[0], battle.participants[0].active[1]
        ally_hp = ally.hp
        before = self.observation()
        self.session.execute_persistent_turn()
        spent = control != "sleep"
        self.assertEqual(battle.z_used, {"A"} if spent else set())
        pp = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        self.assertEqual(pp, initial["moves"][0]["pp"] - int(spent))
        if not spent:
            self.assertFalse(getattr(user, "z_activated", False))
        elif source == "Splash":
            self.assertEqual(user.boosts["attack"], 3)
        elif source == "Growl":
            self.assertEqual(user.boosts["defense"], 1)
            self.assertEqual(target.boosts["attack"], 0 if control in {"protect", "bounce"} else -1)
            self.assertEqual(battle.participants[1].active[1].boosts["attack"], -1)
            self.assertEqual(user.boosts["attack"], -1 if control == "bounce" else 0)
            self.assertEqual(ally.boosts["attack"], 0)
        elif source == "Swords Dance":
            self.assertEqual(
                (user.boosts["attack"], user.boosts["defense"], user.boosts["speed"]), (2, 2, 0)
            )
        elif source == "Haze":
            self.assertEqual(user.hp, user.max_hp)
            self.assertTrue(
                all(
                    value == 0
                    for part in battle.participants
                    for mon in part.active
                    for value in mon.boosts.values()
                )
            )
        elif source == "Curse" and native == "Gastly":
            self.assertEqual(user.hp, user.max_hp - user.max_hp // 2)
            self.assertTrue(target.volatiles.get("cursed"))
            self.assertEqual(target.hp, target.max_hp - target.max_hp // 4)
        elif source == "Curse":
            self.assertEqual(user.hp, initial["current_hp"])
            self.assertEqual(
                (user.boosts["attack"], user.boosts["defense"], user.boosts["speed"]), (2, 1, -1)
            )
        elif source == "Destiny Bond":
            self.assertTrue(user.volatiles.get("destinybond"))
            self.assertFalse(user.volatiles.get("followme"))
            self.assertEqual(ally.hp, ally_hp)
        elif source == "Tailwind":
            self.assertTrue(user.volatiles.get("focusenergy"))
            self.assertIn("tailwind", battle.participants[0].side.conditions)
        elif source == "Memento":
            if control == "protect":
                self.assertGreater(user.hp, 0)
                self.assertEqual(battle.z_replacement["A"], {"0": str(user.model_id)})
            else:
                self.assertEqual(user.hp, 0)
                self.assertEqual(
                    (target.boosts["attack"], target.boosts["special_attack"]), (-2, -2)
                )
                incoming = battle.participants[0].active[0]
                self.assertEqual(incoming.hp, incoming.max_hp)
                self.assertEqual(incoming.status, "slp")
        effect = {
            "user": user.to_dict(),
            "target": target.to_dict(),
            "selected_effects": deepcopy(self.session.logic.to_dict()["state"]["z_effects"]),
        }
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "status-Z-effect",
                "item": item,
                "native": native,
                "source": source,
                "control": control,
                "before": before,
                "after": self.observation(),
                "effect": effect,
            }
        )
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if spent else set())
        if spent and source == "Tailwind":
            self.assertIn("tailwind", self.session.battle.participants[0].side.conditions)
        if finish:
            self.session.end()
            self.session = None
            self.record("hold", "3=")
            self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        return effect

    def source(self, fixture):
        """Each exact named source gets real useful/base, prevention and Protect routes."""
        for control in ("active", "sleep", "protect"):
            self.flow(fixture, control)

    def auxiliary_turn(self, action, args, *, opponent="Splash B1"):
        """Advance a full ordinary doubles turn without hidden direct effects."""
        with patch.object(self.session, "maybe_run_turn"):
            self.record(action, "A1 " + args)
            self.record("attack", "A2 Tail Whip B2")
            self.record("attack", "B1 " + opponent, side=1)
            # After the one initial damage witness, these actors are inert
            # controls for the pending-slot and timer lifetime observations.
            self.record("attack", "B2 Tail Whip A2", side=1)
        self.session.execute_persistent_turn()

    def test_memento_pending_heal_is_slot_bound_durable_and_consumed_once(self):
        """Protected Memento retains its bonus for a later actual incoming holder."""
        self.flow(("Darkinium Z", "Koffing", "Memento"), "protect", finish=False)
        self.assertTrue(self.session.battle.z_replacement["A"].get("0"))
        self.rebuild()
        self.auxiliary_turn("switch", "5")
        incoming = self.session.battle.participants[0].active[0]
        self.assertEqual(incoming.hp, incoming.max_hp)
        self.assertEqual(incoming.status, "slp")
        self.assertFalse(self.session.battle.z_replacement.get("A"))
        self.rebuild()
        self.auxiliary_turn("attack", "Tackle B1", opponent="False Swipe A1")
        incoming = self.session.battle.participants[0].active[0]
        hp = incoming.hp
        self.assertLess(hp, incoming.max_hp)
        self.rebuild()
        self.assertEqual(self.session.battle.participants[0].active[0].hp, hp)
        self.auxiliary_turn("switch", "3")
        self.rebuild()
        self.auxiliary_turn("switch", "5")
        self.assertEqual(self.session.battle.participants[0].active[0].hp, hp)
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_growl_reflects_only_ordinary_base_effect_not_bonus_or_extra_ally(self):
        """Magic Bounce reflects one base target while the original Z bonus stays paid."""
        self.flow(("Normalium Z", "Eevee", "Growl"), "bounce")

    def test_bonus_and_source_payment_roll_back_with_a_failed_turn(self):
        """A real post-bonus exception restores the whole input and permits one retry."""
        from pokemon.battle.z_effects import ZEffects

        self.mon = self.fixture_native("Eevee", ["Growl", "Tackle"], 3)
        self.buy("Normalium Z", price=10000, quantity=1)
        self.record("hold", "3=Normalium Z")
        self.launch()
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Growl=B1")
            self.record("attack", "Growl A1", side=1)
        before = self.observation()
        rng = self.session.battle.rng.getstate()
        start = len(self.player.messages)
        original = ZEffects.start

        def fail(*args):
            """Raise after the production bonus and owned PP payment."""
            original(*args)
            raise RuntimeError("Z status bonus fixture")

        with patch.object(ZEffects, "start", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "Z status bonus fixture"):
                self.session.execute_persistent_turn()
        self.assertEqual(self.observation(), before)
        self.assertEqual(self.session.battle.rng.getstate(), rng)
        self.assertFalse(any("unleashed" in str(m) for m in self.player.messages[start:]))
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.z_used, {"A"})
        self.assertEqual(self.session.battle.participants[0].active[0].boosts["defense"], 1)

    def test_corrupt_selected_effect_ledgers_fail_closed(self):
        """Neither a forged slot heal nor an unknown effect version can be recovered."""
        from pokemon.battle.logic import BattleLogic

        self.flow(("Darkinium Z", "Koffing", "Memento"), "protect", finish=False)
        saved = self.session.logic.to_dict()
        for field, value in (
            ("version", 2),
            ("replacement", {"B": {"0": "owned:" + str(self.mon.pk)}}),
            ("tailwind", {"A": 3}),
        ):
            damaged = deepcopy(saved)
            damaged["state"]["z_effects"][field] = value
            with self.assertRaises(ValueError):
                BattleLogic.from_dict(damaged)

    def restriction(self, effect):
        """An actual faster restrictive move prevents Z, then rejects a fresh input."""
        from pokemon.models.moves import ActiveMoveslot

        self.mon = self.fixture_native("Eevee", ["Growl", "Tackle"], 3)
        self.foe = self.fixture_native(
            "Gardevoir", [effect, "Splash", "Growl"], 1, side=1, level=100
        )
        self.buy("Normalium Z", price=10000, quantity=1)
        self.record("hold", "3=Normalium Z")
        self.launch()
        if effect in {"Disable", "Encore"}:
            with patch.object(self.session, "maybe_run_turn"):
                self.record("attack", ("Growl" if effect == "Disable" else "Tackle") + " B1")
                self.record("attack", "Splash B1", side=1)
            self.session.execute_persistent_turn()
        current = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Growl=B1")
            self.record("attack", effect + (" B1" if effect == "Imprison" else " A1"), side=1)
        before = self.observation()
        self.session.execute_persistent_turn()
        self.assertFalse(self.session.battle.z_used)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.mon, slot=1).current_pp, current)
        self.assertEqual(self.session.battle.participants[0].active[0].boosts["defense"], 0)
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "actual-source-restriction",
                "effect": effect,
                "before": before,
                "after": self.observation(),
            }
        )
        before = self.observation()
        self.record("zmove", "Growl=B1")
        self.assertEqual(self.observation(), before)

    def test_current_type_change_changes_curse_branch_without_undoing_the_turn(self):
        """A real faster Soak makes Ghost Curse use its current non-Ghost branch."""
        self.mon = self.fixture_native("Gastly", ["Curse", "Lick"], 3)
        self.foe = self.fixture_native("Golduck", ["Soak"], 1, side=1, level=100)
        core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(
            current_hp=self.mon.get_max_hp() // 3
        )
        core.OwnedPokemon.flush_cached_instance(self.mon)
        self.buy("Ghostium Z", price=10000, quantity=1)
        self.record("hold", "3=Ghostium Z")
        self.launch()
        user = self.session.battle.participants[0].active[0]
        hp = user.hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "Curse=B1")
            self.record("attack", "Soak A1", side=1)
        self.session.execute_persistent_turn()
        self.assertEqual(user.types, ["Water"])
        self.assertEqual(user.hp, hp)
        self.assertEqual(
            (user.boosts["attack"], user.boosts["defense"], user.boosts["speed"]), (2, 1, -1)
        )
        self.assertEqual(self.session.battle.z_used, {"A"})

    def test_tailwind_timer_expires_across_actual_turns_and_rebuilds(self):
        """A checkpoint must preserve remaining time rather than restart Tailwind."""
        self.flow(("Flyinium Z", "Pidgeot", "Tailwind"), finish=False)
        for remaining in (2, 1, 0):
            self.rebuild()
            self.auxiliary_turn("attack", "Tackle B1")
            condition = self.session.battle.participants[0].side.conditions.get("tailwind")
            self.assertEqual(condition.get("duration") if condition else 0, remaining)

    def test_boost_bonus_obeys_caps_on_the_opposite_doubles_actor(self):
        """A side-B second actor gets one capped bonus and pays its own source."""
        self.mon = self.fixture_native("Eevee", ["Tackle"], 3)
        self.foe = self.fixture_native("Magikarp", ["Splash"], 2, side=1)
        self.players[1].trainer.add_item("Normalium Z")
        self.record("hold", "2=Normalium Z", side=1)
        self.launch("double")
        actor = self.session.battle.participants[1].active[1]
        actor.boosts["attack"] = 5
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "B2 Splash=B2", side=1)
            self.record("attack", "B1 Growl A1", side=1)
            self.record("attack", "A1 Tackle B1")
            self.record("attack", "A2 Tackle B1")
        self.session.execute_persistent_turn()
        self.assertEqual(actor.boosts["attack"], 6)
        self.assertEqual(self.session.battle.z_used, {"B"})


for _fixture in FIXTURES:

    def _case(self, fixture=_fixture):
        """Qualify this reviewed native/source combination through actual inputs."""
        self.source(fixture)

    setattr(
        StatusZCases,
        "test_" + _fixture[1].replace("-", "_") + "_" + _fixture[2].replace(" ", "_"),
        _case,
    )

for _effect in ("Taunt", "Disable", "Encore", "Imprison"):

    def _case(self, effect=_effect):
        """Exercise one actual source restriction in its own fresh SQL/player fixture."""
        self.restriction(effect)

    setattr(StatusZCases, "test_restriction_" + _effect, _case)


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
                unittest.defaultTestLoader.loadTestsFromTestCase(StatusZCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
