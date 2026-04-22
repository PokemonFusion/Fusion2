"""Tests for move lock, override, and disable event routing."""

from __future__ import annotations

from .helpers import build_battle, load_modules


def _battle_action(actor, action_type, **kwargs):
    modules = load_modules()
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


def test_lockedmove_forces_the_stored_move():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    locked = BattleMove(
        name="Tackle",
        power=40,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100},
    )
    locked.key = "tackle"
    other = BattleMove(
        name="Swift",
        power=60,
        accuracy=True,
        type="Normal",
        raw={"category": "Special", "basePower": 60, "accuracy": True},
    )
    other.key = "swift"
    attacker.moves = [locked, other]
    attacker.volatiles["lockedmove"] = {"move": locked, "turns": 2}
    start_hp = defender.hp

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=other,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert action.move is locked
    assert defender.hp < start_hp


def test_encore_override_action_replaces_selected_move():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    encore_move = BattleMove(
        name="Tackle",
        power=40,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100},
    )
    encore_move.key = "tackle"
    chosen_move = BattleMove(
        name="Swift",
        power=60,
        accuracy=True,
        type="Normal",
        raw={"category": "Special", "basePower": 60, "accuracy": True},
    )
    chosen_move.key = "swift"
    attacker.moves = [encore_move, chosen_move]
    attacker.volatiles["encore"] = encore_move
    start_hp = defender.hp

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=chosen_move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert action.move is encore_move
    assert defender.hp < start_hp


def test_taunt_disables_status_moves():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    status_move = BattleMove(
        name="Growl",
        power=0,
        accuracy=100,
        type="Normal",
        raw={"category": "Status", "accuracy": 100},
    )
    status_move.key = "growl"
    attacker.volatiles["taunt"] = True
    start_boosts = dict(defender.boosts)

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=status_move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.boosts == start_boosts


def test_stalling_move_fails_when_stall_roll_misses(monkeypatch):
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    engine_mod = __import__("pokemon.battle.engine", fromlist=["random"])
    battle, attacker, defender = build_battle()
    attacker.volatiles["stall"] = {"counter": 2}
    monkeypatch.setattr(engine_mod.random, "random", lambda: 0.75)
    move = BattleMove(
        name="Detect",
        power=0,
        accuracy=True,
        type="Fighting",
        raw={
            "category": "Status",
            "accuracy": True,
            "stallingMove": True,
            "onHit": "Detect.onHit",
        },
    )
    move.key = "detect"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert "protect" not in attacker.volatiles


def test_non_stalling_move_clears_stall_chain():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    attacker.volatiles["stall"] = {"counter": 4}
    move = BattleMove(
        name="Tackle",
        power=40,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100},
    )
    move.key = "tackle"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert "stall" not in attacker.volatiles


def test_foe_before_move_volatile_can_block_move():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    defender.volatiles["imprison"] = {"id": "imprison"}
    move = BattleMove(
        name="Tackle",
        power=40,
        accuracy=100,
        type="Normal",
        raw={"category": "Physical", "basePower": 40, "accuracy": 100},
    )
    move.key = "tackle"
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
