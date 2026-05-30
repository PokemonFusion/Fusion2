"""Tests for speed-modifier event routing during action ordering."""

from __future__ import annotations

from .helpers import build_battle, load_modules, physical_move


def test_order_actions_applies_status_modify_spe_events():
    load_modules()
    from pokemon.battle.actions import Action, ActionType

    battle, attacker, defender = build_battle(defender_status="par")
    move = physical_move(name="Tackle", power=40)

    actions = [
        Action(
            actor=battle.participants[0],
            action_type=ActionType.MOVE,
            target=battle.participants[1],
            move=move,
            pokemon=attacker,
        ),
        Action(
            actor=battle.participants[1],
            action_type=ActionType.MOVE,
            target=battle.participants[0],
            move=move,
            pokemon=defender,
        ),
    ]

    ordered = battle.order_actions(actions)

    assert ordered[0].pokemon is attacker
    assert ordered[1].pokemon is defender
    assert ordered[0].speed > ordered[1].speed


def test_order_actions_applies_side_condition_modify_spe_events():
    load_modules()
    from pokemon.battle.actions import Action, ActionType

    battle, attacker, defender = build_battle()
    attacker.base_stats.speed = 60
    defender.base_stats.speed = 100
    move = physical_move(name="Tackle", power=40)

    added = battle.add_side_condition(
        battle.participants[0],
        "tailwind",
        {"onSideStart": None},
        source=attacker,
    )
    assert added is True

    actions = [
        Action(
            actor=battle.participants[0],
            action_type=ActionType.MOVE,
            target=battle.participants[1],
            move=move,
            pokemon=attacker,
        ),
        Action(
            actor=battle.participants[1],
            action_type=ActionType.MOVE,
            target=battle.participants[0],
            move=move,
            pokemon=defender,
        ),
    ]

    ordered = battle.order_actions(actions)

    assert ordered[0].pokemon is attacker
    assert ordered[1].pokemon is defender
    assert ordered[0].speed == 120
    assert ordered[1].speed == 100
