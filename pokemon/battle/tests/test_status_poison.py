"""Tests for poison and toxic status behaviour."""

import os
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS

from .helpers import build_battle, resolve_status_text


def test_poison_residual_damage():
        battle, _, target = build_battle(defender_status="psn")
        target.max_hp = 160
        target.hp = 160
        battle.residual()
        assert target.hp == 140


def test_poison_heal_recovers():
        battle, _, target = build_battle(defender_status="psn", defender_ability="Poison Heal")
        target.max_hp = 160
        target.hp = 120
        battle.residual()
        assert target.hp == 140


def test_poison_magic_guard_blocks_damage():
        battle, _, target = build_battle(defender_status="psn", defender_ability="Magic Guard")
        starting = target.hp
        battle.residual()
        assert target.hp == starting


def test_toxic_ramp_and_reset():
        battle, _, target = build_battle()
        target.setStatus("tox", source=target)
        target.max_hp = 160
        target.hp = 160
        for stage in range(1, 4):
                pre = target.hp
                battle.residual()
                expected = max(1, (target.max_hp * stage) // 16)
                assert target.hp == pre - expected
        handler = CONDITION_HANDLERS["tox"]
        handler.onSwitchOut(target, battle=battle)
        handler.onSwitchIn(target, battle=battle)
        target.hp = 160
        battle.residual()
        assert target.hp == 150
        assert target.status == "tox"


def test_poison_immunity_for_steel_type():
        battle, _, target = build_battle(defender_types=["Steel"])
        applied = battle.apply_status_condition(target, "psn", source=battle.participants[0].active[0], effect="move:toxic")
        assert applied is False
        assert target.status != "psn"


def test_corrosion_bypasses_immunity():
        battle, attacker, target = build_battle(defender_types=["Steel"])
        attacker.ability = "Corrosion"
        applied = battle.apply_status_condition(target, "psn", source=attacker, effect="move:toxic")
        assert applied is True
        assert target.status == "psn"


def test_pastel_veil_blocks_poison():
        battle, _, target = build_battle(defender_ability="Pastel Veil")
        applied = battle.apply_status_condition(target, "psn", source=battle.participants[0].active[0], effect="move:toxic")
        assert applied is False
        assert target.status != "psn"


def test_poison_heal_on_badly_poisoned():
        battle, _, target = build_battle(defender_status="tox", defender_ability="Poison Heal")
        target.max_hp = 160
        target.hp = 120
        battle.residual()
        assert target.hp == 140


def test_badly_poisoned_magic_guard():
        battle, _, target = build_battle(defender_status="tox", defender_ability="Magic Guard")
        starting = target.hp
        battle.residual()
        assert target.hp == starting


def test_purifying_salt_blocks_poison():
        battle, _, target = build_battle(defender_ability="Purifying Salt")
        applied = battle.apply_status_condition(target, "psn", source=battle.participants[0].active[0], effect="move:toxic")
        assert applied is False
        assert target.status != "psn"


def test_poison_status_messages():
        battle, attacker, target = build_battle()
        logs = []
        battle.log_action = logs.append

        applied = battle.apply_status_condition(target, "psn", source=attacker, effect="move:toxic")
        assert applied is True
        psn_start = resolve_status_text("psn", "start")
        assert psn_start is not None
        assert logs[-1] == psn_start.replace("[POKEMON]", target.name)

        logs.clear()
        battle.apply_status_condition(target, "psn", source=attacker, effect="move:toxic")
        psn_already = resolve_status_text("psn", "alreadyStarted")
        assert psn_already is not None
        assert logs[-1] == psn_already.replace("[POKEMON]", target.name)

        logs.clear()
        target.setStatus(0, battle=battle)
        psn_end = resolve_status_text("psn", "end")
        assert psn_end is not None
        assert logs[-1] == psn_end.replace("[POKEMON]", target.name)

        # Verify badly poisoned messages share the same templates
        logs.clear()
        applied = battle.apply_status_condition(target, "tox", source=attacker, effect="move:toxic")
        assert applied is True
        tox_start = resolve_status_text("tox", "start")
        assert tox_start is not None
        assert logs[-1] == tox_start.replace("[POKEMON]", target.name)

        logs.clear()
        battle.apply_status_condition(target, "tox", source=attacker, effect="move:toxic")
        tox_already = resolve_status_text("tox", "alreadyStarted")
        assert tox_already is not None
        assert logs[-1] == tox_already.replace("[POKEMON]", target.name)

        logs.clear()
        target.setStatus(0, battle=battle)
        tox_end = resolve_status_text("tox", "end")
        assert tox_end is not None
        assert logs[-1] == tox_end.replace("[POKEMON]", target.name)
