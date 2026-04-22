"""Tests for target modification and drag/trap flow."""

from __future__ import annotations

from .helpers import build_battle, load_modules


def _battle_action(actor, action_type, **kwargs):
    modules = load_modules()
    Action = __import__("pokemon.battle.actions", fromlist=["Action"]).Action
    return Action(actor=actor, action_type=action_type, **kwargs)


def test_modify_target_callback_can_replace_selected_target():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    defender.tempvals["last_damaged_by"] = {"source": attacker, "this_turn": True}
    move = BattleMove(
        name="Comeuppance",
        power=1,
        accuracy=100,
        type="Dark",
        raw={
            "category": "Physical",
            "basePower": 1,
            "accuracy": 100,
            "onModifyTarget": "Comeuppance.onModifyTarget",
        },
    )
    move.key = "comeuppance"

    action = _battle_action(
        battle.participants[1],
        ActionType.MOVE,
        target=battle.participants[0],
        move=move,
        pokemon=defender,
    )
    battle.use_move(action)

    assert action.target is battle.participants[0]


def test_drag_out_force_switch_sets_switch_out_flag():
    modules = load_modules()
    BattleMove = modules["BattleMove"]
    ActionType = __import__("pokemon.battle.actions", fromlist=["ActionType"]).ActionType
    battle, attacker, defender = build_battle()
    reserve = modules["Pokemon"]("Reserve", hp=200, max_hp=200)
    reserve.base_stats = attacker.base_stats
    reserve.types = ["Normal"]
    reserve.boosts = dict(attacker.boosts)
    reserve.tempvals = {}
    reserve.volatiles = {}
    reserve.side = battle.participants[1].side
    reserve.battle = battle
    battle.participants[1].pokemons.append(reserve)
    move = BattleMove(
        name="Roar",
        power=0,
        accuracy=100,
        type="Normal",
        raw={"category": "Status", "accuracy": 100, "forceSwitch": True},
    )
    move.key = "roar"

    action = _battle_action(
        battle.participants[0],
        ActionType.MOVE,
        target=battle.participants[1],
        move=move,
        pokemon=attacker,
    )
    battle.use_move(action)

    assert defender.tempvals.get("switch_out") is True


def test_trap_effect_prevents_standard_switch_out():
    battle, attacker, defender = build_battle()
    reserve = type(attacker)("Reserve", level=50, hp=200, max_hp=200)
    reserve.base_stats = attacker.base_stats
    reserve.types = ["Normal"]
    reserve.boosts = dict(attacker.boosts)
    reserve.tempvals = {}
    reserve.volatiles = {}
    reserve.side = battle.participants[1].side
    reserve.battle = battle
    battle.participants[1].pokemons.append(reserve)
    defender.volatiles["ingrain"] = True
    defender.tempvals["switch_out"] = True

    battle.run_switch()

    assert battle.participants[1].active[0] is defender


def test_foe_volatile_trap_effect_prevents_standard_switch_out():
    battle, attacker, defender = build_battle()
    reserve = type(attacker)("Reserve", level=50, hp=200, max_hp=200)
    reserve.base_stats = attacker.base_stats
    reserve.types = ["Normal"]
    reserve.boosts = dict(attacker.boosts)
    reserve.tempvals = {}
    reserve.volatiles = {}
    reserve.side = battle.participants[1].side
    reserve.battle = battle
    battle.participants[1].pokemons.append(reserve)

    attacker.volatiles["skydrop"] = {"id": "skydrop"}
    defender.volatiles["skydrop"] = True
    defender.tempvals["switch_out"] = True

    battle.run_switch()

    assert battle.participants[1].active[0] is defender
