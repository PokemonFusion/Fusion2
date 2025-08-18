"""Tests for abilities modifying ally base power."""

from tests.test_all_moves_and_abilities import build_ability, get_dex_data
from pokemon.battle.engine import (
    Battle,
    BattleMove,
    BattleParticipant,
    Action,
    ActionType,
    BattleType,
)
from pokemon.battle.battledata import Pokemon
import random


def _run_ally_battle(ability_name, move_type, category):
    """Return damage dealt with an ally holding ``ability_name``."""
    _, abilitydex, Stats, _ = get_dex_data()
    move = BattleMove(
        "TestMove",
        power=200,
        accuracy=100,
        type=move_type,
        raw={"category": category},
    )
    # Create Pokémon
    user = Pokemon("User")
    target = Pokemon("Target")
    ally = Pokemon("Ally")
    base = Stats(hp=100, atk=50, def_=50, spa=50, spd=50, spe=50)
    for poke, num in ((user, 1), (target, 2), (ally, 3)):
        poke.base_stats = base
        poke.num = num
        poke.types = ["Normal"]
        poke.hp = poke.max_hp = 100
    if ability_name:
        ally.ability = build_ability(abilitydex[ability_name])
        # Ensure ability handlers know their owner
        cb = ally.ability.raw.get("onAllyBasePower")
        if getattr(cb, "func", None):
            inst = cb.func.__self__
            inst.effect_state = {"target": ally}
            inst.raw = ally.ability.raw
    # Participants: user and ally share team "A"
    p_user = BattleParticipant("P1", [user], is_ai=False, team="A")
    p_ally = BattleParticipant("PAlly", [ally], is_ai=False, team="A")
    p_target = BattleParticipant("P2", [target], is_ai=False, team="B")
    p_user.active = [user]
    p_ally.active = [ally]
    p_target.active = [target]
    action = Action(p_user, ActionType.MOVE, p_target, move, move.priority)
    p_user.pending_action = action
    battle = Battle(BattleType.WILD, [p_user, p_ally, p_target])
    random.seed(0)
    start = target.hp
    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()
    battle.run_faint()
    battle.residual()
    battle.end_turn()
    return start - target.hp


def test_battery_boosts_special_moves():
    dmg_without = _run_ally_battle(None, "Electric", "Special")
    dmg_with = _run_ally_battle("Battery", "Electric", "Special")
    assert dmg_with > dmg_without


def test_powerspot_boosts_physical_moves():
    dmg_without = _run_ally_battle(None, "Normal", "Physical")
    dmg_with = _run_ally_battle("Powerspot", "Normal", "Physical")
    assert dmg_with > dmg_without


def test_steelyspirit_boosts_steel_moves():
    dmg_without = _run_ally_battle(None, "Steel", "Physical")
    dmg_with = _run_ally_battle("Steelyspirit", "Steel", "Physical")
    assert dmg_with > dmg_without
