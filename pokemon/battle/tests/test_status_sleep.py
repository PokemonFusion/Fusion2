"""Tests for sleep status behaviour."""

import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS

from .helpers import build_battle, resolve_status_text


def test_sleep_turn_range(monkeypatch):
        handler = CONDITION_HANDLERS["slp"]
        durations = set()
        sequence = [1, 2, 3]
        index = {"i": 0}

        def fake_randint(a, b):
                value = sequence[index["i"] % len(sequence)]
                index["i"] += 1
                return value

        monkeypatch.setattr(random, "randint", fake_randint)
        for _ in range(3):
                battle, _, target = build_battle()
                assert handler.onStart(target, battle=battle, effect=None, previous=None) is True
                durations.add(target.tempvals.get("sleep_turns"))
        assert durations == {1, 2, 3}


def test_rest_sets_two_turns():
        handler = CONDITION_HANDLERS["slp"]
        battle, _, target = build_battle()
        assert handler.onStart(target, battle=battle, effect="move:rest", previous=None) is True
        assert target.tempvals["sleep_turns"] == 2
        assert handler.onBeforeMove(target, battle=battle) is False
        assert handler.onBeforeMove(target, battle=battle) is False
        assert handler.onBeforeMove(target, battle=battle) is True
        assert target.status == 0


def test_sleep_blocked_by_insomnia():
        battle, _, target = build_battle(defender_ability="Insomnia")
        applied = battle.apply_status_condition(target, "slp", source=battle.participants[0].active[0], effect="move:spore")
        assert applied is False
        assert target.status != "slp"


def test_sleep_blocked_by_sweet_veil():
        battle, _, target = build_battle(defender_ability="Sweet Veil")
        applied = battle.apply_status_condition(target, "slp", source=battle.participants[0].active[0], effect="move:spore")
        assert applied is False
        assert target.status != "slp"


def test_sleep_blocked_by_electric_terrain():
        battle, _, target = build_battle()
        battle.field.terrain = "electricterrain"
        applied = battle.apply_status_condition(target, "slp", source=battle.participants[0].active[0], effect="move:spore")
        assert applied is False
        assert target.status != "slp"


def test_sleep_blocked_by_uproar():
        battle, attacker, target = build_battle()
        attacker.volatiles["uproar"] = 3
        applied = battle.apply_status_condition(target, "slp", source=attacker, effect="move:spore")
        assert applied is False
        assert target.status != "slp"


def test_sleep_status_messages(monkeypatch):
        battle, attacker, target = build_battle()
        logs = []
        battle.log_action = logs.append

        # Ensure deterministic sleep duration
        monkeypatch.setattr(random, "randint", lambda *_args, **_kwargs: 2)
        applied = battle.apply_status_condition(target, "slp", source=attacker, effect="move:spore")
        assert applied is True
        start_template = resolve_status_text("slp", "start")
        assert start_template is not None
        assert logs[-1] == start_template.replace("[POKEMON]", target.name)

        logs.clear()
        battle.apply_status_condition(target, "slp", source=attacker, effect="move:spore")
        already_template = resolve_status_text("slp", "alreadyStarted")
        assert already_template is not None
        assert logs[-1] == already_template.replace("[POKEMON]", target.name)

        logs.clear()
        target.setStatus(0, battle=battle)
        end_template = resolve_status_text("slp", "end")
        assert end_template is not None
        assert logs[-1] == end_template.replace("[POKEMON]", target.name)
