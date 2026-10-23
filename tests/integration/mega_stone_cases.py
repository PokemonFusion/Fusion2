"""Per-stone ordinary acquisition, native activation and actual effect controls."""

from copy import deepcopy
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from isolated_postgres import IsolatedPostgres
import mega_evolution_cases as core


# The explicit attack fixtures are separate native/learned-move setup, not grants
# made by a player command or a claim of live species acquisition.
POWER_PAIRS = {
    "Aerodactylite": ("Aerodactyl", "Aerial Ace"),
    "Charizardite X": ("Charizard", "Dragon Claw"),
    "Mawilite": ("Mawile", "Bite"),
    "Medichamite": ("Medicham", "Force Palm"),
    "Metagrossite": ("Metagross", "Aerial Ace"),
    "Scizorite": ("Scizor", "Bullet Punch"),
    "Beedrillite": ("Beedrill", "Poison Jab"),
    "Lucarionite": ("Lucario", "Force Palm"),
    "Blastoisinite": ("Blastoise", "Water Pulse"),
    "Cameruptite": ("Camerupt", "Earth Power"),
    "Sharpedonite": ("Sharpedo", "Bite"),
    "Garchompite": ("Garchomp", "Metal Claw"),
    "Steelixite": ("Steelix", "Iron Tail"),
    "Houndoominite": ("Houndoom", "Ember"),
}
CONVERSION_PAIRS = {
    "Altarianite": ("Altaria", "Fairy"),
    "Gardevoirite": ("Gardevoir", "Fairy"),
    "Glalitite": ("Glalie", "Ice"),
    "Pinsirite": ("Pinsir", "Flying"),
    "Salamencite": ("Salamence", "Flying"),
}


class MegaStoneCases(unittest.TestCase):
    """Exercise production commands; fixture controls are explicitly separate."""

    command = core.MegaEvolutionCases.command
    reply = core.MegaEvolutionCases.reply
    state = core.MegaEvolutionCases.state
    native = core.MegaEvolutionCases.native
    buy = core.MegaEvolutionCases.buy
    record = core.MegaEvolutionCases.record
    observation = core.MegaEvolutionCases.observation
    launch = core.MegaEvolutionCases.launch
    rebuild = core.MegaEvolutionCases.rebuild

    def setUp(self):
        """Build ordinary controllers and a fresh source in a disposable schema."""
        core.MegaEvolutionCases.setUp(self)

    def tearDown(self):
        """Use the existing fixture cleanup and real end synchronization."""
        core.MegaEvolutionCases.tearDown(self)

    def fixture_native(self, species, moves, slot, *, side=0, level=50):
        """Create native owned sources with calculated stats and actual move rows."""
        player = self.players[side]
        for placement in player.storage.placements.filter(location_type="party", slot=slot):
            core.PlacementService(player.storage).to_box(placement.pokemon)
        entry = core.resolve_dex_entry(core.POKEDEX, species)
        mon = core.create_owned_pokemon(
            species,
            player.trainer,
            level,
            nature="Hardy",
            ability=entry.raw["abilities"]["0"],
            ivs=[0] * 6,
            evs=[0] * 6,
            active_move_names=moves,
        )
        core.PlacementService(player.storage).to_party(mon, slot=slot)
        self.mons.append(mon)
        return mon

    def failed_purchase(self, item, reason):
        """The same ordinary menu rejects funds/stock without a partial debit."""
        before, start = self.state(), len(self.player.messages)
        self.command("store")
        self.reply("1")
        self.reply(item + " 1")
        self.reply("back")
        self.reply("q")
        self.assertEqual(self.state(), before)
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": reason,
                "commands": ["+store", "1", item + " 1", "back", "q"],
                "before": before,
                "after": self.state(),
                "messages": list(map(str, self.player.messages[start:])),
            }
        )

    def flow(
        self,
        item,
        native,
        move="Tackle",
        *,
        suppressed=False,
        weather=None,
        target_species="Eevee",
        target_ability=None,
        target_status=None,
        target_move="Growl",
        target_level=100,
        battle_format="single",
        seed=12,
        inspect=None,
        ally_status=None,
        foe_target="A1",
        reentry=False,
    ):
        """Buy/equip, issue +mega/+attack, observe effect, rebuild/end/return."""
        if self.session:
            self.session.end()
            self.session = None
        # Each control has fresh native setup and an empty initial item bag.
        quantity = self.player.trainer.get_item_quantity(item)
        if quantity:
            self.player.trainer.remove_item(item, quantity)
        self.mon = self.fixture_native(native, [move, "Growl"], 3)
        self.foe = self.fixture_native(
            target_species, [target_move, "Protect"], 1, side=1, level=target_level
        )
        if target_ability:
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(ability=target_ability)
            core.OwnedPokemon.flush_cached_instance(self.foe)
        if target_status:
            core.OwnedPokemon.objects.filter(pk=self.foe.pk).update(status=target_status)
            core.OwnedPokemon.flush_cached_instance(self.foe)
        from pokemon.services.item_counter import ItemCounter

        offers = ItemCounter("world/mega_stone_counter.json").recipe()["offers"]
        self.assertIn({"item": item, "price": 10000, "quantity": 1}, offers)
        if not suppressed:
            wallet = self.state()["wallet"]
            self.room.db.store_inventory = {item: {"price": 10000, "quantity": 1}}
            self.player.trainer.money = 9999
            self.player.trainer.save(update_fields=["money"])
            self.failed_purchase(item, "insufficient-funds-control")
            self.player.trainer.money = wallet
            self.player.trainer.save(update_fields=["money"])
        self.buy(item, price=10000, quantity=1)
        if not suppressed:
            self.failed_purchase(item, "empty-stock-control")
        self.record("hold", "3=" + item)
        if ally_status:
            ally_row = self.player.storage.get_party_slots()[3]
            core.OwnedPokemon.objects.filter(pk=ally_row.pk).update(status=ally_status)
            core.OwnedPokemon.flush_cached_instance(ally_row)
        self.launch(battle_format)
        battle = self.session.battle
        battle.rng = random.Random(seed)
        holder, target = (part.active[0] for part in battle.participants)
        holder.ability_suppressed = suppressed
        battle.clearWeather()
        if weather:
            battle.setWeather(weather, holder)
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        # Runtime nickname/native/Transform shortcuts cannot bypass fresh SQL.
        for field, value in (
            ("transformed", True),
            ("species", "Eevee"),
            ("native_origin", dict(holder.native_origin, species="Eevee")),
            ("item", "Venusaurite"),
        ):
            old = getattr(holder, field, None)
            setattr(holder, field, value)
            self.record("mega", "A1")
            self.assertFalse(battle.mega_pending)
            self.assertFalse(battle.mega_used)
            setattr(holder, field, old)
        self.record("mega", "A1")
        self.assertEqual(set(battle.mega_pending), {"A"}, self.player.messages[-5:])
        before = self.observation()
        hp = target.hp
        holder_hp = holder.hp
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 " + move + " B1")
            self.record("attack", "B1 " + target_move + " " + foe_target, side=1)
            if battle_format == "double":
                self.record("attack", "A2 Growl B1")
                self.record("attack", "B2 Growl A1", side=1)
        start = len(self.player.messages)
        self.session.execute_persistent_turn()
        logs = list(map(str, self.player.messages[start:]))
        self.assertTrue(holder.mega_evolved)
        self.assertEqual(battle.mega_used, {"A"})
        expected = MegaEvolution.pairs[normalize_name(item)][1]
        self.assertEqual(holder.species, expected)
        from types import SimpleNamespace
        from pokemon.helpers.pokemon_helpers import get_stats

        calculated = get_stats(
            SimpleNamespace(
                species=expected,
                level=holder.level,
                ivs=holder.ivs,
                evs=holder.evs,
                nature=holder.nature,
                hyper_training=holder.hyper_training,
            )
        )
        self.assertEqual({key: getattr(holder.base_stats, key) for key in calculated}, calculated)
        self.assertEqual(
            list(holder.types), core.resolve_dex_entry(core.POKEDEX, expected).raw["types"]
        )
        result = {
            "damage": hp - target.hp,
            "holder_hp_loss": holder_hp - holder.hp,
            "types": list(holder.types),
            "ability": EffectContext.key(holder.ability),
            "boosts": deepcopy(holder.boosts),
            "target_boosts": deepcopy(target.boosts),
            "weather": str(battle.field.weather or ""),
            "status": holder.status,
            "target_status": target.status,
            "logs": logs,
            "moves": holder.to_dict()["moves"],
            "effective_speed": EffectContext.speed(holder),
            "holder_max_hp": holder.max_hp,
            "ally": [
                dict(hp=mon.hp, status=mon.status, max_hp=mon.max_hp) for mon in holder.allies()
            ],
        }
        if inspect:
            inspect(self, holder, target, result)
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "resolved-pair-effect",
                "item": item,
                "control": "suppressed" if suppressed else "active",
                "setup": "Separate fresh native/move/opponent/optional-weather SQL fixture; ordinary source and inputs follow.",
                "before": before,
                "after": self.observation(),
                "effect": result,
            }
        )
        self.rebuild()
        rebuilt = self.session.battle.participants[0].active[0]
        self.assertEqual((rebuilt.species, list(rebuilt.types)), (expected, result["types"]))
        self.assertEqual(EffectContext.key(rebuilt.ability), result["ability"])
        self.assertEqual(self.session.battle.mega_used, {"A"})
        if reentry:
            for destination in (4, 3):
                with patch.object(self.session, "maybe_run_turn"):
                    self.record("switch", "A1 " + str(destination))
                    self.record("attack", "B1 Protect B1", side=1)
                self.session.execute_persistent_turn()
                self.rebuild()
            entered = self.session.battle.participants[0].active[0]
            self.assertEqual(
                (entered.species, EffectContext.key(entered.ability)), (expected, result["ability"])
            )
            self.assertEqual(self.session.battle.mega_used, {"A"})
        self.session.end()
        self.session = None
        row = core.OwnedPokemon.objects.filter(pk=self.mon.pk).values().get()
        self.assertEqual((row["species"], row["held_item"]), (native, item))
        self.assertEqual(self.player.trainer.get_item_quantity(item), 0)
        self.record("hold", "3=")
        self.assertEqual(self.player.trainer.get_item_quantity(item), 1)
        return result

    def power(self, item):
        """The same current Mega stats produce greater damage with the trait active."""
        native, move = POWER_PAIRS[item]
        weather = (
            "sandstorm"
            if item in {"Garchompite", "Steelixite"}
            else "sunnyday" if item == "Houndoominite" else None
        )
        # Water target resists Fire but is immune to Ground only when explicitly
        # configured; comparisons retain the identical opponent and RNG seed.
        a = self.flow(item, native, move, weather=weather)
        b = self.flow(item, native, move, suppressed=True, weather=weather)
        self.assertGreater(a["damage"], b["damage"])
        self.assertGreater(b["damage"], 0)
        if item == "Houndoominite":
            self.assertEqual(a["holder_hp_loss"], a["holder_max_hp"] // 8)
            self.assertEqual(b["holder_hp_loss"], 0)

    def conversion(self, item):
        """A real Normal attack converts and gains its current STAB/power effects."""
        native, converted = CONVERSION_PAIRS[item]
        a = self.flow(item, native, reentry=True)
        b = self.flow(item, native, suppressed=True, reentry=True)
        self.assertGreater(a["damage"], b["damage"])
        self.assertIn(converted, a["types"])

    def weather(self, item, native, expected):
        """Entry effect starts exactly on activation; suppression prevents it."""
        a = self.flow(item, native, reentry=True)
        b = self.flow(item, native, suppressed=True, reentry=True)
        self.assertEqual(a["weather"], expected)
        self.assertEqual(b["weather"], "")

    def test_abomasite_weather(self):
        """Mega entry starts current PF2 snow rather than legacy hail."""
        self.weather("Abomasite", "Abomasnow", "snow")

    def test_charizardite_y_weather(self):
        """A real Drought Start receives the current battle owner context."""
        self.weather("Charizardite Y", "Charizard", "sunnyday")

    def test_tyranitarite_weather(self):
        """Sand Stream starts sand only when its Mega ability is effective."""
        self.weather("Tyranitarite", "Tyranitar", "sandstorm")

    def test_manectite_intimidate(self):
        """The opponent actually loses one Attack stage on Mega activation."""
        a = self.flow("Manectite", "Manectric")
        b = self.flow("Manectite", "Manectric", suppressed=True)
        self.assertEqual((a["target_boosts"]["attack"], b["target_boosts"]["attack"]), (-1, 0))

    def test_blazikenite_speed_boost(self):
        """The new trait receives its first eligible end-of-turn speed increase."""
        a = self.flow("Blazikenite", "Blaziken")
        b = self.flow("Blazikenite", "Blaziken", suppressed=True)
        self.assertEqual((a["boosts"]["speed"], b["boosts"]["speed"]), (1, 0))

    def test_swampertite_rain_speed(self):
        """Swift Swim changes the same active Mega's effective order speed only in rain."""
        a = self.flow("Swampertite", "Swampert", weather="raindance")
        b = self.flow("Swampertite", "Swampert", weather="raindance", suppressed=True)
        c = self.flow("Swampertite", "Swampert")
        self.assertEqual(a["effective_speed"], 2 * b["effective_speed"])
        self.assertEqual(c["effective_speed"], b["effective_speed"])

    def test_heracronite_skill_link(self):
        """Pin Missile gets five actual hits with one ordinary source PP charge."""
        a = self.flow("Heracronite", "Heracross", "Pin Missile")
        b = self.flow("Heracronite", "Heracross", "Pin Missile", suppressed=True)
        self.assertTrue(any("hit 5 times" in line for line in a["logs"]), a["logs"])
        self.assertGreater(a["damage"], 0)
        self.assertEqual(a["moves"][0]["pp"], b["moves"][0]["pp"])

    def test_lopunnite_scrappy(self):
        """A real Normal attack hits a Ghost only with effective Scrappy."""
        a = self.flow("Lopunnite", "Lopunny", target_species="Gastly", target_move="Spite")
        b = self.flow(
            "Lopunnite", "Lopunny", suppressed=True, target_species="Gastly", target_move="Spite"
        )
        self.assertGreater(a["damage"], 0)
        self.assertEqual(b["damage"], 0)

    def bounce(self, item):
        """Reflect one actual opposing Growl without recursive rebounding."""
        native = {"Absolite": "Absol", "Diancite": "Diancie", "Sablenite": "Sableye"}[item]
        a = self.flow(item, native)
        b = self.flow(item, native, suppressed=True)
        self.assertEqual((a["boosts"]["attack"], a["target_boosts"]["attack"]), (0, -1))
        self.assertEqual((b["boosts"]["attack"], b["target_boosts"]["attack"]), (-1, 0))
        self.assertEqual(sum(line.count("reflected Growl") for line in a["logs"]), 1)

    def test_alakazite_trace(self):
        """Trace initializes a real copied Huge Power effect and keeps it on rebuild."""
        options = dict(
            target_species="Azumarill",
            target_move="Splash",
            target_ability="Huge Power",
            reentry=True,
        )
        a = self.flow("Alakazite", "Alakazam", **options)
        b = self.flow("Alakazite", "Alakazam", suppressed=True, **options)
        self.assertEqual((a["ability"], b["ability"]), ("hugepower", "trace"))
        self.assertGreater(a["damage"], b["damage"])

    def test_banettite_prankster_dark_immunity(self):
        """Only the boosted status is prevented by the opposing Dark target."""
        options = dict(target_species="Umbreon", target_move="Growl")
        a = self.flow("Banettite", "Banette", "Will-O-Wisp", **options)
        b = self.flow("Banettite", "Banette", "Will-O-Wisp", suppressed=True, **options)
        self.assertFalse(a["target_status"])
        self.assertEqual(b["target_status"], "brn")

    def test_gengarite_shadow_tag_switch(self):
        """The ordinary opponent switch rejects only while the active owner traps it."""

        def probe(test, holder, target, result):
            """Compare the actual PlayerChoices declaration, not a raw trapped flag."""
            old = deepcopy(test.session.state.declare)
            test.record("switch", "2", side=1)
            result["switch_queued"] = test.session.state.declare != old

        a = self.flow("Gengarite", "Gengar", inspect=probe)
        b = self.flow("Gengarite", "Gengar", suppressed=True, inspect=probe)
        self.assertEqual((a["switch_queued"], b["switch_queued"]), (False, True))

    def defensive(self, item):
        """Actual incoming hits observe Filter, Levitate and critical immunity."""
        native, foe, source = {
            "Aggronite": ("Aggron", "Machop", "Brick Break"),
            "Latiasite": ("Latias", "Diglett", "Mud-Slap"),
            "Latiosite": ("Latios", "Diglett", "Mud-Slap"),
            "Slowbronite": ("Slowbro", "Glalie", "Frost Breath"),
        }[item]
        options = dict(target_species=foe, target_move=source, target_level=50)
        a = self.flow(item, native, "Growl", **options)
        b = self.flow(item, native, "Growl", suppressed=True, **options)
        self.assertGreater(b["holder_hp_loss"], a["holder_hp_loss"])
        if item in {"Latiasite", "Latiosite"}:
            self.assertEqual(a["holder_hp_loss"], 0)

    def mold_breaker(self, item):
        """A real immunity is bypassed by the active Mega attack only."""
        if item == "Ampharosite":
            options = dict(
                target_species="Lanturn", target_ability="Volt Absorb", target_move="Growl"
            )
            native, move = "Ampharos", "Thunderbolt"
        else:
            options = dict(target_species="Gastly", target_move="Spite")
            native, move = "Gyarados", "Earthquake"
        a = self.flow(item, native, move, **options)
        b = self.flow(item, native, move, suppressed=True, **options)
        self.assertGreater(a["damage"], 0)
        self.assertEqual(b["damage"], 0)

    def test_sceptilite_doubles_redirect(self):
        """An opposing Electric attack aimed at A2 redirects to immune Mega A1."""
        options = dict(
            target_species="Pikachu",
            target_move="Thunder Shock",
            target_level=50,
            battle_format="double",
            foe_target="A2",
        )
        a = self.flow("Sceptilite", "Sceptile", **options)
        b = self.flow("Sceptilite", "Sceptile", suppressed=True, **options)
        self.assertEqual((a["boosts"]["special_attack"], b["boosts"]["special_attack"]), (1, 0))
        self.assertEqual(a["ally"][0]["hp"], a["ally"][0]["max_hp"])
        self.assertLess(b["ally"][0]["hp"], b["ally"][0]["max_hp"])

    def test_galladite_inner_focus(self):
        """Fake Out cannot flinch the new ability; its suppressed control loses its move."""
        options = dict(target_species="Kangaskhan", target_move="Fake Out", target_level=50)
        a = self.flow("Galladite", "Gallade", **options)
        b = self.flow("Galladite", "Gallade", suppressed=True, **options)
        self.assertEqual((a["moves"][0]["pp"], b["moves"][0]["pp"]), (34, 35))

    def test_mewtwonite_x_steadfast(self):
        """A real flinch raises Speed exactly once without making the prevented move."""
        options = dict(target_species="Kangaskhan", target_move="Fake Out", target_level=50)
        a = self.flow("Mewtwonite X", "Mewtwo", **options)
        b = self.flow("Mewtwonite X", "Mewtwo", suppressed=True, **options)
        self.assertEqual((a["boosts"]["speed"], b["boosts"]["speed"]), (1, 0))
        self.assertEqual((a["moves"][0]["pp"], b["moves"][0]["pp"]), (35, 35))

    def test_mewtwonite_y_insomnia(self):
        """A real Spore cannot sleep an effective new Insomnia holder."""
        options = dict(target_species="Breloom", target_move="Spore", target_level=50)
        a = self.flow("Mewtwonite Y", "Mewtwo", "Growl", **options)
        b = self.flow("Mewtwonite Y", "Mewtwo", "Growl", suppressed=True, **options)
        self.assertFalse(a["status"])
        self.assertEqual(b["status"], "slp")

    def test_pidgeotite_no_guard(self):
        """The actual Hurricane hit avoids the ordinary accuracy roll."""
        a = self.flow("Pidgeotite", "Pidgeot", "Hurricane", seed=5)
        b = self.flow("Pidgeotite", "Pidgeot", "Hurricane", seed=5, suppressed=True)
        self.assertGreater(a["damage"], 0)
        self.assertEqual(b["damage"], 0)

    def test_audinite_healer(self):
        """A tagged living active ally is cured by a deterministic private battle roll."""
        options = dict(battle_format="double", ally_status="par", seed=2)
        a = self.flow("Audinite", "Audino", **options)
        b = self.flow("Audinite", "Audino", suppressed=True, **options)
        self.assertFalse(a["ally"][0]["status"])
        self.assertEqual(b["ally"][0]["status"], "par")

    def test_kangaskhanite_parental_bond(self):
        """The player attack adds one quarter-strength hit with one source PP debit."""
        a = self.flow("Kangaskhanite", "Kangaskhan")
        b = self.flow("Kangaskhanite", "Kangaskhan", suppressed=True)
        self.assertGreater(a["damage"], b["damage"])
        self.assertLess(a["damage"], b["damage"] * 1.5)
        self.assertEqual((a["moves"][0]["pp"], b["moves"][0]["pp"]), (34, 34))

    def test_weather_start_failure_rolls_back_and_retry_starts_once(self):
        """An unexpected new ability Start cannot commit form/weather/PP/use."""
        from pokemon.dex.functions.abilities_funcs import Drought

        original = Drought.onStart

        def fail(handler, source=None, battle=None):
            """Fault after a real Mega weather change, leaving native entry alone."""
            result = original(handler, source, battle)
            if source and str(source.species) == "Charizard-Mega-Y":
                raise RuntimeError("Mega weather startup fixture")
            return result

        with patch.object(Drought, "onStart", fail):
            with self.assertRaisesRegex(RuntimeError, "Mega weather startup fixture"):
                self.flow("Charizardite Y", "Charizard")
        holder = self.session.battle.participants[0].active[0]
        self.assertEqual(holder.species, "Charizard")
        self.assertFalse(self.session.battle.field.weather)
        self.assertFalse(self.session.battle.mega_used)
        self.assertEqual(holder.to_dict()["moves"][0]["pp"], 35)
        before = self.observation()
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.field.weather, "sunnyday")
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertEqual(
            self.session.battle.participants[0].active[0].to_dict()["moves"][0]["pp"], 34
        )
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "weather-start-retry",
                "before": before,
                "after": self.observation(),
            }
        )

    def test_parental_second_hit_failure_rewinds_first_hit_and_retry(self):
        """A failed second hit restores the first hit, source PP, RNG and side use."""
        from pokemon.battle.engine import Battle

        original = Battle._do_move

        def fail(battle, user, target, move):
            """The first hit is real; fail before resolving the second."""
            if getattr(move, "parental_bond_hit", None) == 2:
                raise RuntimeError("Parental second hit fixture")
            return original(battle, user, target, move)

        with patch.object(Battle, "_do_move", fail):
            with self.assertRaisesRegex(RuntimeError, "Parental second hit fixture"):
                self.flow("Kangaskhanite", "Kangaskhan")
        battle = self.session.battle
        holder, target = (p.active[0] for p in battle.participants)
        self.assertEqual(holder.species, "Kangaskhan")
        self.assertEqual(target.hp, target.max_hp)
        self.assertEqual(holder.to_dict()["moves"][0]["pp"], 35)
        self.assertFalse(battle.mega_used)
        before = self.observation()
        self.session.execute_persistent_turn()
        self.assertEqual(self.session.battle.mega_used, {"A"})
        self.assertLess(self.session.battle.participants[1].active[0].hp, target.max_hp)
        self.assertEqual(
            self.session.battle.participants[0].active[0].to_dict()["moves"][0]["pp"], 34
        )
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "parental-hit-retry",
                "before": before,
                "after": self.observation(),
            }
        )

    def test_opposing_weather_megas_use_pre_form_speed_and_independent_budgets(self):
        """The slower native holder's later Mega entry replaces the faster one's sun."""
        self.mon = self.fixture_native("Charizard", ["Tackle", "Growl"], 3)
        self.foe = self.fixture_native("Tyranitar", ["Tackle", "Growl"], 1, side=1)
        self.buy("Charizardite Y", price=10000, quantity=1)
        self.record("hold", "3=Charizardite Y")
        # Opponent source is separate fixture setup; its complete purchase flow
        # is independently accepted in test_tyranitarite_weather.
        self.players[1].trainer.add_item("Tyranitarite")
        self.record("hold", "1=Tyranitarite", side=1)
        self.launch()
        self.record("mega", "A1")
        self.record("mega", "B1", side=1)
        before, start = self.observation(), len(self.player.messages)
        with patch.object(self.session, "maybe_run_turn"):
            self.record("attack", "A1 Tackle B1")
            self.record("attack", "B1 Tackle A1", side=1)
        self.session.execute_persistent_turn()
        battle = self.session.battle
        self.assertEqual(battle.mega_used, {"A", "B"})
        self.assertEqual(battle.field.weather, "sandstorm")
        lines = [str(m) for m in self.player.messages[start:] if "Mega Evolved" in str(m)]
        text = "\n".join(lines)
        self.assertLess(text.index("Charizard-Mega-Y"), text.index("Tyranitar-Mega"))
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "paired-weather-order",
                "before": before,
                "after": self.observation(),
                "messages": lines,
            }
        )

    def test_prior_venusaurite_only_counter_requires_review_without_adding_stock(self):
        """Extending the recipe never silently expands a previously installed source."""
        from pokemon.services.item_counter import ItemCounter
        from evennia.utils.create import create_object

        counter = ItemCounter("world/mega_stone_counter.json")
        recipe = counter.recipe()
        old_recipe = dict(
            recipe, offers=[offer for offer in recipe["offers"] if offer["item"] == "Venusaurite"]
        )
        hub = create_object(
            "typeclasses.rooms.FusionRoom", key="private legacy Mega hub", nohome=True
        )
        with patch.object(ItemCounter, "recipe", return_value=old_recipe):
            room = counter.install(hub)
        receipt = hub.attributes.get("counter_mega-stone-counter-v1")
        self.installed_objects.extend(
            [hub.pk, room.pk, receipt["entrance"], receipt["return_exit"]]
        )
        before = deepcopy(room.attributes.get("store_inventory"))
        with self.assertRaisesRegex(ValueError, "policy/stock drift"):
            counter.install(hub)
        room.attributes.reset_cache()
        self.assertEqual(room.attributes.get("store_inventory"), before)
        self.assertEqual(set(before), {"Venusaurite"})
        core.EVIDENCE.append(
            {
                "case": self._testMethodName,
                "event": "legacy-source-drift-guard",
                "before": dict(before),
                "after": dict(room.attributes.get("store_inventory")),
                "live_operations": False,
            }
        )


def add_case(label, method, value):
    """Keep independent per-pair failures and named command receipts."""

    def test(self):
        """Exercise the named pair and its meaningful effect control."""
        getattr(self, method)(value)

    setattr(MegaStoneCases, "test_" + label, test)


for name in POWER_PAIRS:
    add_case("power_" + name.lower().replace(" ", "_"), "power", name)
for name in CONVERSION_PAIRS:
    add_case("conversion_" + name.lower(), "conversion", name)
for name in ("Absolite", "Diancite", "Sablenite"):
    add_case("reflection_" + name.lower(), "bounce", name)
for name in ("Aggronite", "Latiasite", "Latiosite", "Slowbronite"):
    add_case("defense_" + name.lower(), "defensive", name)
for name in ("Ampharosite", "Gyaradosite"):
    add_case("bypass_" + name.lower(), "mold_breaker", name)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        core.load_runtime()
        from pokemon.battle.mega_evolution import MegaEvolution
        from pokemon.battle.effect_context import EffectContext
        from pokemon.names import normalize_name

        try:
            result = unittest.TextTestRunner(verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(MegaStoneCases)
            )
        finally:
            if os.environ.get("PF2_MEGA_EVIDENCE"):
                Path(os.environ["PF2_MEGA_EVIDENCE"]).write_text(
                    json.dumps(core.EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8"
                )
        raise SystemExit(not result.wasSuccessful())
