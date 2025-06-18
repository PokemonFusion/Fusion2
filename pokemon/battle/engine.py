from __future__ import annotations

from .battledata import BattleData
from .turnorder import calculateTurnorder


def execute_turn(battle: BattleData, damage: int = 10):
    """Resolve a very simple battle turn.

    Each position that has declared an attack will deal ``damage`` HP to its
    declared target. Turn order is determined via :func:`calculateTurnorder`.
    After resolution, declarations are cleared and the battle turn counter
    increments.
    """
    order = calculateTurnorder(battle.turndata)
    results = []
    for pos_name in order:
        position = battle.turndata.positions[pos_name]
        action = position.getAction()
        if not action or not position.pokemon:
            continue
        target_name = position.getTarget()
        if not target_name:
            continue
        target = battle.turndata.positions.get(target_name)
        if not target or not target.pokemon:
            continue
        target.pokemon.hp = max(0, target.pokemon.hp - damage)
        results.append((pos_name, action.name, target_name))
    battle.battle.incrementTurn()
    for pos in battle.turndata.positions.values():
        pos.removeDeclare()
    return results
