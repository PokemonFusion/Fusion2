"""Tests for the Aura Break ability interactions."""

from tests.test_all_moves_and_abilities import build_ability, get_dex_data, setup_battle
from pokemon.battle.engine import BattleMove


def _run_battle(defender_ability=None):
    """Return damage dealt when attacking into ``defender_ability``."""
    _, abilitydex, *_ = get_dex_data()
    move = BattleMove(
        "Bite", power=200, accuracy=100, type="Dark", raw={"category": "Physical"}
    )
    battle, user, target = setup_battle(move)
    user.ability = build_ability(abilitydex["Darkaura"])
    if defender_ability:
        target.ability = defender_ability
    start = target.hp
    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()
    battle.run_faint()
    battle.residual()
    battle.end_turn()
    return start - target.hp


def test_aura_break_weakens_dark_aura():
    """Aura Break should reduce Dark Aura's power boost."""
    _, abilitydex, *_ = get_dex_data()
    aura_break = build_ability(abilitydex["Aurabreak"])
    dmg_without = _run_battle()
    dmg_with = _run_battle(aura_break)
    assert dmg_with < dmg_without


def test_on_any_try_primary_hit_sets_flag():
    """Aurabreak should flag moves when the global event fires."""
    _, abilitydex, *_ = get_dex_data()
    move = BattleMove(
        "Bite", power=200, accuracy=100, type="Dark", raw={"category": "Physical"}
    )
    battle, user, target = setup_battle(move)
    user.ability = build_ability(abilitydex["Darkaura"])
    target.ability = build_ability(abilitydex["Aurabreak"])
    battle.start_turn()
    battle.run_switch()
    battle.run_after_switch()
    battle.run_move()
    battle.run_faint()
    battle.residual()
    battle.end_turn()
    assert getattr(move, "hasAuraBreak", False) is True
