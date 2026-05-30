"""Tests for pre-move TryMove routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


def _battle_action(actor, action_type, **kwargs):
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


class _AnyTryMoveVolatile:
    def __init__(self):
        self.calls = 0

    def onAnyTryMove(self, user, target, move, **kwargs):
        self.calls += 1
        return False


def test_move_on_try_move_blocks_execution_before_damage():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    move = BattleMove(
        name="Charge Gate",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "chargegate"
    move.onTryMove = lambda user, target, battle=None, move=None: False
    start_hp = defender.hp

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.hp == start_hp


def test_non_ability_any_try_move_holder_can_block_move():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    move = BattleMove(
        name="Tackle",
        power=50,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 50, "accuracy": 100},
    )
    move.key = "tackle"
    start_hp = defender.hp
    handler = _AnyTryMoveVolatile()
    defender.volatiles["watchtrymove"] = {"id": "watchtrymove"}

    import pokemon.dex.functions.moves_funcs as moves_funcs

    original = moves_funcs.VOLATILE_HANDLERS.get("watchtrymove")
    moves_funcs.VOLATILE_HANDLERS["watchtrymove"] = handler
    try:
        action = _battle_action(
            battle.participants[0],
            ActionType.MOVE,
            target=battle.participants[1],
            move=move,
            pokemon=attacker,
        )
        battle.use_move(action)
    finally:
        if original is None:
            moves_funcs.VOLATILE_HANDLERS.pop("watchtrymove", None)
        else:
            moves_funcs.VOLATILE_HANDLERS["watchtrymove"] = original

    assert handler.calls == 1
    assert defender.hp == start_hp
