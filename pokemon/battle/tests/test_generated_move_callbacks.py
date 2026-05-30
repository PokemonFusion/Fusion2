"""Generated move callback resolution and adapter smoke tests.

These tests are intentionally opt-in.  They prove dex callback references are
loadable and that compatible callback groups can be invoked offline, but they
do not replace exact semantic contracts for move correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable, Mapping

import pytest

from pokemon import dex
from pokemon.battle.callbacks import _resolve_callback, invoke_callback
from pokemon.dex.functions import moves_funcs


pytestmark = pytest.mark.callbacks


TOP_LEVEL_CALLBACK_KEYS = {
    "onHit",
    "onTry",
    "onTryHit",
    "onTryMove",
    "onModifyMove",
    "basePowerCallback",
    "damageCallback",
    "onBasePower",
    "onAfterMove",
    "onPrepareHit",
}

INVOKED_CALLBACK_KEYS = {
    "basePowerCallback",
    "damageCallback",
    "onBasePower",
    "onModifyMove",
    "onTry",
    "onTryHit",
    "onTryMove",
    "onPrepareHit",
    "onAfterMove",
    "secondary.onHit",
}

ALLOWED_RETURN_TYPES = (type(None), bool, int, float, str, dict, list, tuple)


@dataclass(frozen=True)
class CallbackCase:
    move_name: str
    hook: str
    ref: Any
    raw: Mapping[str, Any]

    def __str__(self) -> str:
        return f"{self.move_name}:{self.hook}"


class CallbackPokemon(SimpleNamespace):
    def __init__(self, **kwargs):
        defaults = {
            "name": "Callbackmon",
            "species": "Callbackmon",
            "hp": 200,
            "max_hp": 200,
            "level": 50,
            "types": ["Normal"],
            "boosts": {
                "attack": 0,
                "defense": 0,
                "special_attack": 0,
                "special_defense": 0,
                "speed": 0,
                "accuracy": 0,
                "evasion": 0,
            },
            "tempvals": {},
            "volatiles": {},
            "side": SimpleNamespace(conditions={}, hazards={}, screens={}, volatiles={}),
            "item": None,
            "held_item": None,
            "ability": None,
            "weightkg": 120,
            "status": 0,
            "gender": "N",
            "active_move_actions": 1,
            "last_move_this_turn": "fusionflare",
            "pledge_combo": True,
            "grounded": True,
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setStatus(self, status, *args, **kwargs):
        self.status = status
        return True

    def addVolatile(self, volatile, *args, **kwargs):
        self.volatiles[volatile] = True
        return True


class CallbackBattle(SimpleNamespace):
    def __init__(self):
        super().__init__(
            field=SimpleNamespace(weather="", terrain="", pseudo_weather={}),
            terrain="",
            weather="",
            sides=[],
            rng=None,
        )
        self.log = []

    def log_action(self, message):
        self.log.append(message)

    def heal(self, pokemon, amount, *args, **kwargs):
        before = pokemon.hp
        pokemon.hp = min(pokemon.max_hp, pokemon.hp + int(amount))
        return pokemon.hp - before

    def damage(self, pokemon, amount, *args, **kwargs):
        pokemon.hp = max(0, pokemon.hp - int(amount))
        return amount

    def apply_status_condition(self, pokemon, status, *args, **kwargs):
        pokemon.status = status
        return True

    def apply_volatile_status(self, pokemon, volatile, *args, **kwargs):
        pokemon.volatiles[volatile] = True
        return True

    def setWeather(self, weather, *args, **kwargs):
        self.weather = weather
        self.field.weather = weather
        return True

    def setTerrain(self, terrain, *args, **kwargs):
        self.terrain = terrain
        self.field.terrain = terrain
        return True

    def add_side_condition(self, participant, condition, state=None, *args, **kwargs):
        side = getattr(participant, "side", participant)
        side.conditions[condition] = dict(state or {})
        return side.conditions[condition]

    def runEvent(self, *args, **kwargs):
        return None


def _entry_raw(entry: Any) -> Mapping[str, Any]:
    raw = getattr(entry, "raw", None)
    if isinstance(raw, Mapping):
        return raw
    if isinstance(entry, Mapping):
        return entry
    return {}


def _callback_refs_from_effect(
    move_name: str,
    hook_prefix: str,
    effect: Mapping[str, Any],
) -> Iterable[CallbackCase]:
    if effect.get("onHit"):
        yield CallbackCase(move_name, f"{hook_prefix}.onHit", effect["onHit"], effect)


def _callback_cases() -> tuple[CallbackCase, ...]:
    cases: list[CallbackCase] = []
    for key, entry in dex.MOVEDEX.items():
        raw = _entry_raw(entry)
        move_name = str(raw.get("name") or getattr(entry, "name", key))
        for hook in sorted(TOP_LEVEL_CALLBACK_KEYS):
            if raw.get(hook):
                cases.append(CallbackCase(move_name, hook, raw[hook], raw))

        secondary = raw.get("secondary")
        if isinstance(secondary, Mapping):
            cases.extend(_callback_refs_from_effect(move_name, "secondary", secondary))

        secondaries = raw.get("secondaries") or ()
        if isinstance(secondaries, Mapping):
            cases.extend(_callback_refs_from_effect(move_name, "secondary", secondaries))
        else:
            for effect in secondaries:
                if isinstance(effect, Mapping):
                    cases.extend(_callback_refs_from_effect(move_name, "secondary", effect))

    return tuple(cases)


CALLBACK_CASES = _callback_cases()
INVOKED_CASES = tuple(case for case in CALLBACK_CASES if case.hook in INVOKED_CALLBACK_KEYS)


def _resolve_case(case: CallbackCase):
    callback = _resolve_callback(case.ref, moves_funcs)
    assert callable(callback), f"{case.move_name} {case.hook} did not resolve: {case.ref!r}"
    return callback


def _callback_context(case: CallbackCase):
    user = CallbackPokemon(name="User")
    target = CallbackPokemon(name="Target", types=["Water"], weightkg=220, status="brn")
    battle = CallbackBattle()
    user.side = SimpleNamespace(conditions={}, hazards={}, screens={}, volatiles={})
    target.side = SimpleNamespace(conditions={}, hazards={}, screens={}, volatiles={})
    move = SimpleNamespace(
        name=case.move_name,
        id=str(case.raw.get("id") or case.move_name).replace(" ", "").lower(),
        key=str(case.raw.get("id") or case.move_name).replace(" ", "").lower(),
        raw=dict(case.raw),
        power=int(case.raw.get("basePower", 80) or 80),
        basePower=int(case.raw.get("basePower", 80) or 80),
        accuracy=case.raw.get("accuracy", True),
        type=case.raw.get("type", "Normal"),
        category=case.raw.get("category", "Physical"),
        target=case.raw.get("target", "normal"),
        flags=dict(case.raw.get("flags", {}) or {}),
        sourceEffect=case.raw.get("sourceEffect", "round"),
        hit=1,
        pp=5,
    )
    return user, target, move, battle


def _invoke_case(case: CallbackCase, callback):
    user, target, move, battle = _callback_context(case)

    if case.hook == "basePowerCallback":
        return invoke_callback(callback, user, target, move, battle=battle)
    if case.hook == "damageCallback":
        return invoke_callback(callback, user, target, move, battle=battle)
    if case.hook == "onBasePower":
        return invoke_callback(callback, user, target, move, battle=battle)
    if case.hook == "onModifyMove":
        return invoke_callback(callback, move, user, target, battle=battle)
    if case.hook in {"onTry", "onTryMove", "onPrepareHit", "onAfterMove"}:
        return invoke_callback(callback, user, target, move, battle=battle)
    if case.hook == "onTryHit":
        return invoke_callback(callback, target, user, move, battle=battle)
    if case.hook == "secondary.onHit":
        return invoke_callback(callback, user, target, battle=battle, move=move)
    raise AssertionError(f"No invocation adapter for {case.hook}")


@pytest.mark.parametrize("case", CALLBACK_CASES, ids=str)
def test_all_discovered_move_callbacks_resolve(case):
    _resolve_case(case)


@pytest.mark.parametrize("case", INVOKED_CASES, ids=str)
def test_generated_move_callback_adapters_invoke_compatible_hooks(case):
    callback = _resolve_case(case)
    result = _invoke_case(case, callback)

    assert isinstance(result, ALLOWED_RETURN_TYPES) or hasattr(result, "__dict__")
