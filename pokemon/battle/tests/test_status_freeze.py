"""Tests for freeze status behaviour."""

import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS

from .helpers import build_battle, resolve_status_text


def test_freeze_random_thaw(monkeypatch):
        handler = CONDITION_HANDLERS["frz"]
        battle, _, target = build_battle(defender_status="frz")
        monkeypatch.setattr(random, "random", lambda: 0.1)
        assert handler.onBeforeMove(target, battle=battle) is True
        assert target.status == 0


def test_freeze_can_keep_pokemon_frozen(monkeypatch):
        handler = CONDITION_HANDLERS["frz"]
        battle, _, target = build_battle(defender_status="frz")
        monkeypatch.setattr(random, "random", lambda: 0.5)
        assert handler.onBeforeMove(target, battle=battle) is False
        assert target.status == "frz"


def test_freeze_thaws_on_fire_hit():
        handler = CONDITION_HANDLERS["frz"]
        battle, _, target = build_battle(defender_status="frz")
        class Move:
                type = "Fire"
                raw = {}
        handler.onDamagingHit(target, move=Move(), battle=battle)
        assert target.status == 0


def test_freeze_thaws_on_flagged_move():
        handler = CONDITION_HANDLERS["frz"]
        battle, _, target = build_battle(defender_status="frz")
        class Move:
                type = "Water"
                raw = {"thawsTarget": True}
        handler.onDamagingHit(target, move=Move(), battle=battle)
        assert target.status == 0


def test_freeze_immunity_for_ice_types():
        battle, _, target = build_battle(defender_types=["Ice"])
        applied = battle.apply_status_condition(target, "frz", source=battle.participants[0].active[0], effect="move:icebeam")
        assert applied is False
        assert target.status != "frz"


def test_freeze_magma_armor_immunity():
        battle, _, target = build_battle(defender_ability="Magma Armor")
        applied = battle.apply_status_condition(target, "frz", source=battle.participants[0].active[0], effect="move:icebeam")
        assert applied is False
        assert target.status != "frz"


def test_freeze_blocked_by_harsh_sunlight():
        battle, _, target = build_battle()
        battle.field.weather = "harshsunlight"
        applied = battle.apply_status_condition(target, "frz", source=battle.participants[0].active[0], effect="move:icebeam")
        assert applied is False
        assert target.status != "frz"


def test_freeze_status_messages():
        battle, attacker, target = build_battle()
        logs = []
        battle.log_action = logs.append

        applied = battle.apply_status_condition(target, "frz", source=attacker, effect="move:icebeam")
        assert applied is True
        start_template = resolve_status_text("frz", "start")
        assert start_template is not None
        assert logs[-1] == start_template.replace("[POKEMON]", target.name)

        logs.clear()
        battle.apply_status_condition(target, "frz", source=attacker, effect="move:icebeam")
        already_template = resolve_status_text("frz", "alreadyStarted")
        assert already_template is not None
        assert logs[-1] == already_template.replace("[POKEMON]", target.name)

        logs.clear()
        target.setStatus(0, battle=battle)
        end_template = resolve_status_text("frz", "end")
        assert end_template is not None
        assert logs[-1] == end_template.replace("[POKEMON]", target.name)
