"""Verify five existing incense boosters through real hold and battle commands."""

import json
import math
import os
from pathlib import Path
import random
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from isolated_postgres import IsolatedPostgres
from ui_cases import PlayerView as SessionTransport

EVIDENCE = []
PROFILES = {"Odd Incense": ("Psychic", "Psychic"), "Rock Incense": ("Power Gem", "Rock"),
            "Rose Incense": ("Energy Ball", "Grass"), "Sea Incense": ("Surf", "Water"),
            "Wave Incense": ("Surf", "Water")}
SEED = 771
DEBUG = re.compile(r"\[DEBUG\] lvl=(\d+) pow=(\d+) atk=(\d+) def=(\d+) "
                   r"stab=([\d.]+) eff=([\d.]+) roll=([\d.]+) crit=(True|False) dmg=(\d+)")


class IncensePlayer(SessionTransport):
    """Capture transport while retaining production owned/inventory lookups."""

    def get_pokemon_by_id(self, identifier):
        """Use the ordinary owner-validated full-ID lookup."""
        return User.get_pokemon_by_id(self, identifier)

    def get_active_pokemon_by_slot(self, slot):
        """Keep canonical gapped party slots."""
        return User.get_active_pokemon_by_slot(self, slot)

    def has_item(self, item, quantity=1):
        """Check actual bag stock."""
        return User.has_item(self, item, quantity)

    def remove_item(self, item, quantity=1):
        """Use the production bag writer."""
        return User.remove_item(self, item, quantity)


class IncenseCases(unittest.TestCase):
    """Pair ordinary equipped/unheld actions with durable state and controls."""

    def setUp(self):
        """Create only tagged normal players in the guarded disposable schema."""
        room = ObjectDB.objects.create(db_key="incense-771-room-" + uuid4().hex)
        self.room = SimpleNamespace(id=room.pk, pk=room.pk, key=room.key, db=room.db,
                                    ndb=room.ndb, attributes=room.attributes, contents=[])
        self.players, self.owned, self.session = [], [], None
        for _ in range(2):
            character = ObjectDB.objects.create(db_key="incense-771-player-" + uuid4().hex,
                                                db_typeclass_path="pokemon.user.User")
            player = IncensePlayer(character, character.trainer, character.storage)
            player.pk, player.location = character.pk, self.room
            self.players.append(player)
        self.player = self.players[0]
        self.room.contents = self.players
        self.search = patch("pokemon.battle.battleinstance.search_object",
                            lambda query: [p for p in self.players if str(p.id) == str(query).lstrip("#")])
        self.search.start()

    def tearDown(self):
        """End only this fixture's session and release its captured transport."""
        self.stop()
        self.search.stop()

    def prepare(self, item, *, species="Mew", ability="Synchronize", foe="Mew", stock=True,
                holder_moves=None, foe_ability="Synchronize", opponent_moves=None):
        """Create legal native holders/moves and separate explicit bag setup."""
        self.item, self.matching = item, PROFILES[item][0]
        holder_moves = holder_moves or ([self.matching, "Swift", "Magic Room", "Safeguard"]
                                        if species == "Mew" else ["Psychic", "Swift"])
        opponent_moves = opponent_moves or (["Safeguard", "Embargo", "Knock Off", "Corrosive Gas"]
                                            if foe == "Mew" else ["Safeguard"])
        self.owned = [
            create_owned_pokemon(species, self.player.trainer, 50, nature="Hardy", ability=ability,
                ivs=[0] * 6, evs=[0] * 6,
                active_move_names=holder_moves),
            create_owned_pokemon(foe, self.players[1].trainer, 50, nature="Calm", ability=foe_ability,
                ivs=[31] * 6, evs=[252, 0, 0, 0, 252, 0],
                active_move_names=opponent_moves),
        ]
        for player, mon in zip(self.players, self.owned):
            PlacementService(player.storage).to_party(mon, slot=3)
        if stock:
            for name in PROFILES:
                self.player.trainer.add_item(name, 2)

    def command(self, kind, args, side=0):
        """Execute the shipped parser/command, choices, queue and turn routes."""
        module, cls = COMMANDS[kind]
        command = cls()
        command.caller, command.args, command.cmdstring = self.players[side], args, "+" + kind
        command.parse()
        if hasattr(module, "get_system"):
            with patch.object(module, "get_system", return_value=SimpleNamespace(battle_manager=None)):
                command.func()
        else:
            command.func()
        if self.session:
            self.assertFalse(self.session.turn_state.get("error"), self.session.turn_state)
        return self.players[side].messages[-1]

    def snapshot(self):
        """Retain independent SQL rows, bags and actual battle snapshots."""
        return {
            "owned": list(OwnedPokemon.objects.filter(pk__in=[m.pk for m in self.owned]).order_by("pk").values()),
            "placements": list(PokemonPlacement.objects.filter(pokemon__in=self.owned).order_by("pk").values()),
            "moves": list(ActiveMoveslot.objects.filter(pokemon__in=self.owned).order_by("pokemon_id", "slot").values()),
            "bags": [list(p.trainer.list_inventory().values("item_name", "quantity")) for p in self.players],
            "inventory_cache": [dict(p.db.inventory or {}) for p in self.players],
            "runtime": [[m.to_dict() for m in part.pokemons] for part in self.session.battle.participants]
                       if self.session else None,
        }

    def hold(self, item):
        """Equip/remove using ordinary +hold, preserving command/SQL receipts."""
        before, start = self.snapshot(), len(self.player.messages)
        self.command("hold", "3=" + item)
        self.assertEqual(self.saved_item(), item)
        EVIDENCE.append({"label": "ordinary-hold", "item": self.item, "command": "+hold 3=" + item,
                         "before": before, "after": self.snapshot(), "messages": self.player.messages[start:]})

    def saved_item(self):
        """Bypass Evennia model identity caching for held-state assertions."""
        return OwnedPokemon.objects.filter(pk=self.owned[0].pk).values_list("held_item", flat=True).get()

    def stop(self):
        """Close a real PvP session before another ordinary field transition."""
        if self.session:
            self.session.end()
            self.session = None

    def start(self, item):
        """Prepare fresh stats/HP/PP, equip normally and start the PvP lifecycle."""
        self.stop()
        for index, mon in enumerate(self.owned):
            OwnedPokemon.flush_cached_instance(mon)
            self.owned[index] = OwnedPokemon.objects.get(pk=mon.pk)
            self.owned[index].heal()
        self.hold(item)
        self.session = BattleSession(self.player, self.players[1], rng=random.Random(SEED))
        self.session.start_pvp()
        self.session.battle.debug = True  # Existing diagnostics only; no effect substitution.
        self.assertEqual(self.session.battle.participants[0].active[0].model_id, "owned:" + str(self.owned[0].pk))
        if item:
            actual = self.session.battle.participants[0].active[0].item
            self.assertIsInstance(actual, Item)
            self.assertEqual(actual.raw["onBasePower"], resolve_dex_entry(ITEMDEX, item).raw["onBasePower"])

    def turn(self, ours, theirs="Safeguard", *, rebuild=False):
        """Declare both ordinary actions, optionally restore while one is queued."""
        before, starts = self.snapshot(), [len(p.messages) for p in self.players]
        battle = self.session.battle
        turn = battle.turn_count
        random.seed(SEED)
        battle.rng = random.Random(SEED)
        self.command("attack", "A1 " + ours)
        self.assertEqual(battle.turn_count, turn)
        if rebuild:
            self.rebuild()
            self.rebuild()
            self.session.battle.debug = True
            self.session.battle.rng = random.Random(SEED)
        self.command("attack", "B1 " + theirs, 1)
        self.assertEqual(self.session.battle.turn_count, turn + 1)
        messages = [p.messages[start:] for p, start in zip(self.players, starts)]
        traces = [match.groups() for message in messages[0] for match in DEBUG.finditer(str(message))]
        record = {"label": "ordinary-battle-turn", "item": self.item,
                  "commands": ["+attack A1 " + ours, "+attack B1 " + theirs],
                  "seed": SEED, "queued_rebuilds": 2 if rebuild else 0,
                  "before": before, "after": self.snapshot(), "messages": messages, "damage_traces": traces}
        EVIDENCE.append(record)
        return record

    def rebuild(self):
        """Discard live references and reconstruct production durable battle state."""
        self.session._sync_active_battle_state()
        self.session._persist_turn_state()
        battle_handler.unregister(self.session)
        for p in self.players:
            p.ndb.battle_instance = None
        self.room.ndb.battle_instances = {}
        self.session = BattleSession.restore(self.room, self.session.battle_id)
        self.assertIsNotNone(self.session)
        self.session.battle.debug = True

    def hit(self, move, *, rebuild=False):
        """Check real HP/PP against the emitted damage inputs and integer formula."""
        attacker, defender = [part.active[0] for part in self.session.battle.participants]
        hp = defender.hp
        slot = next(slot for slot in self.owned[0].activemoveslot_set.all()
                    if normalize_name(slot.move.name) == normalize_name(move))
        pp = slot.current_pp
        record = self.turn(move, rebuild=rebuild)
        self.assertEqual(len(record["damage_traces"]), 1, record["messages"])
        trace = record["damage_traces"][0]
        level, power, attack, defense = map(int, trace[:4])
        stab, effectiveness, roll = map(float, trace[4:7])
        self.assertEqual(trace[7], "False", "Seeded fixture must avoid critical amplification")
        # Independent arithmetic, not a direct item callback or damage-helper call.
        base = math.floor(math.floor(math.floor(2 * level / 5 + 2) * power * attack / defense) / 50) + 2
        damage = max(1, math.floor(math.floor(math.floor(base * roll) * stab) * effectiveness))
        self.assertEqual(int(trace[8]), damage)
        defender = self.session.battle.participants[1].active[0]
        self.assertEqual(hp - defender.hp, damage)
        self.assertEqual(ActiveMoveslot.objects.get(pk=slot.pk).current_pp, pp - 1)
        self.assertEqual(record["after"]["bags"], record["before"]["bags"])
        self.assertEqual(record["after"]["inventory_cache"], record["before"]["inventory_cache"])
        return {"power": power, "damage": damage, "controls": (level, attack, defense, stab, effectiveness, roll, trace[7])}

    def measure(self, held, move, *, mode=None, queued=False):
        """Compare useful moves under explicit native/legal battle preconditions."""
        self.start(held)
        if mode == "magic":
            self.turn("Magic Room")
            self.assertIn("magicroom", self.session.battle.field.pseudo_weather)
        elif mode == "embargo":
            self.turn("Safeguard", "Embargo")
            self.assertIn("embargo", self.session.battle.participants[0].active[0].volatiles)
        elif mode == "knockoff":
            self.turn("Safeguard", "Knock Off")
            self.assertFalse(self.session.battle.participants[0].active[0].item)
            self.assertEqual(self.saved_item(), "")
        elif mode == "sand":
            self.turn("Sandstorm")
            self.assertEqual(self.session.battle.field.weather, "sandstorm")
        if mode:
            self.rebuild()
            self.rebuild()
            actual = self.session.battle.participants[0].active[0]
            if mode == "sand" and held:
                self.assertIsNotNone(EffectContext.item(actual))
            else:
                self.assertIsNone(EffectContext.item(actual))
            if mode != "knockoff":
                self.assertEqual(EffectContext.key(actual.item), normalize_name(held))
                self.assertEqual(self.saved_item(), held)
        return self.hit(move, rebuild=queued)

    def exercise(self, item, case):
        """Run one per-item normal-route acceptance facet and paired control."""
        self.prepare(item)
        move = self.matching
        power = resolve_dex_entry(MOVEDEX, move).power
        if case == "matching":
            self.assertIn(item, self.command("inventory", ""))
            self.assertIn(normalize_name(item), normalize_name(self.command("itemdex", item)))
            baseline = self.measure("", move)
            held = self.measure(item, move)
            self.assertEqual(held["controls"], baseline["controls"])
            self.assertEqual((baseline["power"], held["power"]), (power, int(power * 1.2)))
            self.assertGreater(held["damage"], baseline["damage"])
            self.assertEqual(self.hit(move)["power"], held["power"])
            self.assertEqual(self.saved_item(), item)
        elif case == "nonmatching":
            self.assertEqual(self.measure("", "Swift"), self.measure(item, "Swift"))
        elif case in {"magic", "embargo", "knockoff"}:
            baseline = self.measure("", move, mode=case)
            actual = self.measure(item, move, mode=case)
            self.assertEqual(actual, baseline)
            self.assertEqual(actual["power"], power)
            if case == "magic":
                self.turn("Magic Room")
                self.assertNotIn("magicroom", self.session.battle.field.pseudo_weather)
                self.assertEqual(self.hit(move)["power"], int(power * 1.2))
                self.assertEqual(self.saved_item(), item)
        elif case == "checkpoint":
            baseline = self.measure("", move)
            actual = self.measure(item, move, queued=True)
            self.assertEqual(actual["controls"], baseline["controls"])
            self.assertEqual(actual["power"], int(power * 1.2))
            self.assertEqual(self.saved_item(), item)
            self.assertEqual(EffectContext.key(self.session.battle.participants[0].active[0].item), normalize_name(item))
        elif case == "remove_replace":
            self.measure(item, move)
            self.stop()
            quantity = self.player.trainer.get_item_quantity(item)
            self.hold("")
            self.assertEqual(self.player.trainer.get_item_quantity(item), quantity + 1)
            self.assertEqual(self.measure("", move)["power"], power)
            self.measure(item, move)
            self.stop()
            replacement = "Rock Incense" if item == "Odd Incense" else "Odd Incense"
            quantity = self.player.trainer.get_item_quantity(item)
            self.hold(replacement)
            self.assertEqual(self.player.trainer.get_item_quantity(item), quantity + 1)
            self.assertEqual(self.measure(replacement, move)["power"], power)

    def test_native_klutz_blocks_odd_incense_without_losing_item(self):
        """A canonical Klutz Swoobat retains incense but gains no Psychic boost."""
        self.prepare("Odd Incense", species="Swoobat", ability="Klutz")
        self.assertEqual(self.measure("", "Psychic"), self.measure("Odd Incense", "Psychic"))
        self.assertIsNone(EffectContext.item(self.session.battle.participants[0].active[0]))
        self.assertEqual(self.saved_item(), "Odd Incense")

    def test_native_sand_force_does_not_skip_rock_incense_in_clear_weather(self):
        """A native no-op ability result still permits the ordinary item hook."""
        self.prepare("Rock Incense", species="Gigalith", ability="Sand Force", holder_moves=["Power Gem"])
        baseline = self.measure("", "Power Gem")
        held = self.measure("Rock Incense", "Power Gem")
        self.assertEqual(baseline["controls"], held["controls"])
        self.assertEqual((baseline["power"], held["power"]), (80, 96))
        self.assertGreater(held["damage"], baseline["damage"])

    def test_native_sand_force_and_rock_incense_compose_in_sandstorm(self):
        """Legal sand-immune native holders expose sequential ability/item power."""
        self.prepare("Rock Incense", species="Gigalith", ability="Sand Force",
                     holder_moves=["Power Gem", "Sandstorm"], foe="Tyranitar", foe_ability="Unnerve")
        baseline = self.measure("", "Power Gem", mode="sand")
        held = self.measure("Rock Incense", "Power Gem", mode="sand")
        self.assertEqual(baseline["controls"], held["controls"])
        self.assertEqual((baseline["power"], held["power"]), (104, 124))
        self.assertGreater(held["damage"], baseline["damage"])

    def test_immune_target_is_expected_failure_without_consumption(self):
        """Psychic cannot hit a native Dark target even with Odd Incense."""
        self.prepare("Odd Incense", foe="Umbreon")
        self.start("Odd Incense")
        foe = self.session.battle.participants[1].active[0]
        hp = foe.hp
        before = self.snapshot()
        record = self.turn("Psychic")
        self.assertEqual(foe.hp, hp)
        self.assertTrue(any("doesn't affect" in str(m) for m in record["messages"][0]), record["messages"])
        self.assertEqual(self.saved_item(), "Odd Incense")
        self.assertEqual(self.snapshot()["bags"], before["bags"])

    def test_missing_bag_stock_cannot_equip_any_incense(self):
        """Existing definitions do not grant an unowned held item."""
        self.prepare("Odd Incense", stock=False)
        for item in PROFILES:
            before = self.snapshot()
            self.command("hold", "3=" + item)
            self.assertEqual(self.snapshot(), before)


def add_case(item, case):
    """Give every item an individually counted ordinary-route test per facet."""
    def test(self):
        """Run this incense's matching/control/suppression/persistence route."""
        self.exercise(item, case)
    setattr(IncenseCases, "test_" + key(item) + "_" + case, test)


def key(value):
    """Name dynamic cases before loading game modules in the private schema."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


for incense in PROFILES:
    for facet in ("matching", "nonmatching", "magic", "embargo", "knockoff", "checkpoint", "remove_replace"):
        add_case(incense, facet)


if __name__ == "__main__":
    with IsolatedPostgres() as database:
        database.create_model_tables()
        import evennia
        from evennia.commands.command import Command
        from evennia.commands.cmdset import CmdSet
        with patch.object(evennia, "Command", Command), patch.object(evennia, "CmdSet", CmdSet):
            from commands.player import cmd_battle_attack, cmd_party, cmd_inventory, cmd_pokedex
        from evennia.objects.models import ObjectDB
        from pokemon.battle.battleinstance import BattleSession
        from pokemon.battle.effect_context import EffectContext
        from pokemon.battle.handler import battle_handler
        from pokemon.dex import ITEMDEX, MOVEDEX
        from pokemon.dex.entities import Item
        from pokemon.helpers.pokemon_helpers import create_owned_pokemon
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.models.storage import PokemonPlacement
        from pokemon.names import normalize_name, resolve_dex_entry
        from pokemon.services.placement import PlacementService
        from pokemon.user import User
        COMMANDS = {"attack": (cmd_battle_attack, cmd_battle_attack.CmdBattleAttack),
                    "hold": (cmd_party, cmd_party.CmdSetHoldItem),
                    "inventory": (cmd_inventory, cmd_inventory.CmdInventory),
                    "itemdex": (cmd_pokedex, cmd_pokedex.CmdItemdexSearch)}
        try:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IncenseCases))
        finally:
            if os.environ.get("PF2_INCENSE_EVIDENCE"):
                Path(os.environ["PF2_INCENSE_EVIDENCE"]).write_text(json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
        raise SystemExit(not result.wasSuccessful())
