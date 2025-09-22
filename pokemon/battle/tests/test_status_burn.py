"""Tests for burn status behaviour."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

import pytest

from .helpers import (
        build_battle,
        make_flame_orb,
        physical_move,
        resolve_status_text,
        run_damage,
)


def test_burn_residual_standard():
        battle, _, burned = build_battle(defender_status="brn")
        burned.max_hp = 160
        burned.hp = 160
        battle.residual()
        assert burned.hp == 150


def test_burn_heatproof_halves():
        battle, _, burned = build_battle(defender_status="brn", defender_ability="Heatproof")
        burned.max_hp = 128
        burned.hp = 128
        battle.residual()
        assert burned.hp == 124


def test_burn_magic_guard_blocks_chip():
        battle, _, burned = build_battle(defender_status="brn", defender_ability="Magic Guard")
        starting = burned.hp
        battle.residual()
        assert burned.hp == starting


def test_burn_attack_halving_and_guts():
        _, attacker, defender = build_battle()
        move = physical_move()
        baseline = run_damage(attacker, defender, move)

        attacker.setStatus("brn", source=attacker)
        burned_damage = run_damage(attacker, defender, move)
        assert burned_damage < baseline

        attacker.setStatus(0)
        attacker.ability = "Guts"
        attacker.setStatus("brn", source=attacker)
        guts_damage = run_damage(attacker, defender, move)
        assert guts_damage >= baseline


def test_burn_facade_not_halved():
        _, attacker, defender = build_battle()
        move = physical_move("Facade", 70)
        base_damage = run_damage(attacker, defender, move)
        attacker.setStatus("brn", source=attacker)
        burned_damage = run_damage(attacker, defender, move)
        assert burned_damage >= base_damage


def test_burn_immunity_fire_type():
        battle, _, defender = build_battle(defender_types=["Fire"])
        applied = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
        assert applied is False
        assert defender.status != "brn"


def test_burn_blocked_by_misty_terrain():
        battle, _, defender = build_battle()
        battle.field.terrain = "mistyterrain"
        applied = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
        assert applied is False
        assert defender.status != "brn"


def test_burn_blocked_by_safeguard():
        battle, _, defender = build_battle()
        defender.side.conditions["safeguard"] = {}
        applied = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
        assert applied is False
        assert defender.status != "brn"


def test_burn_blocked_by_substitute():
        battle, _, defender = build_battle()
        defender.volatiles["substitute"] = True
        applied = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
        assert applied is False
        assert defender.status != "brn"


def test_flame_orb_bypasses_protection():
        battle, pokemon, _ = build_battle()
        pokemon.side.conditions["safeguard"] = {}
        battle.field.terrain = "mistyterrain"
        orb = make_flame_orb()
        orb.onResidual(pokemon=pokemon)
        assert pokemon.status == "brn"


def test_flame_orb_respects_immunity():
        battle, pokemon, _ = build_battle(attacker_types=["Fire"])
        orb = make_flame_orb()
        orb.onResidual(pokemon=pokemon)
        assert pokemon.status != "brn"


def test_magic_guard_still_halves_attack():
        _, attacker, defender = build_battle()
        move = physical_move()
        baseline = run_damage(attacker, defender, move)
        attacker.ability = "Magic Guard"
        attacker.setStatus("brn", source=attacker)
        burned_damage = run_damage(attacker, defender, move)
        assert burned_damage < baseline


def test_burn_purifying_salt_immunity():
        battle, _, defender = build_battle(defender_ability="Purifying Salt")
        applied = battle.apply_status_condition(defender, "brn", source=battle.participants[0].active[0], effect="move:willowisp")
        assert applied is False
        assert defender.status != "brn"


def test_burn_status_messages():
        battle, attacker, defender = build_battle()
        logs = []
        battle.log_action = logs.append

        applied = battle.apply_status_condition(defender, "brn", source=attacker, effect="move:willowisp")
        assert applied is True
        start_template = resolve_status_text("brn", "start")
        assert start_template is not None
        assert logs[-1] == start_template.replace("[POKEMON]", defender.name)

        logs.clear()
        battle.apply_status_condition(defender, "brn", source=attacker, effect="move:willowisp")
        already_template = resolve_status_text("brn", "alreadyStarted")
        assert already_template is not None
        assert logs[-1] == already_template.replace("[POKEMON]", defender.name)

        logs.clear()
        defender.setStatus(0, battle=battle)
        end_template = resolve_status_text("brn", "end")
        assert end_template is not None
        assert logs[-1] == end_template.replace("[POKEMON]", defender.name)

        # Reapply burn to verify item-based curing text
        battle.apply_status_condition(defender, "brn", source=attacker, effect="move:willowisp")
        logs.clear()
        defender.setStatus(0, battle=battle, effect="item:fullheal")
        item_template = resolve_status_text("brn", "endFromItem")
        assert item_template is not None
        item_name = battle._item_display_name("fullheal")
        expected = item_template.replace("[POKEMON]", defender.name).replace("[ITEM]", item_name)
        assert logs[-1] == expected
