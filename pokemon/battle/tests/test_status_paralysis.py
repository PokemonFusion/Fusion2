"""Tests for paralysis status behaviour."""

import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS

from .helpers import build_battle, resolve_status_text


def test_paralysis_speed_halved():
        _, _, target = build_battle(defender_status="par")
        handler = CONDITION_HANDLERS["par"]
        halved = handler.onModifySpe(200, pokemon=target)
        assert halved == 100


def test_paralysis_can_prevent_move(monkeypatch):
        battle, _, target = build_battle(defender_status="par")
        handler = CONDITION_HANDLERS["par"]
        monkeypatch.setattr(random, "random", lambda: 0.1)
        assert handler.onBeforeMove(target, battle=battle) is False
        monkeypatch.setattr(random, "random", lambda: 0.5)
        assert handler.onBeforeMove(target, battle=battle) is True


def test_paralysis_electric_immunity():
        battle, _, target = build_battle(defender_types=["Electric"])
        applied = battle.apply_status_condition(target, "par", source=battle.participants[0].active[0], effect="move:thunderwave")
        assert applied is False
        assert target.status != "par"


def test_paralysis_limber_immunity():
        battle, _, target = build_battle(defender_ability="Limber")
        applied = battle.apply_status_condition(target, "par", source=battle.participants[0].active[0], effect="move:thunderwave")
        assert applied is False
        assert target.status != "par"


def test_paralysis_status_messages():
        battle, attacker, target = build_battle()
        logs = []
        battle.log_action = logs.append

        applied = battle.apply_status_condition(target, "par", source=attacker, effect="move:thunderwave")
        assert applied is True
        start_template = resolve_status_text("par", "start")
        assert start_template is not None
        assert logs[-1] == start_template.replace("[POKEMON]", target.name)

        logs.clear()
        battle.apply_status_condition(target, "par", source=attacker, effect="move:thunderwave")
        already_template = resolve_status_text("par", "alreadyStarted")
        assert already_template is not None
        assert logs[-1] == already_template.replace("[POKEMON]", target.name)

        logs.clear()
        target.setStatus(0, battle=battle)
        end_template = resolve_status_text("par", "end")
        assert end_template is not None
        assert logs[-1] == end_template.replace("[POKEMON]", target.name)
