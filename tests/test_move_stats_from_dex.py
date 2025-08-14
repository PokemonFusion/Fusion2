import os
import sys
import importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Reload core modules to ensure fresh MOVEDEX and engine references
# in case other tests stubbed these modules.
dex_mod = importlib.import_module("pokemon.dex")
eng_mod = importlib.import_module("pokemon.battle.engine")
bd_mod = importlib.import_module("pokemon.battle.battledata")

dex_mod = importlib.reload(dex_mod)
eng_mod = importlib.reload(eng_mod)
bd_mod = importlib.reload(bd_mod)

MOVEDEX = dex_mod.MOVEDEX
Battle = eng_mod.Battle
BattleParticipant = eng_mod.BattleParticipant
BattleMove = eng_mod.BattleMove
Action = eng_mod.Action
ActionType = eng_mod.ActionType
BattleType = eng_mod.BattleType
Pokemon = bd_mod.Pokemon


def test_move_stats_loaded_from_dex():
    """Moves should hydrate core stats from MOVEDEX when used."""
    user = Pokemon("User")
    target = Pokemon("Target")
    move = BattleMove("Tackle", power=0, accuracy=0)
    # Avoid damage calculation during the test
    move.onHit = lambda *args, **kwargs: None
    p1 = BattleParticipant("P1", [user])
    p2 = BattleParticipant("P2", [target])
    p1.active = [user]
    p2.active = [target]
    action = Action(p1, ActionType.MOVE, p2, move, move.priority)
    battle = Battle(BattleType.WILD, [p1, p2])
    battle.use_move(action)

    dex_move = MOVEDEX["tackle"]
    assert action.move.power == dex_move.power
    assert action.move.accuracy == dex_move.accuracy
    assert action.move.type == dex_move.type
    assert action.move.priority == dex_move.raw.get("priority", 0)
