import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Minimal package structure for pokemon.battle
pkg_battle = types.ModuleType("pokemon.battle")
pkg_battle.__path__ = []
sys.modules["pokemon.battle"] = pkg_battle

bd_path = os.path.join(ROOT, "pokemon", "battle", "battledata.py")
bd_spec = importlib.util.spec_from_file_location("pokemon.battle.battledata", bd_path)
bd_mod = importlib.util.module_from_spec(bd_spec)
sys.modules[bd_spec.name] = bd_mod
bd_spec.loader.exec_module(bd_mod)
Pokemon = bd_mod.Pokemon
Move = bd_mod.Move
TurnInit = bd_mod.TurnInit
DeclareAttack = bd_mod.DeclareAttack
PositionData = bd_mod.PositionData

# Load turnorder module after stubbing battledata
turn_path = os.path.join(ROOT, "pokemon", "battle", "turnorder.py")
turn_spec = importlib.util.spec_from_file_location("pokemon.battle.turnorder", turn_path)
turn_mod = importlib.util.module_from_spec(turn_spec)
sys.modules[turn_spec.name] = turn_mod
turn_spec.loader.exec_module(turn_mod)
calculateTurnorder = turn_mod.calculateTurnorder


def build_round(prios):
    positions = {}
    for idx, (priority, speed) in enumerate(prios, start=1):
        poke = Pokemon(f"P{idx}")
        poke.speed = speed
        move = Move(f"M{idx}", priority=priority)
        atk = DeclareAttack("t", move)
        pos = PositionData(poke)
        pos.turninit = TurnInit(attack=atk)
        positions[f"A{idx}"] = pos
    return types.SimpleNamespace(positions=positions)


def test_turnorder_consecutive_calls():
    rnd1 = build_round([(1, 10), (0, 20)])
    order1 = calculateTurnorder(rnd1)
    assert order1 == ["A1", "A2"]

    rnd2 = build_round([(0, 5), (0, 30), (0, 10)])
    order2 = calculateTurnorder(rnd2)
    assert order2 == ["A2", "A3", "A1"]
