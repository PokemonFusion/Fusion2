import os
import sys
import types
import importlib.util
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal pokemon.battle package stub
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

# Minimal pokemon.battle.utils stub for damage module
utils_stub = types.ModuleType("pokemon.battle.utils")

def get_modified_stat(pokemon, stat):
    return getattr(pokemon.base_stats, stat, 0)

utils_stub.get_modified_stat = get_modified_stat
sys.modules["pokemon.battle.utils"] = utils_stub

# Load damage module and expose damage_calc
damage_path = os.path.join(ROOT, "pokemon", "battle", "damage.py")
d_spec = importlib.util.spec_from_file_location("pokemon.battle.damage", damage_path)
d_mod = importlib.util.module_from_spec(d_spec)
sys.modules[d_spec.name] = d_mod
d_spec.loader.exec_module(d_mod)
pkg_battle.damage_calc = d_mod.damage_calc

# Load entity dataclasses for Stats
ent_path = os.path.join(ROOT, "pokemon", "dex", "entities.py")
ent_spec = importlib.util.spec_from_file_location("pokemon.dex.entities", ent_path)
ent_mod = importlib.util.module_from_spec(ent_spec)
sys.modules[ent_spec.name] = ent_mod
ent_spec.loader.exec_module(ent_mod)
Stats = ent_mod.Stats

# Minimal pokemon.dex package stub
pokemon_dex = types.ModuleType("pokemon.dex")
pokemon_dex.__path__ = []
pokemon_dex.entities = ent_mod
pokemon_dex.MOVEDEX = {}
pokemon_dex.Move = ent_mod.Move
pokemon_dex.Pokemon = ent_mod.Pokemon
sys.modules["pokemon.dex"] = pokemon_dex

# Minimal pokemon.data stub used by damage_calc
data_stub = types.ModuleType("pokemon.data")
data_stub.__path__ = []
data_stub.TYPE_CHART = {}
sys.modules["pokemon.data"] = data_stub

# Load battledata
bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon
Move = bd_mod.Move

# Load engine
eng_path = os.path.join(ROOT, "pokemon", "battle", "engine.py")
eng_spec = importlib.util.spec_from_file_location("pokemon.battle.engine", eng_path)
eng_mod = importlib.util.module_from_spec(eng_spec)
sys.modules[eng_spec.name] = eng_mod
eng_spec.loader.exec_module(eng_mod)
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleMove = eng_mod.BattleMove
Action = eng_mod.Action
ActionType = eng_mod.ActionType
BattleType = eng_mod.BattleType

# Preload minimal move data so the battle engine doesn't attempt to load the full dex
_tackle = Move("Tackle")
_tackle.raw = {"accuracy": 100, "basePower": 40, "type": "Normal", "category": "Physical"}
eng_mod.MOVEDEX["tackle"] = _tackle


def setup_battle(status=None):
    p1 = Pokemon("P1", level=1, hp=100, max_hp=100, moves=[Move("Tackle")])
    p2 = Pokemon("P2", level=1, hp=100, max_hp=100, moves=[Move("Tackle")])
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke, num in ((p1, 1), (p2, 2)):
        poke.base_stats = base
        poke.num = num
        poke.types = ["Normal"]
    if status:
        p1.status = status
    part1 = BattleParticipant("P1", [p1], is_ai=False)
    part2 = BattleParticipant("P2", [p2], is_ai=False)
    part1.active = [p1]
    part2.active = [p2]
    move = BattleMove("Tackle", power=40, accuracy=100)
    part1.pending_action = Action(part1, ActionType.MOVE, part2, move, move.priority)
    return Battle(BattleType.WILD, [part1, part2]), p1, p2


def test_paralysis_can_prevent_move():
    """Paralysis should occasionally stop a Pokémon from acting."""
    battle, p1, p2 = setup_battle("par")
    with patch("pokemon.battle.engine.random.random", return_value=0.1):
        battle.run_turn()
    assert p2.hp == 100


def test_frozen_blocks_move():
    """Frozen status should prevent action unless the Pokémon thaws."""
    battle, p1, p2 = setup_battle("frz")
    with patch("pokemon.battle.engine.random.random", return_value=0.5):
        battle.run_turn()
    assert p2.hp == 100
    assert p1.status == "frz"


def test_frozen_can_thaw_and_move():
    """Frozen Pokémon may thaw out and attack."""
    battle, p1, p2 = setup_battle("frz")
    with patch("pokemon.battle.engine.random.random", return_value=0.1):
        battle.run_turn()
    assert p2.hp < 100
    assert p1.status == 0
