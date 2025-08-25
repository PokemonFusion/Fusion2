"""Multi-battle integration tests using lightweight stubs.

These tests construct a minimal battle environment with stubbed modules to
ensure the engine handles multi-participant battles correctly.
"""

import importlib.util
import os
import random
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Load entity dataclasses
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

# Minimal dex stub
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

# Minimal data stub
data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# Load damage module
damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
damage_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = damage_mod
d_spec.loader.exec_module(damage_mod)
pkg_battle.damage_calc = damage_mod.damage_calc

# Load battledata and engine
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon

eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
engine = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = engine
eng_spec.loader.exec_module(engine)

BattleMove = engine.BattleMove
BattleParticipant = engine.BattleParticipant
Battle = engine.Battle
Action = engine.Action
ActionType = engine.ActionType
BattleType = engine.BattleType


def setup_participants(count):
        """Create ``count`` battle participants with identical base stats."""

        base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
        participants = []
        for idx in range(1, count + 1):
                poke = Pokemon(f"P{idx}mon")
                poke.base_stats = base
                poke.num = idx
                poke.types = ["Normal"]
                part = BattleParticipant(f"P{idx}", [poke], is_ai=False)
                part.active = [poke]
                participants.append(part)
        return participants


def test_three_and_four_way_battles():
        """Ensure all participants take damage in three- and four-way battles."""

        try:
                for count in (3, 4):
                        parts = setup_participants(count)
                        move = BattleMove("Tackle", power=40, accuracy=100)
                        for idx, part in enumerate(parts):
                                target = parts[(idx + 1) % count]
                                part.pending_action = Action(
                                        part,
                                        ActionType.MOVE,
                                        target,
                                        move,
                                        move.priority,
                                        pokemon=part.active[0],
                                )

                        battle = Battle(BattleType.WILD, parts)
                        random.seed(0)
                        battle.run_turn()

                        for part in parts:
                                assert part.active[0].hp < 100
        finally:
                for name in (
                        "pokemon.dex.entities",
                        "pokemon.dex",
                        "pokemon.data",
                        "pokemon.battle.damage",
                        "pokemon.battle.battledata",
                        "pokemon.battle.engine",
                        "pokemon.battle",
                ):
                        sys.modules.pop(name, None)
