"""Per-crystal ordinary acquisition and full-turn damage controls in private SQL."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core
from mega_stone_cases import MegaStoneCases
from pokemon.names import normalize_name


FIXTURES = (
    ("Buginium Z", "Caterpie", "Bug Bite", "Charizard", "Wonder Guard"),
    ("Darkinium Z", "Eevee", "Bite", "Umbreon", "Wonder Guard"),
    ("Dragonium Z", "Altaria", "Dragon Breath", "Clefairy", None),
    ("Electrium Z", "Pikachu", "Thunder Shock", "Diglett", None),
    ("Fairium Z", "Sylveon", "Fairy Wind", "Magnemite", "Wonder Guard"),
    ("Fightinium Z", "Machop", "Karate Chop", "Gastly", None),
    ("Firium Z", "Charmander", "Ember", "Vulpix", "Flash Fire"),
    ("Flyinium Z", "Pidgeotto", "Wing Attack", "Magnemite", "Wonder Guard"),
    ("Ghostium Z", "Gastly", "Lick", "Eevee", None),
    ("Grassium Z", "Bulbasaur", "Vine Whip", "Vulpix", "Sap Sipper"),
    ("Groundium Z", "Diglett", "Mud-Slap", "Gastly", "Levitate"),
    ("Icium Z", "Swinub", "Powder Snow", "Vulpix", "Wonder Guard"),
    ("Poisonium Z", "Ekans", "Poison Sting", "Magnemite", None),
    ("Psychium Z", "Kadabra", "Confusion", "Umbreon", None),
    ("Rockium Z", "Geodude", "Rock Throw", "Geodude", "Wonder Guard"),
    ("Steelium Z", "Aron", "Metal Claw", "Magnemite", "Wonder Guard"),
    ("Waterium Z", "Squirtle", "Water Gun", "Vaporeon", "Water Absorb"),
)


class GenericZCases(unittest.TestCase):
    """Separate native/move/control setup from ordinary purchased-item input."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild
    fixture_native = MegaStoneCases.fixture_native
    failed_purchase = MegaStoneCases.failed_purchase

    def setUp(self):
        """Build ordinary transports and tagged sources only in this private schema."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """End the production session and clean only this case's objects."""
        core.MegaEvolutionCases.tearDown(self)

    def flow(self, fixture, control):
        """Buy, equip, queue, rebuild, execute, inspect SQL, end and return."""
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.services.item_counter import ItemCounter
        from pokemon.battle.z_profiles import ZProfiles

        item, native, source, immune_native, immune_ability = fixture
        if self.session:
            self.session.end()
            self.session = None
        quantity = self.player.trainer.get_item_quantity(item)
        if quantity:
            self.player.trainer.remove_item(item, quantity)
        self.mon = self.fixture_native(native, [source, "Growl"], 3)
        self.foe = self.fixture_native(
            immune_native if control == "immune" else "Mew",
            ["Protect", "Splash"],
            1,
            side=1,
            level=100,
        )
        if control == "immune" and immune_ability:
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability=immune_ability)
            core.OwnedPokemon.flush_cached_instance(self.foe)
        if control == "sleep":
            core.OwnedPokemon.objects.filter(pk=self.mon.pk).update(status="slp", sleep_turns=3)
            core.OwnedPokemon.flush_cached_instance(self.mon)
        offers = ItemCounter("world/z_crystal_counter.json").recipe()["offers"]
        self.assertIn({"item": item, "price": 10000, "quantity": 1}, offers)
        if control == "active":
            self.room.db.store_inventory = {item: {"price": 10000, "quantity": 1}}
            wallet = self.state()["wallet"]
            self.player.trainer.money = 9999
            self.player.trainer.save(update_fields=["money"])
            self.failed_purchase(item, "insufficient-funds")
            self.player.trainer.money = wallet
            self.player.trainer.save(update_fields=["money"])
        self.buy(item, price=10000, quantity=1)
        if control == "active":
            self.failed_purchase(item, "sold-out")
        self.record("hold", "3=" + item)
        self.launch("double")
        battle = self.session.battle
        holder, target = (part.active[0] for part in battle.participants)
        profile = ZProfiles.get(item, source)
        self.assertIsNotNone(profile)
        from pokemon.battle.legal_actions import LegalActions

        descriptor = profile.descriptor(
            LegalActions(battle, battle.participants[0], holder)._move(holder.moves[0])
        )
        self.assertIn(descriptor.power, {100, 120})
        self.assertEqual(descriptor.priority, 0)
        self.assertIs(descriptor.accuracy, True)
        self.assertFalse(descriptor.raw["flags"].get("contact"))
        self.assertFalse(
            any(
                descriptor.raw.get(k)
                for k in ("secondary", "secondaries", "recoil", "drain", "multihit", "self")
            )
        )
        initial_pp = next(
            s
            for s in battle._move_pp_states(holder)
            if normalize_name(s[1]) == normalize_name(source)
        )[2]
        self.record("zmove", "A1")
        for field, value in (
            ("transformed", True),
            ("species", "Pikachu" if native == "Eevee" else "Eevee"),
            ("item", "Normalium Z"),
        ):
            old = getattr(holder, field, None)
            setattr(holder, field, value)
            before = self.observation()
            self.record("zmove", "A1 " + source + "=B1")
            self.assertEqual(self.observation(), before)
            setattr(holder, field, old)
        before = self.observation()
        self.record("zmove", "A1 Invented Move=B1")
        self.assertEqual(self.observation(), before)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("zmove", "A1 " + source + "=B1")
            self.record("attack", "A2 Growl B1")
            self.record(
                "attack", "B1 " + ("Protect B1" if control == "protect" else "Splash B1"), side=1
            )
            self.record("attack", "B2 Growl A2", side=1)
        self.rebuild()
        battle = self.session.battle
        # Reconnect creates a fresh private RNG. Seed this actual execution,
        # rather than comparing unrelated post-reconnect damage rolls.
        battle.rng = random.Random(12)
        holder, target = (part.active[0] for part in battle.participants)
        hp, before = target.hp, self.observation()
        self.session.execute_persistent_turn()
        damage = hp - target.hp
        used = control != "sleep"
        self.assertEqual(battle.z_used, {"A"} if used else set())
        slot = ActiveMoveslot.objects.get(pokemon=self.mon, slot=1)
        self.assertEqual(slot.current_pp, initial_pp - int(used))
        if control in {"sleep", "immune"}:
            self.assertEqual(damage, 0)
        else:
            self.assertGreater(damage, 0)
        self.assertFalse(target.status)
        result = {
            "damage": damage,
            "pp_before": initial_pp,
            "pp_after": slot.current_pp,
            "power": profile.power,
            "type": profile.move_type,
            "category": profile.category,
        }
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "generic-Z-effect",
                "item": item,
                "source": source,
                "native": native,
                "control": control,
                "before": before,
                "after": self.observation(),
                "effect": result,
            }
        )
        self.rebuild()
        self.assertEqual(self.session.battle.z_used, {"A"} if used else set())
        self.session.end()
        self.session = None
        self.assertEqual(
            normalize_name(core.OwnedPokemon.objects.get(pk=self.mon.pk).held_item),
            normalize_name(item),
        )
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        return result

    def pair(self, fixture):
        """Each reviewed pair gets damage/protection/prevention/immunity controls."""
        ordinary = self.flow(fixture, "active")
        protected = self.flow(fixture, "protect")
        self.assertEqual(protected["damage"], max(1, ordinary["damage"] // 4))
        self.flow(fixture, "sleep")
        self.flow(fixture, "immune")


for _fixture in FIXTURES:

    def _case(self, fixture=_fixture):
        """Exercise this exact published source with actual player commands."""
        self.pair(fixture)

    setattr(GenericZCases, "test_" + _fixture[0].replace(" ", "_"), _case)


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
                unittest.defaultTestLoader.loadTestsFromTestCase(GenericZCases)
            )
        finally:
            if os.environ.get("PF2_Z_EVIDENCE"):
                Path(os.environ["PF2_Z_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
