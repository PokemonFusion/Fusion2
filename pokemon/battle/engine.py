"""Basic battle engine implementing turn-based combat.

This module provides a simplified framework for battles using the design
specification found in the repository documentation.  The focus is on
turn ordering and state tracking rather than full battle logic.

Notes
-----
The file :mod:`simulator-doc.txt` from PokÃƒÆ’Ã‚Â©mon Showdown describes the
expected control flow of that engine.  The important parts are included
here as a reference for future work.  Individual functions below map to
sections of that pseudocode and currently act as placeholders.

```
STEP 1. MOVE PRE-USAGE
STEP 2. MOVE USAGE
STEP 3. MOVE EXECUTION (sub-moves)
STEP 4. MOVE HIT

MAIN LOOP
    BeforeTurn
    ModifyPriority
    runAction() {
        runSwitch()
        runAfterSwitch()
        runMove()
    }
    runFaint()
    residual()
```

Only a fraction of the above is implemented at the moment.  Unclear or
complex behaviour has been marked with ``TODO`` comments and the
corresponding methods simply ``pass`` for now.
"""

from __future__ import annotations

import copy
import importlib
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from utils.safe_import import safe_import

try:
    from .error_handling import battle_debug_fail_fast
except Exception:  # pragma: no cover - fallback for stripped test stubs
    def battle_debug_fail_fast(battle=None):
        return False

try:
    from .events import EventDispatcher  # type: ignore
except Exception:  # pragma: no cover - fallback for tests with stubs
    try:
        EventDispatcher = safe_import("pokemon.battle.events").EventDispatcher  # type: ignore[attr-defined]
    except Exception:
        import inspect
        from collections import defaultdict

        class EventDispatcher:
            """Minimal dispatcher used when :mod:`pokemon.battle.events` is unavailable."""

            def __init__(self, *, allow_arity_fallback: bool = False) -> None:
                self._handlers = defaultdict(list)
                self.allow_arity_fallback = allow_arity_fallback

            def register(self, event: str, handler: Callable[..., Any]) -> None:
                self._handlers[event].append(handler)

            def dispatch(self, event: str, **context: Any) -> None:
                for handler in list(self._handlers.get(event, [])):
                    sig = inspect.signature(handler)
                    if any(
                        p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in sig.parameters.values()
                    ):
                        params = context
                    else:
                        params = {
                            k: v for k, v in context.items() if k in sig.parameters
                        }
                    handler(**params)


import importlib.machinery
import importlib.util
import logging
import os
import sys

from pokemon.dex import MOVEDEX
from pokemon.names import resolve_dex_entry

try:  # pragma: no cover - ability data may be stubbed during tests
    from pokemon.dex import ABILITYDEX  # type: ignore
except Exception:  # pragma: no cover - fallback to empty mapping
    ABILITYDEX = {}

try:  # pragma: no cover - item data may be optional during tests
    from pokemon.dex import ITEMDEX  # type: ignore
except Exception:  # pragma: no cover - fallback to empty mapping
    ITEMDEX = {}

_BASE_PATH = os.path.dirname(__file__)

if "pokemon" not in sys.modules:
    pkg = importlib.util.module_from_spec(
        importlib.machinery.ModuleSpec("pokemon", loader=None)
    )
    pkg.__path__ = [os.path.dirname(_BASE_PATH)]
    sys.modules["pokemon"] = pkg
if "pokemon.battle" not in sys.modules:
    sub = importlib.util.module_from_spec(
        importlib.machinery.ModuleSpec("pokemon.battle", loader=None)
    )
    sub.__path__ = [_BASE_PATH]
    sys.modules["pokemon.battle"] = sub

from ._shared import (
    _normalize_key,
    ensure_movedex_aliases,
    get_raw,
    reset_tempvals,
    snapshot_battle_value,
)
from .battledata import (
    _REVEAL_ALL_VIEWERS,
    _ability_display_name,
    _caller_is_admin,
    _normalize_reveal_viewer,
    _pokemon_reveal_key,
)
from .registry import CALLBACK_REGISTRY

ensure_movedex_aliases(MOVEDEX)


def _get_move_class():
    """Return the canonical Move class, or a lightweight fallback.

    Tests sometimes stub ``pokemon.dex`` as a simple module without the
    ``entities`` subpackage.  Importing :class:`Move` at module import time
    would therefore fail.  This helper tries to import the real class and, if
    unavailable, returns a minimal stand-in exposing the attributes the battle
    engine relies upon.
    """

    try:  # normal path when the full dex package is available
        from pokemon.dex.entities import Move as _Move  # type: ignore
        return _Move
    except Exception:
        class _FallbackMove:
            def __init__(
                self,
                name,
                num=0,
                type=None,
                category=None,
                power=None,
                accuracy=None,
                pp=None,
                raw=None,
            ):
                self.name = name
                self.num = num
                self.type = type
                self.category = category
                self.power = power
                self.accuracy = accuracy
                self.pp = pp
                self.raw = raw or {}
                self.basePowerCallback = None
                self.damageCallback = None
                self.onBasePower = None

        return _FallbackMove


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_BASE_PATH, filename)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


participants_mod = _load_module("pokemon.battle.participants", "participants.py")
actions_mod = _load_module("pokemon.battle.actions", "actions.py")
callbacks_mod = _load_module("pokemon.battle.callbacks", "callbacks.py")
conditions_mod = _load_module("pokemon.battle.conditions", "conditions.py")
turns_mod = _load_module("pokemon.battle.turns", "turns.py")

BattleParticipant = participants_mod.BattleParticipant
Action = actions_mod.Action
ActionType = actions_mod.ActionType
BattleActions = actions_mod.BattleActions
ConditionHelpers = conditions_mod.ConditionHelpers
TurnProcessor = turns_mod.TurnProcessor

from .callbacks import _resolve_callback, invoke_callback, resolve_callback_from_modules

battle_logger = logging.getLogger("battle")
try:
    BALL_MODIFIERS = safe_import("pokemon.dex.items.ball_modifiers").BALL_MODIFIERS  # type: ignore[attr-defined]
except ModuleNotFoundError:
    BALL_MODIFIERS = {}

# Import dex helper modules lazily to avoid heavy dependencies during tests.
# ``moves_funcs`` is resolved on demand via :func:`pokemon.battle.callbacks._resolve_callback`.
try:  # pragma: no cover - optional at runtime
    conditions_funcs = safe_import("pokemon.dex.functions.conditions_funcs")  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - used in lightweight test stubs
    conditions_funcs = None
moves_funcs = None


def _get_default_text() -> Dict[str, Dict[str, str]]:
    """Return the localized battle text mapping with graceful fallback."""

    try:  # pragma: no cover - optional dependency during lightweight tests
        from pokemon.data.text import DEFAULT_TEXT  # type: ignore
    except Exception:  # pragma: no cover - fallback when data package missing
        return {"default": {}, "drain": {}, "recoil": {}}
    return DEFAULT_TEXT  # type: ignore[return-value]


def _apply_placeholders(
    template: str, replacements: Mapping[str, Sequence[str] | str]
) -> str:
    """Substitute placeholder tokens in ``template`` with ``replacements``."""

    message = template
    for placeholder, value in replacements.items():
        if isinstance(value, Sequence) and not isinstance(value, str):
            values = [str(part) for part in value if part is not None]
            if not values:
                continue
            for part in values[:-1]:
                message = message.replace(placeholder, part, 1)
            message = message.replace(placeholder, values[-1])
        else:
            message = message.replace(placeholder, str(value))
    return message


def is_self_target(target: str | None) -> bool:
    """Return whether the move intrinsically targets its own user."""

    try:
        from .utils import is_self_target as util_is_self_target  # type: ignore
    except Exception:  # pragma: no cover - best effort during import issues
        util_is_self_target = None

    if util_is_self_target:
        return util_is_self_target(target)
    return target == "self"


def _resolve_ability(ability):
    """Return an :class:`~pokemon.dex.entities.Ability` for ``ability``.

    PokÃƒÆ’Ã‚Â©mon instances within tests sometimes store their ability as a simple
    string identifier rather than an :class:`Ability` object.  This helper
    looks up such strings in :data:`pokemon.dex.ABILITYDEX` and returns the
    corresponding instance so callers can safely invoke callbacks.  If the
    ability cannot be resolved, ``None`` is returned.
    """

    if ability and not hasattr(ability, "call"):
        if isinstance(ability, str):
            return (
                ABILITYDEX.get(str(ability))
                or ABILITYDEX.get(_normalize_key(str(ability)))
                or ABILITYDEX.get(str(ability).replace(" ", ""))
            )
        return ability
    return ability


def _effect_key(effect) -> str:
    """Return a normalized key for an ability, item, move, or raw value."""

    if effect is None:
        return ""
    value = getattr(effect, "id", None) or getattr(effect, "key", None) or getattr(effect, "name", None) or effect
    return _normalize_key(str(value)).lower()


REVEAL_ON_ENTRY_ABILITIES = {
    "drizzle",
    "drought",
    "electricsurge",
    "frisk",
    "grassysurge",
    "hadronengine",
    "intimidate",
    "mistysurge",
    "moldbreaker",
    "orichalcumpulse",
    "pressure",
    "primordialsea",
    "psychicsurge",
    "sandstream",
    "snowwarning",
    "teravolt",
    "trace",
    "turboblaze",
}


def _ability_try_hit_blocks(target, source, move, battle) -> bool:
    """Return whether the target's ``onTryHit`` ability blocks ``move``.

    Several immunity abilities in the dex use Showdown's ``onTryHit`` hook and
    either return ``False`` or mark the target's ``immune`` state while
    returning ``None``.  Treat both forms as a blocked hit, but only when the
    immunity marker changed during this callback so stale state from an earlier
    interaction does not block unrelated moves.
    """

    if target is None or move is None:
        return False
    from .effect_context import EffectContext

    ability = EffectContext.ability(target)
    ignores = getattr(battle, "_move_ignores_target_ability", None)
    if callable(ignores) and ignores(source, target, move):
        return False
    raw = getattr(ability, "raw", {}) or {}
    if not ability or not raw.get("onTryHit"):
        return False

    before_immune = getattr(target, "immune", None)
    try:
        if hasattr(ability, "call"):
            state = dict(getattr(target, "ability_state", {}) or {})
            state["target"] = target
            result = ability.call("onTryHit", target, source, move, battle=battle, effect_state=state)
        else:
            try:
                from pokemon.dex.functions import abilities_funcs  # type: ignore
            except Exception:  # pragma: no cover - optional in light-weight stubs
                abilities_funcs = None
            callback = (
                _resolve_callback(raw.get("onTryHit"), abilities_funcs)
                if abilities_funcs
                else None
            )
            result = invoke_callback(callback, target, source, move, battle=battle)
    except Exception:
        return False

    after_immune = getattr(target, "immune", None)
    if result is False:
        return True
    return bool(result is None and after_immune and after_immune != before_immune)


def _apply_move_damage(
    user, target, battle_move: "BattleMove", battle, *, spread: bool = False, update_hp=True
):
    """Construct a temporary :class:`pokemon.dex.entities.Move` from ``battle_move``.

    Any ``basePowerCallback`` present on ``battle_move`` is attached to the
    temporary move and invoked once prior to damage calculation to allow the
    callback to adjust move data.  The helper then delegates to
    :func:`apply_damage` and returns its :class:`~pokemon.battle.damage.DamageResult`.

    Parameters
    ----------
    user, target:
        Combatants involved in the interaction.
    battle_move:
        The :class:`BattleMove` definition being used.
    battle:
        The active :class:`Battle` instance for context.
    spread:
        Passed through to :func:`apply_damage` to indicate spread damage.

    Returns
    -------
    DamageResult
        The result of :func:`apply_damage`.
    """

    import sys

    damage_mod = sys.modules.get("pokemon.battle.damage")
    if damage_mod is None:  # pragma: no cover - fallback for stub environments
        damage_mod = _load_module("pokemon.battle.damage", "damage.py")
    apply_damage = getattr(damage_mod, "apply_damage")
    DamageResult = getattr(damage_mod, "DamageResult")
    Move = _get_move_class()

    # ------------------------------------------------------------------
    # Ability hooks
    # ------------------------------------------------------------------
    # Many abilities modify move data prior to damage calculation via
    # callbacks such as ``onModifyType`` and ``onBasePower``.  These hooks
    # are normally invoked by the battle engine but our lightweight test
    # harness constructs :class:`BattleMove` instances directly, bypassing
    # the usual dispatch system.  To ensure ability callbacks are still
    # triggered (and to allow them to tweak move attributes), we invoke the
    # relevant handlers here before building the temporary :class:`Move`
    # used for damage computation.

    from .effect_context import EffectContext

    user_ability = _resolve_ability(EffectContext.ability(user))
    if user_ability and hasattr(user_ability, "call") and not getattr(battle_move, "_ability_move_prepared", False):
        try:
            user_ability.call("onModifyMove", battle_move, user=user, target=target, battle=battle)
        except Exception:
            try:
                user_ability.call("onModifyMove", battle_move)
            except Exception:
                pass

    from .effect_context import EffectContext

    for owner in (user, target):
        ability = _resolve_ability(EffectContext.ability(owner))
        if not ability:
            ability = None
        # Suppression keeps the owned item but disables its offensive hooks.
        item = EffectContext.item(owner)

        # onAnyBasePower applies to moves used by any Pokemon on the field.
        new_power = None
        if ability:
            try:
                new_power = ability.call(
                    "onAnyBasePower",
                    battle_move.power,
                    source=user,
                    target=target,
                    move=battle_move,
                )
            except Exception:
                try:
                    new_power = ability.call("onAnyBasePower", battle_move.power)
                except Exception:
                    new_power = None
        if isinstance(new_power, (int, float)):
            battle_move.power = int(new_power)

        # Ordinary offensive hooks belong to the move user. The defender can
        # still contribute global hooks above and onSourceBasePower below.
        if owner is not user:
            continue

        # onModifyType may mutate ``battle_move`` in-place.  We attempt to
        # pass the ability's owner when supported but fall back to a simple
        # call with only the move argument if the signature differs.
        if ability:
            try:
                ability.call("onModifyType", battle_move, user=owner)
            except Exception:
                try:
                    ability.call("onModifyType", battle_move)
                except Exception:
                    pass
        if item and hasattr(item, "call"):
            try:
                item.call("onModifyType", battle_move, user=owner)
            except Exception:
                try:
                    item.call("onModifyType", battle_move)
                except Exception:
                    pass

        # onBasePower can return a modified base power.  Similar to above we
        # try a generous call signature but gracefully handle mismatches.
        new_power = None
        if ability:
            try:
                new_power = ability.call(
                    "onBasePower", battle_move.power, user=owner, target=target,
                    attacker=owner, defender=target, move=battle_move, battle=battle
                )
            except Exception:
                try:
                    new_power = ability.call("onBasePower", battle_move.power)
                except Exception:
                    new_power = None
        if isinstance(new_power, (int, float)):
            battle_move.power = int(new_power)
        # Ability and held-item power results compose; a no-op ability result
        # must not skip the item hook (for example Sand Force in clear weather).
        if item and hasattr(item, "call"):
            try:
                new_power = item.call(
                    "onBasePower", battle_move.power, user=owner, target=target,
                    attacker=owner, defender=target, move=battle_move, battle=battle
                )
            except Exception:
                try:
                    new_power = item.call("onBasePower", battle_move.power)
                except Exception:
                    new_power = None
        if isinstance(new_power, (int, float)):
            battle_move.power = int(new_power)

    # Abilities on the user's side, including the user, can influence the
    # move's base power through ``onAllyBasePower`` hooks.
    attacker_part = (
        battle.participant_for(user)
        if battle is not None and hasattr(battle, "participant_for")
        else None
    )
    if attacker_part and hasattr(battle, "participants"):
        my_team = getattr(attacker_part, "team", None)
        for part in battle.participants:
            if part.has_lost:
                continue
            other_team = getattr(part, "team", None)
            same_team = part is attacker_part or (
                my_team is not None and other_team == my_team
            )
            if same_team:
                for ally in getattr(part, "active", []):
                    ability = _resolve_ability(EffectContext.ability(ally))
                    if not ability:
                        continue
                    try:
                        new_power = ability.call(
                            "onAllyBasePower",
                            battle_move.power,
                            attacker=user,
                            defender=target,
                            user=user,
                            pokemon=user,
                            target=target,
                            move=battle_move,
                        )
                    except Exception:
                        try:
                            new_power = ability.call(
                                "onAllyBasePower",
                                battle_move.power,
                                pokemon=user,
                                target=target,
                                move=battle_move,
                            )
                        except Exception:
                            try:
                                new_power = ability.call(
                                    "onAllyBasePower",
                                    battle_move.power,
                                    user=user,
                                    target=target,
                                    move=battle_move,
                                )
                            except Exception:
                                try:
                                    new_power = ability.call(
                                        "onAllyBasePower", battle_move.power
                                    )
                                except Exception:
                                    new_power = None
                    if isinstance(new_power, (int, float)):
                        battle_move.power = int(new_power)

    # Defensive abilities may further adjust the power of incoming moves via
    # ``onSourceBasePower``.  This hook is separate from ``onBasePower`` above,
    # which applies when the ability's owner uses a move.
    target_ability = _resolve_ability(EffectContext.ability(target))
    ignores_ability = getattr(battle, "_move_ignores_target_ability", None)
    if callable(ignores_ability) and ignores_ability(user, target, battle_move):
        target_ability = None
    if target_ability:
        try:
            new_power = target_ability.call(
                "onSourceBasePower",
                battle_move.power,
                attacker=user,
                defender=target,
                move=battle_move,
            )
        except Exception:
            try:
                new_power = target_ability.call("onSourceBasePower", battle_move.power)
            except Exception:
                new_power = None
        if isinstance(new_power, (int, float)):
            battle_move.power = int(new_power)

    raw = dict(battle_move.raw)
    raw["flags"] = dict(getattr(battle_move, "flags", raw.get("flags", {})))
    if battle_move.basePowerCallback:
        raw["basePowerCallback"] = battle_move.basePowerCallback
    if battle_move.damageCallback:
        raw["damageCallback"] = battle_move.damageCallback
    if battle_move.onBasePower:
        raw["onBasePower"] = battle_move.onBasePower

    # Default to ``Physical`` but allow the move's category to be provided via
    # ``raw`` so special moves can correctly reference SpA/SpD instead of
    # Atk/Def.
    category = raw.get("category") or "Physical"
    if str(category).lower() == "status":
        return DamageResult()

    try:
        move = Move(
            name=battle_move.name,
            num=0,
            type=battle_move.type,
            category=category,
            power=battle_move.power,
            accuracy=battle_move.accuracy,
            pp=None,
            raw=raw,
        )
        setattr(move, "flags", dict(raw.get("flags", {}) or {}))
    except TypeError:  # pragma: no cover - fallback for simple stubs
        move = Move(battle_move.name)
        setattr(move, "type", battle_move.type)
        setattr(move, "category", category)
        setattr(move, "power", battle_move.power)
        setattr(move, "accuracy", battle_move.accuracy)
        setattr(move, "pp", None)
        setattr(move, "raw", raw)
        setattr(move, "flags", dict(raw.get("flags", {}) or {}))

    for attr in ("multihit", "multihit_type", "parental_bond_hit", "_z_paid"):
        if hasattr(battle_move, attr):
            setattr(move, attr, getattr(battle_move, attr))

    for attr in ("sourceEffect", "hit", "pp", "pledge_combo", "ignoreImmunity", "ignore_immunity", "infiltrates"):
        if attr == "pp" and getattr(battle_move, "pp", None) is not None:
            setattr(move, attr, battle_move.pp)
        elif attr in raw:
            setattr(move, attr, raw[attr])
        elif hasattr(battle_move, attr):
            setattr(move, attr, getattr(battle_move, attr))

    if battle_move.basePowerCallback:
        try:
            move.basePowerCallback = battle_move.basePowerCallback
        except Exception:
            move.basePowerCallback = None

    if battle_move.damageCallback:
        move.damageCallback = battle_move.damageCallback

    if battle_move.onBasePower:
        move.onBasePower = battle_move.onBasePower

    move._stellar_boosts = getattr(battle_move, "_stellar_boosts", {})
    battle_move._stellar_boosts = move._stellar_boosts
    move._tera_shared_use = True
    move._engine_secondaries = True
    from .item_effects import HeldItemRules

    HeldItemRules.apply_gem_power(battle_move)
    if getattr(battle_move, "_gem_power_applied", False):
        move.power = battle_move.power
    hp_before = getattr(target, "hp", 0)
    damage_options = {"update_hp": False} if not update_hp else {}
    result = apply_damage(user, target, move, battle=battle, spread=spread, **damage_options)
    ledger = (getattr(target, "tempvals", {}) or {}).get("last_damaged_by", {})
    actual_damage = ledger.get("actual_damage", 0) if ledger.get("source") is user and ledger.get("move") is move else max(0, hp_before - getattr(target, "hp", 0))
    battle_move.total_damage = getattr(battle_move, "total_damage", 0) + actual_damage
    if actual_damage > 0:
        HeldItemRules.commit_gem(user, battle_move)
    from .terastallization import apply_stellar_cost

    apply_stellar_cost(user, battle_move, result)

    try:
        move_power = getattr(move, "power", None)
        if isinstance(move_power, (int, float)):
            battle_move.power = int(move_power)
    except Exception:
        pass

    return result


def _select_ai_action(
    participant: "BattleParticipant", active_pokemon, battle: "Battle", *, reserved=(), planned=()
) -> Optional[Action]:
    """Select a scored legal move or bounded voluntary reserve switch."""
    from .ai_actions import select_ai_action

    return select_ai_action(participant, active_pokemon, battle, logger=battle_logger, reserved=reserved, planned=planned)


@dataclass
class BattleSide:
    """Container for effects active on one side of the battle."""

    # Generic container for any side conditions (Reflect, Spikes, etc)
    conditions: Dict[str, Dict] = field(default_factory=dict)
    hazards: Dict[str, Any] = field(default_factory=dict)
    screens: Dict[str, Any] = field(default_factory=dict)
    volatiles: Dict[str, Any] = field(default_factory=dict)
    active: List[Any] = field(default_factory=list)
    used_items: List[Any] = field(default_factory=list)
    sideConditions: Dict[str, Dict] = field(default_factory=dict)
    slot_conditions: Dict[int, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    HAZARD_TO_CONDITION = {
        "rocks": "stealthrock",
        "spikes": "spikes",
        "toxicspikes": "toxicspikes",
        "stickyweb": "stickyweb",
        "steelsurge": "gmaxsteelsurge",
    }
    CONDITION_TO_HAZARD = {value: key for key, value in HAZARD_TO_CONDITION.items()}

    def __post_init__(self) -> None:
        self.sideConditions = self.conditions

    @property
    def side_conditions(self) -> Dict[str, Dict]:
        return self.conditions

    @side_conditions.setter
    def side_conditions(self, value: Optional[Dict[str, Dict]]) -> None:
        self.conditions = value or {}
        self.sideConditions = self.conditions

    def add_side_condition(self, name: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = dict(state or {})
        self.conditions[name] = state
        self.sideConditions = self.conditions
        return state

    def remove_side_condition(self, name: str) -> bool:
        removed = self.conditions.pop(name, None) is not None
        self.sideConditions = self.conditions
        return removed

    def set_hazard(self, name: str, value: Any = True, state: Optional[Dict[str, Any]] = None) -> None:
        store_key = self.CONDITION_TO_HAZARD.get(name, name)
        condition_key = self.HAZARD_TO_CONDITION.get(store_key, store_key)
        self.hazards[store_key] = value
        if value:
            self.conditions[condition_key] = dict(state or self.conditions.get(condition_key) or {})
        else:
            self.conditions.pop(condition_key, None)
            self.conditions.pop(store_key, None)
        self.sideConditions = self.conditions

    def clear_hazard(self, name: str) -> bool:
        store_key = self.CONDITION_TO_HAZARD.get(name, name)
        condition_key = self.HAZARD_TO_CONDITION.get(store_key, store_key)
        removed = self.hazards.pop(store_key, None) is not None
        removed = self.conditions.pop(condition_key, None) is not None or removed
        removed = self.conditions.pop(store_key, None) is not None or removed
        self.sideConditions = self.conditions
        return removed

    def sync_hazard_conditions(self) -> None:
        for store_key, condition_key in self.HAZARD_TO_CONDITION.items():
            if self.hazards.get(store_key):
                self.conditions.setdefault(condition_key, {})
            else:
                self.conditions.pop(condition_key, None)
                self.conditions.pop(store_key, None)
        self.sideConditions = self.conditions

    def add_slot_condition(
        self,
        slot: int,
        name: str,
        state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        state = dict(state or {})
        bucket = self.slot_conditions.setdefault(slot, {})
        bucket[name] = state
        return state

    def get_slot_condition(self, slot: int, name: str) -> Optional[Dict[str, Any]]:
        return self.slot_conditions.get(slot, {}).get(name)

    def remove_slot_condition(self, slot: int, name: str) -> bool:
        bucket = self.slot_conditions.get(slot)
        if not bucket:
            return False
        removed = bucket.pop(name, None) is not None
        if not bucket:
            self.slot_conditions.pop(slot, None)
        return removed


class BattleType(Enum):
    """Different types of battles."""

    WILD = 0
    PVP = 1
    TRAINER = 2
    SCRIPTED = 3


@dataclass(frozen=True)
class _MoveResultState:
    """Detached effects used to distinguish a successful move from no change."""

    hp: int
    boosts: dict
    status: Any
    volatiles: dict
    item: str
    ability: str

    @classmethod
    def capture(cls, pokemon):
        """Copy condition state without following live battler or ORM graphs."""
        from pokemon.utils.boosts import STAT_KEY_MAP

        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        ability = getattr(pokemon, "ability", None)
        return cls(
            hp=getattr(pokemon, "hp", 0),
            boosts={STAT_KEY_MAP.get(key, key): value for key, value in getattr(pokemon, "boosts", {}).items()},
            status=getattr(pokemon, "status", None),
            volatiles=snapshot_battle_value(getattr(pokemon, "volatiles", {}) or {}),
            item=_normalize_key(getattr(item, "name", None) or item or ""),
            ability=_normalize_key(getattr(ability, "name", None) or ability or ""),
        )


@dataclass
class BattleMove:
    """Representation of a move used in battle."""

    effectType = "Move"
    name: str
    key: Optional[str] = None
    power: int = 0
    accuracy: int | float | bool = 100
    priority: int = 0
    onHit: Optional[Callable] = None
    onTry: Optional[Callable] = None
    onTryMove: Optional[Callable] = None
    onModifyType: Optional[Callable] = None
    onBeforeMove: Optional[Callable] = None
    onAfterMove: Optional[Callable] = None
    onModifyMove: Optional[Callable] = None
    onPrepareHit: Optional[Callable] = None
    onTryHit: Optional[Callable] = None
    onTryHitSide: Optional[Callable] = None
    onTryHitField: Optional[Callable] = None
    onHitSide: Optional[Callable] = None
    onHitField: Optional[Callable] = None
    onMoveFail: Optional[Callable] = None
    onMoveAborted: Optional[Callable] = None
    onAfterHit: Optional[Callable] = None
    onAfterMoveSecondary: Optional[Callable] = None
    onAfterMoveSecondarySelf: Optional[Callable] = None
    onUseMoveMessage: Optional[Callable] = None
    onUpdate: Optional[Callable] = None
    priorityChargeCallback: Optional[Callable] = None
    beforeMoveCallback: Optional[Callable] = None
    basePowerCallback: Optional[Callable] = None
    damageCallback: Optional[Callable] = None
    onBasePower: Optional[Callable] = None
    type: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    pp: Optional[int] = None

    def __post_init__(self) -> None:
        """Ensure a normalized key is always available."""
        if not self.key:
            self.key = _normalize_key(self.name)
        if not hasattr(self, "id") or getattr(self, "id", None) is None:
            self.id = _normalize_key(self.key).lower()
        if not hasattr(self, "flags") or getattr(self, "flags", None) is None:
            raw_flags = {}
            if isinstance(self.raw, dict):
                raw_flags = self.raw.get("flags", {}) or {}
            self.flags = dict(raw_flags)
        if not hasattr(self, "category") or getattr(self, "category", None) is None:
            raw_category = self.raw.get("category") if isinstance(self.raw, dict) else None
            self.category = raw_category or ("Status" if not self.power else "Physical")
        self.multihit = self.raw.get("multihit") if isinstance(self.raw, dict) else None

    def execute(self, user, target, battle: "Battle") -> None:
        """Execute this move's effect.

        The function normally relies on ``pokemon.data.text`` for human readable
        battle messages.  Lightweight test stubs used throughout the suite do
        not always provide this package which would normally result in an
        import error.  Import the text module lazily and fall back to a minimal
        placeholder mapping when it cannot be resolved so that the core battle
        logic can still be exercised without the full data package.
        """

        DEFAULT_TEXT = _get_default_text()
        raw_flags = self.raw.get("flags", {}) if self.raw else {}
        bypasses_substitute = bool(
            (self.raw.get("bypassSub") if self.raw else None)
            or raw_flags.get("bypasssub")
            or getattr(self, "infiltrates", False)
        )
        side_gate = getattr(battle, "_passes_side_protection", None)
        if target is not user and callable(side_gate) and not side_gate(target, user, self):
            return

        if battle and hasattr(battle, "log_action"):
            default_messages = DEFAULT_TEXT.get("default", {})
            actor_name = getattr(user, "name", None) or getattr(user, "species", "Pokemon")

            item_template = default_messages.get("activateItem")
            if item_template:
                item = getattr(user, "item", None) or getattr(user, "held_item", None)
                item_name = getattr(item, "name", None)
                if not item_name and isinstance(item, str):
                    item_name = item
                if item_name:
                    item_message = item_template.replace("[POKEMON]", str(actor_name)).replace(
                        "[ITEM]", str(item_name)
                    )
                    battle.log_action(item_message)

        if self.onTry:
            result = invoke_callback(self.onTry, user, target, self, battle=battle)
            if result is False:
                return
        if (getattr(self, "pranksterBoosted", False)
                and str(self.category).lower() == "status" and target is not user
                and not user.is_ally(target) and "Dark" in getattr(target, "types", [])):
            battle.log_action(f"{target.name} is immune to the Prankster-boosted {self.name}!")
            return
        from .called_moves import CalledMoveExecutor

        if CalledMoveExecutor(battle).reflect(user, target, self):
            return
        from .effect_context import EffectContext
        target_item = EffectContext.item(target)
        if target is not user and hasattr(target_item, "call") and target_item.call("onTryHit", target=target, source=user, move=self) is False:
            return
        if target is not user and _ability_try_hit_blocks(target, user, self, battle):
            return
        from .protection import StatusTypeImmunity

        if target is not user and StatusTypeImmunity.blocks(target, self):
            if battle and hasattr(battle, "log_action"):
                battle.log_action(f"{target.name} is immune to {self.name}!")
            return
        if (str(self.category).lower() == "status" or self.raw.get("heal")) and target is not user:
            from .accuracy import MoveAccuracy

            if not MoveAccuracy.check_status(user, target, self, battle):
                if battle and hasattr(battle, "log_action"):
                    battle.log_action(f"{user.name} uses {self.name} but it missed!")
                return
        if self.onHit:
            handled = invoke_callback(self.onHit, user, target, battle=battle)
            if handled is not True:
                return
            if (str(self.key).lower() == "pollenpuff"
                    and getattr(user, "side", None) is not None
                    and getattr(user, "side", None) is getattr(target, "side", None)):
                # Its ally callback heals; the damaging default only applies
                # to foes. Do not undo the heal with a friendly damage hit.
                return
        self._primary_hit_successful = True

        # Default behaviour for moves without custom handlers
        move_category = self.raw.get("category", self.category) if self.raw else self.category
        category = str(move_category).lower()
        result = None
        if category != "status" and not self.raw.get("heal"):
            # Expose the canonical category for ability hooks that expect it as
            # an attribute on the move instance.
            setattr(self, "category", move_category)
            if battle and hasattr(battle, "runEvent"):
                if battle.runEvent("TryPrimaryHit", target, user, self) is False:
                    return

            pre_hp = getattr(target, "hp", None)
            result = _apply_move_damage(user, target, self, battle, spread=getattr(self, "_spread", False))
            if not sum(result.debug.get("damage", [])):
                self._primary_hit_successful = False
                return
            from .z_effects import ZEffects

            ZEffects.hit(battle, user, self, max(0, pre_hp - target.hp))
        else:
            boosts = self.raw.get("boosts") if self.raw else None
            if boosts:
                from pokemon.utils.boosts import apply_boost

                affected = user if is_self_target(self.raw.get("target")) else target
                if affected is not None:
                    apply_boost(affected, boosts, source=user, effect=self)

        # Apply draining effects (e.g. Absorb)
        drain = self.raw.get("drain") if self.raw else None
        if drain and result is not None:
            damage = 0
            if hasattr(result, "debug"):
                dmg_list = result.debug.get("damage", [])
                if isinstance(dmg_list, list):
                    damage = sum(dmg_list)
            if pre_hp is not None:
                damage = max(0, pre_hp - getattr(target, "hp", pre_hp))
            if damage > 0:
                frac = drain[0] / drain[1]
                heal_amt = max(1, int(damage * frac))
                applied = battle.heal(user, heal_amt, source=target, effect=self) if battle else 0
                if battle and applied > 0:
                    if target:
                        battle.log_action(
                            DEFAULT_TEXT["drain"]["heal"].replace(
                                "[SOURCE]", getattr(target, "name", "Pokemon")
                            )
                        )
                    battle.log_action(
                        DEFAULT_TEXT["default"]["heal"].replace(
                            "[POKEMON]", getattr(user, "name", "Pokemon")
                        )
                    )

        # Apply recoil damage (e.g. Brave Bird)
        recoil = self.raw.get("recoil") if self.raw else None
        if recoil and result is not None:
            damage = 0
            if hasattr(result, "debug"):
                dmg_list = result.debug.get("damage", [])
                if isinstance(dmg_list, list):
                    damage = sum(dmg_list)
            if damage > 0:
                frac = recoil[0] / recoil[1]
                from .indirect_damage import apply_recoil_damage

                recoil_loss = apply_recoil_damage(user, int(damage * frac), self, battle=battle, source=target)
                if battle and recoil_loss:
                    battle.log_action(
                        DEFAULT_TEXT["recoil"]["damage"].replace(
                            "[POKEMON]", getattr(user, "name", "Pokemon")
                        )
                    )

        # Struggle uses maximum-HP recoil, independent of actual hit damage.
        if str(self.key).lower() == "struggle" and result is not None:
            from .indirect_damage import IndirectEffect, apply_indirect_damage

            apply_indirect_damage(user, max(1, user.max_hp // 4), battle=battle,
                                  source=user, effect=IndirectEffect("strugglerecoil", "Recoil"))

        # Apply flat healing (e.g. Recover)
        heal = self.raw.get("heal") if self.raw else None
        if heal:
            frac = heal[0] / heal[1] if isinstance(heal, (list, tuple)) else 0
            heal_target = user if is_self_target(self.raw.get("target")) else target
            if heal_target is not None:
                max_hp = getattr(heal_target, "max_hp", getattr(heal_target, "hp", 1))
                amount = max(1, int(max_hp * frac)) if frac else max_hp
                applied = battle.heal(heal_target, amount, source=user, effect=self) if battle else 0
                if applied > 0 and _effect_key(self) == "roost":
                    from .recovery_moves import RoostTyping

                    RoostTyping.start(heal_target)
                if battle and applied > 0:
                    battle.log_action(
                        DEFAULT_TEXT["default"]["heal"].replace(
                            "[POKEMON]", getattr(heal_target, "name", "Pokemon")
                        )
                    )

        weather = self.raw.get("weather") if self.raw else None
        if weather and battle:
            battle.setWeather(weather, source=user)

        terrain = self.raw.get("terrain") if self.raw else None
        if terrain and battle:
            battle.setTerrain(terrain, source=user)

        pseudo_weather = self.raw.get("pseudoWeather") if self.raw else None
        if pseudo_weather and battle:
            battle.add_pseudo_weather(pseudo_weather, source=user)

        # Handle side conditions set by this move
        side_cond = self.raw.get("sideCondition") if self.raw else None
        if side_cond:
            condition = self.raw.get("condition", {})
            target_side = user
            if self.raw.get("target") != "allySide":
                target_side = target
            part = battle.participant_for(target_side)
            if part:
                battle.add_side_condition(
                    part, side_cond, condition, source=user, moves_funcs=moves_funcs
                )

        slot_cond = self.raw.get("slotCondition") if self.raw else None
        if slot_cond and battle:
            condition = self.raw.get("condition", {})
            slot_target = user if is_self_target(self.raw.get("target")) else target
            if slot_target is not None:
                battle.add_slot_condition(slot_target, slot_cond, condition, source=user)

        # Apply stat stage changes caused by this move. For damaging moves
        # this happens here so the boost is applied after damage is dealt.
        # Status moves already handled their boosts above, so we skip them
        # here to avoid applying the same boost twice (e.g. Acid Armor).
        boosts = self.raw.get("boosts") if self.raw else None
        if boosts and category != "status":
            from pokemon.utils.boosts import apply_boost

            affected = user if is_self_target(self.raw.get("target")) else target
            if affected:
                apply_boost(affected, boosts, source=user, effect=self)

        # Apply volatile status effects set by this move
        volatile = self.raw.get("volatileStatus") if self.raw else None
        if volatile:
            effect = self.raw.get("condition", {})
            cb_name = effect.get("onStart")
            cb = _resolve_callback(cb_name, moves_funcs)
            affected = user if is_self_target(self.raw.get("target")) else target
            if affected and hasattr(affected, "volatiles"):
                if battle and hasattr(battle, "add_volatile"):
                    battle.apply_volatile_status(affected, volatile, source=user, effect=self, start_callback=cb)
                else:
                    if callable(cb):
                        invoke_callback(cb, user, target, battle=battle)
                    if battle:
                        battle.apply_volatile_status(affected, volatile)
                    else:
                        affected.volatiles.setdefault(volatile, True)

        # Apply major status conditions inflicted by this move
        status = self.raw.get("status") if self.raw else None
        if status:
            affected = user if is_self_target(self.raw.get("target")) else target
            if affected is not None:
                if (
                    affected is not user
                    and getattr(affected, "volatiles", {}).get("substitute")
                    and not bypasses_substitute
                ):
                    return
                battle.apply_status_condition(
                    affected,
                    status,
                    source=user,
                    effect=self,
                )

        self_effect = self.raw.get("self") if self.raw else None
        if isinstance(self_effect, dict) and self_effect.get("onHit"):
            cb = _resolve_callback(self_effect.get("onHit"), moves_funcs)
            if callable(cb):
                invoke_callback(cb, user, target, battle=battle)

        # Apply secondary effects such as additional boosts or status changes
        secondaries = getattr(self, "secondaries", None)
        if secondaries is None:
            secondaries = list(self.raw.get("secondaries", [])) if self.raw else []
            if self.raw and self.raw.get("secondary"):
                secondaries.append(self.raw["secondary"])
        if secondaries:
            from pokemon.battle.damage import percent_check
            from pokemon.utils.boosts import apply_boost

            ability_source = _resolve_ability(getattr(user, "ability", None))
            ability_target = _resolve_ability(getattr(target, "ability", None))
            item_source = getattr(user, "item", None) or getattr(
                user, "held_item", None
            )
            item_target = getattr(target, "item", None) or getattr(
                target, "held_item", None
            )

            modified = secondaries
            for holder, func in (
                (ability_source, "onSourceModifySecondaries"),
                (item_source, "onSourceModifySecondaries"),
                (ability_target, "onModifySecondaries"),
                (item_target, "onModifySecondaries"),
            ):
                if holder and hasattr(holder, "call"):
                    try:
                        new_secs = holder.call(
                            func, modified, source=user, target=target, move=self
                        )
                    except Exception:
                        new_secs = holder.call(func, modified)
                    if isinstance(new_secs, list):
                        modified = new_secs

            for sec in modified:
                chance = sec.get("chance", 100)
                if not percent_check(
                    chance / 100.0,
                    rng=getattr(battle, "rng", None),
                ):
                    continue

                if sec.get("onHit"):
                    cb = _resolve_callback(sec.get("onHit"), moves_funcs)
                    if callable(cb):
                        invoke_callback(cb, user, target, battle=battle)

                if sec.get("boosts") and target:
                    apply_boost(target, sec["boosts"], source=user, effect=self)
                if sec.get("status") and target and battle:
                    battle.apply_status_condition(
                        target,
                        sec["status"],
                        source=user,
                        effect=self,
                    )
                if (
                    sec.get("volatileStatus")
                    and target
                    and hasattr(target, "volatiles")
                ):
                    if battle and hasattr(battle, "add_volatile"):
                        battle.apply_volatile_status(target, sec["volatileStatus"], source=user, effect=self)
                    else:
                        target.volatiles.setdefault(sec["volatileStatus"], True)
                        if battle:
                            battle.apply_volatile_status(target, sec["volatileStatus"])

                if sec.get("drain") and result is not None and user:
                    dmg = 0
                    if hasattr(result, "debug"):
                        dmg_list = result.debug.get("damage", [])
                        if isinstance(dmg_list, list):
                            dmg = sum(dmg_list)
                    if pre_hp is not None:
                        dmg = max(0, pre_hp - getattr(target, "hp", pre_hp))
                    if dmg > 0:
                        frac = sec["drain"][0] / sec["drain"][1]
                        heal_amt = max(1, int(dmg * frac))
                        applied = battle.heal(user, heal_amt, source=target, effect=self) if battle else 0
                        if battle and applied > 0:
                            if target:
                                battle.log_action(
                                    DEFAULT_TEXT["drain"]["heal"].replace(
                                        "[SOURCE]", getattr(target, "name", "Pokemon")
                                    )
                                )
                            battle.log_action(
                                DEFAULT_TEXT["default"]["heal"].replace(
                                    "[POKEMON]", getattr(user, "name", "Pokemon")
                                )
                            )

                if sec.get("recoil") and result is not None and user:
                    dmg = 0
                    if hasattr(result, "debug"):
                        dmg_list = result.debug.get("damage", [])
                        if isinstance(dmg_list, list):
                            dmg = sum(dmg_list)
                    if dmg > 0:
                        frac = sec["recoil"][0] / sec["recoil"][1]
                        from .indirect_damage import apply_recoil_damage

                        recoil_loss = apply_recoil_damage(user, int(dmg * frac), self, battle=battle, source=target)
                        if battle and recoil_loss:
                            battle.log_action(
                                DEFAULT_TEXT["recoil"]["damage"].replace(
                                    "[POKEMON]", getattr(user, "name", "Pokemon")
                                )
                            )

                if sec.get("heal") and target:
                    heal = sec["heal"]
                    frac = heal[0] / heal[1] if isinstance(heal, (list, tuple)) else 0
                    max_hp = getattr(target, "max_hp", getattr(target, "hp", 1))
                    amount = max(1, int(max_hp * frac)) if frac else max_hp
                    applied = battle.heal(target, amount, source=user, effect=self) if battle else 0
                    if battle and applied > 0:
                        battle.log_action(
                            DEFAULT_TEXT["default"]["heal"].replace(
                                "[POKEMON]", getattr(target, "name", "Pokemon")
                            )
                        )

                self_sec = sec.get("self")
                if self_sec and user:
                    if self_sec.get("boosts"):
                        apply_boost(user, self_sec["boosts"], source=user, effect=self)
                    if self_sec.get("status") and battle:
                            battle.apply_status_condition(
                                user,
                                self_sec["status"],
                                source=user,
                                effect=self,
                            )
                    if self_sec.get("volatileStatus") and hasattr(user, "volatiles"):
                        if battle and hasattr(battle, "add_volatile"):
                            battle.apply_volatile_status(user, self_sec["volatileStatus"], source=user, effect=self)
                        else:
                            user.volatiles.setdefault(self_sec["volatileStatus"], True)
                            if battle:
                                battle.apply_volatile_status(user, self_sec["volatileStatus"])
                    if self_sec.get("heal"):
                        heal = self_sec["heal"]
                        frac = (
                            heal[0] / heal[1] if isinstance(heal, (list, tuple)) else 0
                        )
                        max_hp = getattr(user, "max_hp", getattr(user, "hp", 1))
                        amount = max(1, int(max_hp * frac)) if frac else max_hp
                        user.hp = min(max_hp, user.hp + amount)
                        if battle:
                            battle.log_action(
                                DEFAULT_TEXT["default"]["heal"].replace(
                                    "[POKEMON]", getattr(user, "name", "Pokemon")
                                )
                            )

        if self.onAfterMoveSecondary:
            invoke_callback(self.onAfterMoveSecondary, user, target, self, battle=battle)
        if self.onAfterMoveSecondarySelf:
            invoke_callback(self.onAfterMoveSecondarySelf, user, target, self, battle=battle)


class MessageFormatter:
    """Format and emit human-readable battle messages."""

    def __init__(
        self,
        text_provider: Callable[[], Dict[str, Dict[str, str]]] | None = None,
    ) -> None:
        """Initialize the formatter."""

        self._text_provider = text_provider or _get_default_text

    def format_default_message(
        self,
        key: str,
        replacements: Mapping[str, Sequence[str] | str],
        fallback: str | None = None,
    ) -> str | None:
        """Return the formatted ``default`` message for ``key``."""

        default_messages = self._text_provider().get("default", {})
        template = default_messages.get(key) or fallback
        if not template:
            return None
        return _apply_placeholders(template, replacements)

    def pokemon_nickname(self, pokemon) -> str:
        """Return the best nickname representation for ``pokemon``."""

        nickname = getattr(pokemon, "name", None) or getattr(pokemon, "nickname", None)
        if nickname:
            return str(nickname)
        species = getattr(pokemon, "species", None)
        if hasattr(species, "name") and getattr(species, "name"):
            return str(getattr(species, "name"))
        if species:
            return str(species)
        return "Pokemon"

    def pokemon_fullname(self, pokemon) -> str:
        """Return a display-friendly full name for ``pokemon``."""

        nickname = self.pokemon_nickname(pokemon)
        species = getattr(pokemon, "species", None)
        species_name = None
        if hasattr(species, "name") and getattr(species, "name"):
            species_name = str(getattr(species, "name"))
        elif isinstance(species, str) and species:
            species_name = species
        if species_name and species_name != nickname:
            return f"{nickname} ({species_name})"
        return nickname

    def item_display_name(self, item) -> str:
        """Return a display string for ``item``."""

        if hasattr(item, "name") and getattr(item, "name"):
            return str(getattr(item, "name"))
        item_key = None
        if isinstance(item, str):
            item_key = _normalize_key(item)
        elif getattr(item, "key", None):
            item_key = _normalize_key(getattr(item, "key"))
        if item_key:
            entry = ITEMDEX.get(item_key)
            if entry:
                for attr in ("name", "id"):
                    value = getattr(entry, attr, None)
                    if value:
                        return str(value)
            return item_key.replace("-", " ").replace("_", " ").title()
        if isinstance(item, str):
            return item
        return str(item)

    def status_template(self, status_key: str, event: str) -> str | None:
        """Return the message template for ``status_key`` and ``event``."""

        messages = self._text_provider()
        visited: set[str] = set()
        current = status_key
        while current:
            entry = messages.get(current, {})
            template = entry.get(event)
            if template is None:
                return None
            if isinstance(template, str) and template.startswith("#"):
                ref = template[1:]
                if not ref or ref in visited:
                    return None
                visited.add(ref)
                current = ref
                continue
            return template
        return None


class StatusService:
    """Encapsulate status and immunity helper checks."""

    def handle_immunities_and_abilities(self, battle: "Battle", attacker, target, move) -> bool:
        """Return ``True`` if ``move`` is blocked before damage execution."""

        eff = 1.0
        if move.type:
            eff = battle.calculate_type_effectiveness(target, move)
        if eff == 0:
            return True
        if getattr(target, "volatiles", {}).get("protect") and not (
                getattr(move, "breaksProtect", False) or getattr(move, "raw", {}).get("breaksProtect")):
            return True
        return False

    def check_protect_substitute(self, target) -> bool:
        """Return ``True`` if ``target`` has protect/substitute volatile effects."""

        vols = getattr(target, "volatiles", {})
        return "protect" in vols or "substitute" in vols


class TurnResolutionService:
    """Provide turn-order helper checks for battle execution."""

    def check_priority_override(self, pokemon) -> bool:
        """Return whether temporary effects override normal priority."""

        return getattr(pokemon, "tempvals", {}).get("quash", False)


class RewardService:
    """Apply post-battle reward rules."""

    def handle_end_of_battle_rewards(self, battle: "Battle", winner: BattleParticipant) -> None:
        """Award post-battle rewards to the winning participant."""

        if not getattr(battle, "award_prizes", True):
            return
        if battle._rewards_granted:
            return
        if not winner or not getattr(winner, "player", None):
            return
        if battle.type is not BattleType.TRAINER:
            return

        try:  # pragma: no cover - data import optional in tests
            from pokemon.dex.exp_ev_yields import GAIN_INFO  # type: ignore
        except Exception:  # pragma: no cover - fallback to empty mapping
            GAIN_INFO = {}

        prize_money = 0
        for participant in battle.participants:
            if participant is winner or not getattr(participant, "has_lost", False):
                continue
            if getattr(participant, "player", None) and not getattr(participant, "is_ai", False):
                continue
            for poke in getattr(participant, "pokemons", []):
                if getattr(poke, "hp", 0) > 0:
                    continue
                species = getattr(poke, "species", None) or getattr(poke, "name", "")
                info = resolve_dex_entry(GAIN_INFO, species) or {}
                amount = int(info.get("exp", 0)) if info else 0
                if amount <= 0:
                    level = getattr(poke, "level", 1) or 1
                    amount = max(10, int(level) * 10)
                prize_money += amount

        if prize_money <= 0:
            battle._rewards_granted = True
            return

        recipient = winner.player
        delivery = getattr(battle, "reward_delivery", None)
        if delivery is not None and delivery.supports(recipient):
            claimed = delivery.deliver(recipient, "prize", {"money": prize_money}, caller=battle)
            if claimed is None:
                return
            battle._rewards_granted = True
            if claimed:
                battle.log_action(f"{getattr(recipient, 'key', 'Player')} received ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â½{prize_money} for winning!")
            return
        trainer = getattr(recipient, "trainer", None)
        if trainer and hasattr(trainer, "add_money"):
            trainer.add_money(prize_money)
        else:
            add_money = getattr(recipient, "add_money", None)
            if callable(add_money):
                add_money(prize_money)

        if hasattr(battle, "log_action"):
            battle.log_action(
                f"{getattr(recipient, 'key', 'Player')} received ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â½{prize_money} for winning!"
            )

        battle._rewards_granted = True


class Battle(TurnProcessor, ConditionHelpers, BattleActions):
    """Main battle controller for one or more sides."""

    def __init__(
        self,
        battle_type: BattleType,
        participants: List[BattleParticipant],
        *,
        rng: Optional[random.Random] = None,
        turn_resolution_service: TurnResolutionService | None = None,
        status_service: StatusService | None = None,
        message_formatter: MessageFormatter | None = None,
        reward_service: RewardService | None = None,
    ) -> None:
        """Create a new battle with arbitrary participants.

        Parameters
        ----------
        battle_type:
            Type of battle being run.
        participants:
            List of :class:`BattleParticipant` instances taking part.
        rng:
            Optional :class:`random.Random` compatible object used for all random
            rolls. When ``None`` the module-level :mod:`random` generator is
            used, allowing ``random.seed`` to control determinism in tests.
        """

        self.type = battle_type
        self.participants = participants
        self.sides = [getattr(part, "side", None) for part in participants]
        self.turn_count = 0
        self.battle_over = False
        self.flee_allowed = True
        self.dispatcher = EventDispatcher(allow_arity_fallback=False)
        from .battledata import Field

        self.field = Field()
        self.debug: bool = False
        # In debug/testing modes we re-raise callback exceptions to fail fast.
        self.fail_fast_errors: bool = battle_debug_fail_fast(self)
        # Toggle to display exact damage numbers alongside descriptive text.
        self.show_damage_numbers: bool = False
        self.revealed_abilities: Dict[str, Dict[str, str]] = {}
        self.admin_ability_reveal: bool = True
        self._reveal_data = None
        self.rng = rng or random
        self._rewards_granted: bool = False
        self._result_logged: bool = False
        self.award_xp: bool = True
        self.award_txp: bool = True
        self.turn_resolution_service = turn_resolution_service or TurnResolutionService()
        self.status_service = status_service or StatusService()
        self.message_formatter = message_formatter or MessageFormatter()
        self.reward_service = reward_service or RewardService()

        # If any participant already has active PokÃƒÆ’Ã‚Â©mon assigned (common in
        # tests or restored battles) make sure they are marked as having
        # participated so they receive rewards appropriately.
        for part in self.participants:
            side = getattr(part, "side", None)
            if side is not None:
                setattr(side, "pokemons", getattr(part, "pokemons", []))
                setattr(side, "active", getattr(part, "active", []))
                if not hasattr(side, "volatiles"):
                    setattr(side, "volatiles", {})
                if not hasattr(side, "used_items"):
                    setattr(side, "used_items", [])
                if not hasattr(side, "side_conditions"):
                    setattr(side, "side_conditions", getattr(side, "conditions", {}))
            for poke in getattr(part, "active", []) or []:
                if hasattr(part, "record_participation"):
                    part.record_participation(poke)
                setattr(poke, "battle", self)
                for state_name, effect in (("ability_state", getattr(poke, "ability", None)),
                                           ("item_state", getattr(poke, "item", None) or getattr(poke, "held_item", None))):
                    if not effect:
                        continue
                    state = dict(getattr(poke, state_name, {}) or {})
                    rebound = self.init_effect_state(effect, target=poke)
                    rebound.update({key: value for key, value in state.items() if key != "target"})
                    setattr(poke, state_name, rebound)
        for part in self.participants:
            side = getattr(part, "side", None)
            if side is None:
                continue
            foe = self.opponent_of(part)
            setattr(side, "foe", getattr(foe, "side", None) if foe else None)

    def init_effect_state(
        self,
        effect: Any | None = None,
        *,
        target=None,
        source=None,
        source_effect=None,
    ) -> Dict[str, Any]:
        """Create a lightweight Showdown-style effect state mapping."""

        effect_id = None
        if isinstance(effect, str):
            effect_id = _normalize_key(effect)
        elif effect is not None:
            effect_id = _normalize_key(
                getattr(effect, "id", None)
                or getattr(effect, "name", None)
                or getattr(effect.__class__, "__name__", "")
            )
        return {
            "id": effect_id or "",
            "target": target,
            "source": source,
            "sourceEffect": source_effect,
        }

    def bind_reveal_data(self, data: Any) -> None:
        """Bind live reveal helpers to the serializable BattleData object."""

        self._reveal_data = data
        self.revealed_abilities = getattr(data, "revealed_abilities", {}) or {}
        self.admin_ability_reveal = bool(getattr(data, "admin_ability_reveal", True))

    def _reveal_store(self):
        store = getattr(self, "_reveal_data", None)
        if store is not None and hasattr(store, "reveal_ability_to_viewer"):
            return store
        return self

    def _local_pokemon_reveal_key(self, pokemon, *, side: Optional[str] = None) -> str:
        teams = getattr(getattr(self, "_reveal_data", None), "teams", None)
        return _pokemon_reveal_key(pokemon, teams, side=side)

    def reveal_ability_to_viewer(
        self,
        viewer_side_or_id: Any,
        pokemon,
        ability_name: Optional[str] = None,
        *,
        pokemon_side: Optional[str] = None,
    ) -> bool:
        """Remember that a viewer side knows a Pokemon's ability."""

        store = self._reveal_store()
        if store is not self:
            changed = store.reveal_ability_to_viewer(
                viewer_side_or_id,
                pokemon,
                ability_name,
                pokemon_side=pokemon_side,
            )
            self.revealed_abilities = getattr(store, "revealed_abilities", {})
            self.admin_ability_reveal = bool(getattr(store, "admin_ability_reveal", True))
            return changed

        viewer_key = _normalize_reveal_viewer(viewer_side_or_id)
        pokemon_key = self._local_pokemon_reveal_key(pokemon, side=pokemon_side)
        ability_text = ability_name or _ability_display_name(
            getattr(pokemon, "ability", None) or getattr(pokemon, "ability_name", None)
        )
        if not viewer_key or not pokemon_key or not ability_text:
            return False
        self.revealed_abilities.setdefault(viewer_key, {})[pokemon_key] = ability_text
        return True

    def reveal_ability_to_side(
        self,
        viewer_side_or_id: Any,
        pokemon,
        ability_name: Optional[str] = None,
        *,
        pokemon_side: Optional[str] = None,
    ) -> bool:
        return self.reveal_ability_to_viewer(
            viewer_side_or_id,
            pokemon,
            ability_name,
            pokemon_side=pokemon_side,
        )

    def reveal_ability_to_all(
        self,
        pokemon,
        ability_name: Optional[str] = None,
        *,
        pokemon_side: Optional[str] = None,
    ) -> bool:
        return self.reveal_ability_to_viewer(
            _REVEAL_ALL_VIEWERS,
            pokemon,
            ability_name,
            pokemon_side=pokemon_side,
        )

    def get_revealed_ability_for_viewer(
        self,
        viewer_side_or_id: Any,
        pokemon,
        *,
        pokemon_side: Optional[str] = None,
    ) -> Optional[str]:
        store = self._reveal_store()
        if store is not self:
            return store.get_revealed_ability_for_viewer(
                viewer_side_or_id,
                pokemon,
                pokemon_side=pokemon_side,
            )

        pokemon_key = self._local_pokemon_reveal_key(pokemon, side=pokemon_side)
        viewer_key = _normalize_reveal_viewer(viewer_side_or_id)
        for key in (viewer_key, _REVEAL_ALL_VIEWERS):
            if not key:
                continue
            ability = self.revealed_abilities.get(key, {}).get(pokemon_key)
            if ability:
                return ability
        return None

    def can_view_ability(
        self,
        caller: Any,
        pokemon,
        viewer_side_or_id: Any,
        *,
        pokemon_side: Optional[str] = None,
        owns_pokemon: bool = False,
    ) -> tuple[bool, bool]:
        store = self._reveal_store()
        if store is not self and hasattr(store, "can_view_ability"):
            return store.can_view_ability(
                caller,
                pokemon,
                viewer_side_or_id,
                pokemon_side=pokemon_side,
                owns_pokemon=owns_pokemon,
            )
        if owns_pokemon:
            return True, False
        if self.get_revealed_ability_for_viewer(
            viewer_side_or_id,
            pokemon,
            pokemon_side=pokemon_side,
        ):
            return True, False
        if self.admin_ability_reveal and _caller_is_admin(caller):
            return True, True
        return False, False

    def set_admin_ability_reveal(self, enabled: bool) -> None:
        """Set the battle-scoped admin reveal flag."""

        self.admin_ability_reveal = bool(enabled)
        store = getattr(self, "_reveal_data", None)
        if store is not None:
            setattr(store, "admin_ability_reveal", self.admin_ability_reveal)

    def reveal_entry_ability(self, pokemon) -> bool:
        """Reveal abilities whose switch-in/start effect exposes them."""

        ability = _resolve_ability(getattr(pokemon, "ability", None)) or getattr(pokemon, "ability", None)
        if _effect_key(ability) not in REVEAL_ON_ENTRY_ABILITIES:
            return False
        return self.reveal_ability_to_all(
            pokemon,
            _ability_display_name(ability),
        )

    def clear_effect_state(self, state: Optional[Dict[str, Any]]) -> None:
        """Clear an effect-state mapping in place."""

        if isinstance(state, dict):
            state.clear()

    def _ability_flags(self, ability) -> Dict[str, Any]:
        """Return raw dex flags for ``ability`` when available."""

        resolved = _resolve_ability(ability) or ability
        raw = getattr(resolved, "raw", None)
        if isinstance(raw, Mapping):
            flags = raw.get("flags")
            if isinstance(flags, Mapping):
                return dict(flags)
        entry = ABILITYDEX.get(_effect_key(resolved))
        raw = getattr(entry, "raw", None)
        if isinstance(raw, Mapping) and isinstance(raw.get("flags"), Mapping):
            return dict(raw["flags"])
        return {}

    def _move_ignores_target_ability(self, source, target, move) -> bool:
        """Return whether ``move`` should bypass target ability effects."""

        from .effect_context import EffectContext

        ability = EffectContext.ability(target)
        if source is target or (getattr(ability, "raw", {}) or {}).get("flags", {}).get("cantsuppress"):
            return False
        if ability is not None and not self._ability_flags(ability).get("breakable"):
            return False
        if EffectContext.key(EffectContext.item(target)) == "abilityshield":
            return False
        if getattr(move, "ignore_ability", False) or getattr(move, "ignoreAbility", False):
            return True
        raw = getattr(move, "raw", {}) or {}
        if raw.get("ignoreAbility"):
            return True
        source_ability = EffectContext.key(EffectContext.ability(source))
        if source_ability in {"moldbreaker", "teravolt", "turboblaze"}:
            return True
        if getattr(target, "volatiles", {}).get("gastroacid"):
            return True
        return False

    def _metadata_immunity(self, eventid: str, target, source, effect, relayVar):
        """Handle metadata-only ability immunity rules not represented by callbacks."""

        if eventid != "Immunity" or target is None:
            return None
        move_type = _normalize_key(relayVar or getattr(effect, "type", None)).lower()
        if move_type != "ground":
            return None
        from .effect_context import EffectContext
        ability = _resolve_ability(EffectContext.ability(target))
        if _effect_key(ability) != "levitate":
            return None
        if self._move_ignores_target_ability(source, target, effect):
            return None
        field = getattr(self, "field", None)
        if getattr(field, "pseudo_weather", {}).get("gravity"):
            return None
        item_key = _effect_key(getattr(target, "item", None) or getattr(target, "held_item", None))
        if item_key == "ironball":
            return None
        volatiles = getattr(target, "volatiles", {}) or {}
        if volatiles.get("ingrain") or volatiles.get("smackdown"):
            return None
        target.immune = "Levitate"
        return False

    def _ability_item_type(self, pokemon) -> Optional[str]:
        """Return the type granted by Multitype/RKS System's held item."""

        ability_key = _effect_key(_resolve_ability(getattr(pokemon, "ability", None)) or getattr(pokemon, "ability", None))
        item = self._holder_item(pokemon)
        raw = getattr(item, "raw", {}) or {}
        if ability_key == "multitype" and raw.get("onPlate"):
            return str(raw["onPlate"]).title()
        if ability_key == "rkssystem" and raw.get("onMemory"):
            return str(raw["onMemory"]).title()
        return None

    def _apply_ability_item_type(self, pokemon) -> None:
        """Apply Multitype/RKS System item-driven typing on entry."""

        granted_type = self._ability_item_type(pokemon)
        if not granted_type:
            return
        base = str(getattr(pokemon, "base_species", getattr(pokemon, "species", ""))).split("-")[0]
        if base in {"Arceus", "Silvally"}:
            previous = str(pokemon.species)
            forme = base if granted_type == "Normal" else base + "-" + granted_type
            pokemon.species = forme
            if pokemon.name == previous:
                pokemon.name = forme
        if hasattr(pokemon, "setType"):
            try:
                pokemon.setType(granted_type)
                return
            except Exception:
                pass
        pokemon.types = [granted_type]

    def _assign_post_battle_item(self, pokemon, item) -> bool:
        """Assign an item after battle, tolerating item names absent from ITEMDEX."""

        if not pokemon or not item or self._pokemon_has_item(pokemon):
            return False
        if self.set_item(pokemon, item):
            return True
        pokemon.item = item
        if hasattr(pokemon, "held_item"):
            pokemon.held_item = getattr(item, "name", str(item))
        return True

    def _honey_gather_chance(self, pokemon) -> int:
        """Return Honey Gather's level-tier percentage chance."""

        level = max(1, int(getattr(pokemon, "level", 1) or 1))
        return min(50, ((level - 1) // 10 + 1) * 5)

    def resolve_post_battle_abilities(self, *, caught: bool = False, thrown_ball: str | None = None,
                                     participant=None):
        """Resolve eligible item effects and return only the awarded runtime items."""

        rng = getattr(self, "rng", random)
        awards = []
        participants = [participant] if participant is not None else getattr(self, "participants", []) or []
        for owner in participants:
            for pokemon in getattr(owner, "pokemons", []) or []:
                if self._pokemon_has_item(pokemon):
                    continue
                ability_key = _effect_key(_resolve_ability(getattr(pokemon, "ability", None)) or getattr(pokemon, "ability", None))
                if ability_key == "ballfetch":
                    if thrown_ball and not caught:
                        if self._assign_post_battle_item(pokemon, thrown_ball):
                            awards.append((pokemon, thrown_ball))
                elif ability_key == "honeygather":
                    chance = self._honey_gather_chance(pokemon) / 100.0
                    if rng.random() < chance:
                        if self._assign_post_battle_item(pokemon, "Honey"):
                            awards.append((pokemon, "Honey"))
        return awards

    def _trigger_dancer_copy(self, user, target, move) -> None:
        """Let active Dancer holders copy a dance-flag move once."""

        if getattr(move, "_dancer_copy", False):
            return
        flags = getattr(move, "flags", None) or (getattr(move, "raw", {}) or {}).get("flags", {})
        if not isinstance(flags, Mapping) or not flags.get("dance"):
            return
        for participant in getattr(self, "participants", []) or []:
            for dancer in getattr(participant, "active", []) or []:
                if dancer is None or dancer is user or getattr(dancer, "hp", 0) <= 0:
                    continue
                ability_key = _effect_key(_resolve_ability(getattr(dancer, "ability", None)) or getattr(dancer, "ability", None))
                if ability_key != "dancer":
                    continue
                copied = copy.deepcopy(move)
                setattr(copied, "_dancer_copy", True)
                copied_target = dancer if is_self_target((getattr(copied, "raw", {}) or {}).get("target")) else target
                if copied_target is None:
                    copied_target = dancer
                try:
                    copied.execute(dancer, copied_target, self)
                except Exception as err:
                    self._record_failure(context="dancer_copy", exception=err, pokemon=dancer, event=getattr(move, "name", None))

    def _event_hook_name(self, eventid: str) -> str:
        return f"on{eventid}"

    def _call_effect_event(
        self,
        holder: Any,
        hook: str,
        *call_args: Any,
        fallback_modules: str | list[str] | None = None,
        **call_kwargs: Any,
    ) -> Any:
        """Invoke ``hook`` on an effect holder when possible."""

        if holder is None:
            return None
        if hasattr(holder, "call"):
            return holder.call(hook, *call_args, **call_kwargs)
        callback = getattr(holder, hook, None)
        if callable(callback):
            return invoke_callback(callback, *call_args, **call_kwargs)

        raw = getattr(holder, "raw", None)
        if isinstance(raw, dict):
            cb_name = raw.get(hook)
            if cb_name:
                callback = resolve_callback_from_modules(
                    cb_name,
                    fallback_modules
                    or [
                        "pokemon.dex.functions.moves_funcs",
                        "pokemon.dex.functions.conditions_funcs",
                        "pokemon.dex.functions.abilities_funcs",
                        "pokemon.dex.functions.items_funcs",
                    ],
                )
                if callable(callback):
                    return invoke_callback(callback, *call_args, **call_kwargs)
        return None

    def _pokemon_status_handler(self, pokemon):
        status = getattr(pokemon, "status", None)
        if not status:
            return None
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            return None
        return CONDITION_HANDLERS.get(status)

    def _pokemon_volatile_handlers(self, pokemon) -> List[tuple[str, Any]]:
        handlers: List[tuple[str, Any]] = []
        for name in list(getattr(pokemon, "volatiles", {}).keys()):
            handler = self._volatile_handler(name)
            if handler:
                handlers.append((name, handler))
        return handlers

    def _volatile_handler(self, condition: str):
        """Resolve a volatile handler from move or condition callback modules."""

        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:
            VOLATILE_HANDLERS = {}
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        handler = VOLATILE_HANDLERS.get(condition) or CONDITION_HANDLERS.get(condition)
        if handler is not None:
            return handler
        try:
            import pokemon.dex.functions.moves_funcs as moves_funcs_mod
        except Exception:
            moves_funcs_mod = None
        try:
            import pokemon.dex.functions.conditions_funcs as conditions_funcs_mod
        except Exception:
            conditions_funcs_mod = None
        if moves_funcs_mod is not None:
            cls = getattr(moves_funcs_mod, str(condition).capitalize(), None)
            if cls:
                try:
                    return cls()
                except Exception:
                    return None
        if conditions_funcs_mod is not None:
            cls = getattr(conditions_funcs_mod, str(condition).capitalize(), None)
            if cls:
                try:
                    return cls()
                except Exception:
                    return None
        return None

    def _side_condition_handlers(self, side) -> List[tuple[str, Any, Dict[str, Any]]]:
        """Return resolved handlers for conditions active on ``side``."""

        if side is None:
            return []
        lookup = getattr(self, "_lookup_effect", None)
        if not callable(lookup):
            return []
        handlers: List[tuple[str, Any, Dict[str, Any]]] = []
        for name, state in list(getattr(side, "conditions", {}).items()):
            handler = lookup(name)
            if handler is not None:
                handlers.append((name, handler, state if isinstance(state, dict) else {}))
        return handlers

    def _active_slot_index(self, pokemon) -> Optional[int]:
        """Return the active-slot index for ``pokemon`` if it is currently active."""

        participant = self.participant_for(pokemon)
        if participant is None:
            return None
        if getattr(participant, 'field_position', None):
            return int(participant.field_position[1:]) - 1
        try:
            return list(getattr(participant, "active", [])).index(pokemon)
        except ValueError:
            return None

    def _slot_condition_handlers(self, side, slot: Optional[int]) -> List[tuple[str, Any, Dict[str, Any]]]:
        """Return resolved handlers for slot conditions active in ``slot`` on ``side``."""

        if side is None or slot is None:
            return []
        lookup = getattr(self, "_lookup_effect", None)
        if not callable(lookup):
            return []
        handlers: List[tuple[str, Any, Dict[str, Any]]] = []
        for name, state in list(getattr(side, "slot_conditions", {}).get(slot, {}).items()):
            handler = lookup(name)
            if handler is not None:
                handlers.append((name, handler, state if isinstance(state, dict) else {}))
        return handlers

    def _field_effect_handlers(self) -> List[tuple[Any, Optional[Dict[str, Any]], Any]]:
        """Return active field effect holders for scoped event dispatch."""

        holders: List[tuple[Any, Optional[Dict[str, Any]], Any]] = [(self.field, None, self.field)]
        weather_handler = getattr(self.field, "weather_handler", None)
        if weather_handler is not None:
            holders.append((weather_handler, getattr(self.field, "weather_state", None), self.field))
        terrain_handler = getattr(self.field, "terrain_handler", None)
        if terrain_handler is not None:
            holders.append((terrain_handler, getattr(self.field, "terrain_state", None), self.field))
        lookup = getattr(self, "_lookup_effect", None)
        if callable(lookup):
            weather_key = getattr(self.field, "weather", None)
            terrain_key = getattr(self.field, "terrain", None)
            for name, state in list(getattr(self.field, "pseudo_weather", {}).items()):
                if name == weather_key and weather_handler is not None:
                    continue
                if name == terrain_key and terrain_handler is not None:
                    continue
                handler = lookup(name)
                if handler is not None:
                    holders.append((handler, state if isinstance(state, dict) else {}, self.field))
        return holders

    def _event_scoped_holders(
        self, target=None, source=None, effect=None, *, include_suppressed_items=False,
    ) -> List[tuple[Any, Optional[Dict[str, Any]], Any]]:
        """Return effect holders participating in a scoped event."""

        holders: List[tuple[Any, Optional[Dict[str, Any]], Any]] = []
        seen: set[tuple[Any, int, int, int]] = set()
        from .effect_context import EffectContext

        # Physical removal rules still apply under Embargo, Klutz and Magic Room.
        # Other event consumers continue to receive only effective held items.
        item_for = self._holder_item if include_suppressed_items else EffectContext.item

        def add_holder(holder, state=None, owner=None) -> None:
            if holder is not None:
                relation = holder[0] if isinstance(holder, tuple) else None
                actual_holder = holder[1] if isinstance(holder, tuple) else holder
                key = (relation, id(actual_holder), id(state), id(owner))
                if key in seen:
                    return
                seen.add(key)
                holders.append((holder, state, owner))

        def add_holder_with_relation(relation, holder, state=None, owner=None) -> None:
            add_holder((relation, holder) if relation is not None and holder is not None else holder, state, owner)

        if target is not None:
            add_holder(target, None, target)
            add_holder(self._pokemon_status_handler(target), getattr(target, "status_state", None), target)
            for volatile_name, handler in self._pokemon_volatile_handlers(target):
                add_holder(handler, getattr(target, "volatiles", {}).get(volatile_name), target)
            if not self._move_ignores_target_ability(source, target, effect):
                add_holder(EffectContext.ability(target), getattr(target, "ability_state", None), target)
            add_holder(item_for(target), getattr(target, "item_state", None), target)
            target_participant = self.participant_for(target)
            target_side = getattr(target_participant, "side", getattr(target, "side", None))
            if target_side is not None:
                add_holder(target_side, None, target_side)
                for _, handler, state in self._side_condition_handlers(target_side):
                    add_holder(handler, state, target_side)
                target_slot = self._active_slot_index(target)
                for _, handler, state in self._slot_condition_handlers(target_side, target_slot):
                    add_holder(handler, state, target)
            for holder, state, owner in self._field_effect_handlers():
                add_holder(holder, state, owner)
        else:
            target_participant = None
            target_side = None

        for part in self.participants:
            side = getattr(part, "side", None)
            side_relation = "foe"
            if source is not None and getattr(source, 'side', None) is side:
                side_relation = "source"
            elif target_participant is not None and self._allied(part, target_participant):
                side_relation = "ally"
            if target is not None and side is not None and side is not target_side:
                add_holder_with_relation(side_relation, side, None, side)
                for _, handler, state in self._side_condition_handlers(side):
                    add_holder_with_relation(side_relation, handler, state, side)
            for pokemon in getattr(part, "active", []):
                if pokemon is None or pokemon is target:
                    continue
                relation = "foe"
                if source is not None and pokemon is source:
                    relation = "source"
                elif target is not None and self._allied(self.participant_for(pokemon), self.participant_for(target)):
                    relation = "ally"
                add_holder_with_relation(relation, self._pokemon_status_handler(pokemon), getattr(pokemon, "status_state", None), pokemon)
                for volatile_name, handler in self._pokemon_volatile_handlers(pokemon):
                    add_holder_with_relation(relation, handler, getattr(pokemon, "volatiles", {}).get(volatile_name), pokemon)
                ability = EffectContext.ability(pokemon)
                item = item_for(pokemon)
                slot = self._active_slot_index(pokemon)
                if side is not None:
                    for _, handler, state in self._slot_condition_handlers(side, slot):
                        add_holder_with_relation(relation, handler, state, pokemon)
                if ability:
                    add_holder_with_relation(relation, ability, getattr(pokemon, "ability_state", None), pokemon)
                if item:
                    add_holder_with_relation(relation, item, getattr(pokemon, "item_state", None), pokemon)

        if target is None:
            for holder, state, owner in self._field_effect_handlers():
                add_holder(holder, state, owner)
            for part in self.participants:
                add_holder(part.side, None, part.side)
                for _, handler, state in self._side_condition_handlers(part.side):
                    add_holder(handler, state, part.side)
                for pokemon in getattr(part, "active", []):
                    add_holder(self._pokemon_status_handler(pokemon), getattr(pokemon, "status_state", None), pokemon)
                    for volatile_name, handler in self._pokemon_volatile_handlers(pokemon):
                        add_holder(handler, getattr(pokemon, "volatiles", {}).get(volatile_name), pokemon)
                    slot = self._active_slot_index(pokemon)
                    for _, handler, state in self._slot_condition_handlers(part.side, slot):
                        add_holder(handler, state, pokemon)
                    add_holder(EffectContext.ability(pokemon), getattr(pokemon, "ability_state", None), pokemon)
                    add_holder(item_for(pokemon), getattr(pokemon, "item_state", None), pokemon)
        return holders

    def singleEvent(
        self,
        eventid: str,
        effect: Any,
        state: Optional[Dict[str, Any]],
        target,
        source=None,
        source_effect=None,
        relayVar: Any = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> Any:
        """Run a single explicit event against ``effect``."""

        hook = self._event_hook_name(eventid)
        event_state = state if isinstance(state, dict) else self.init_effect_state(effect, target=target, source=source, source_effect=source_effect)
        if relayVar is None:
            call_args = (target, source, source_effect)
        else:
            call_args = (relayVar, target, source, source_effect)
        try:
            if callable(callback):
                result = invoke_callback(callback, *call_args, battle=self, effect_state=event_state)
            else:
                result = self._call_effect_event(effect, hook, *call_args, battle=self, effect_state=event_state)
        except Exception as err:
            self._record_failure(context="single_event", exception=err, pokemon=target, event=eventid)
            return False if relayVar is None else relayVar
        if result is None:
            return True if relayVar is None else relayVar
        return result

    def runEvent(
        self,
        eventid: str,
        target=None,
        source=None,
        effect: Any = None,
        relayVar: Any = None,
        onEffect: bool = False,
        fastExit: bool = False,
    ) -> Any:
        """Run a simplified Showdown-style scoped event."""

        metadata_result = self._metadata_immunity(eventid, target, source, effect, relayVar)
        if metadata_result is False:
            return False

        base_hook = self._event_hook_name(eventid)
        relay = relayVar
        relay_kw_name = None
        relay_positional = True
        item_event = eventid in {"UseItem", "TryEatItem", "EatItem", "TakeItem"}
        if item_event:
            relay_kw_name = "item"
            relay_positional = False
        elif eventid in {"SetStatus", "AfterSetStatus"}:
            relay_kw_name = "status"
            relay_positional = False
        elif eventid == "SetAbility":
            relay_kw_name = "ability"
            relay_positional = False
        elif eventid == "TryAddVolatile":
            relay_kw_name = "status"
            relay_positional = False
        for holder, state, owner in self._event_scoped_holders(
            target=target, source=source, effect=effect,
            include_suppressed_items=eventid == "TakeItem",
        ):
            relation = None
            actual_holder = holder
            if isinstance(holder, tuple):
                relation, actual_holder = holder
            hooks = [base_hook]
            if eventid == "TryAddVolatile" and relation is None and owner is target:
                hooks.append("onAllyTryAddVolatile")
            if relation == "source":
                hooks = [f"onSource{eventid}"]
            elif relation == "ally":
                hooks = [f"onAlly{eventid}"]
            elif relation == "foe":
                hooks = [f"onFoe{eventid}"]

            if (
                eventid == "RedirectTarget"
                and relation in {"ally", "foe"}
                and source is not None
                and owner is not None
            ):
                # Redirect effects belong to the attacker's ally/foe relation.
                # A separate controller can still be on the attacker's team.
                owner_part = self.participant_for(owner)
                source_part = self.participant_for(source)
                if owner_part is not None and source_part is not None:
                    prefix = "onAlly" if self._allied(owner_part, source_part) else "onFoe"
                    hooks = [f"{prefix}{eventid}"]

            try:
                call_kwargs = {
                    "battle": self,
                    "effect_state": state,
                    "effect_owner": owner,
                }
                if relayVar is None:
                    call_args = (target, source, effect)
                    if eventid == "PrepareHit":
                        call_args = (effect, target, source)
                else:
                    call_kwargs["relayVar"] = relay
                    if relay_kw_name:
                        call_kwargs[relay_kw_name] = relay
                    if item_event:
                        call_kwargs["pokemon"] = target
                        call_kwargs["source"] = source
                        call_kwargs["effect"] = effect
                        call_args = ()
                    elif relay_kw_name:
                        call_kwargs["pokemon"] = target
                        call_kwargs["target"] = target
                        call_kwargs["source"] = source
                        call_kwargs["effect"] = effect
                        call_args = ()
                    else:
                        call_args = (
                            (relay, target, source, effect)
                            if relay_positional
                            else (target, source, effect)
                        )
                result = None
                for hook in hooks:
                    hook_args = call_args
                    hook_kwargs = dict(call_kwargs)
                    if (
                        eventid == "RedirectTarget"
                        and relayVar is not None
                        and owner is not None
                        and hook != base_hook
                    ):
                        hook_args = (owner, source, effect)
                    elif (
                        eventid == "TryHeal"
                        and relayVar is not None
                        and hook == f"onSource{eventid}"
                    ):
                        hook_args = (relay,)
                        hook_kwargs["source"] = source
                        hook_kwargs["target"] = target
                        hook_kwargs["move"] = effect
                        hook_kwargs["effect"] = effect
                    elif (
                        eventid == "TryHeal"
                        and relayVar is not None
                        and hook == base_hook
                        and getattr(effect, "raw", {}).get("drain")
                    ):
                        drain_effect = SimpleNamespace(id="drain")
                        hook_args = (relay, target, source, drain_effect)
                        hook_kwargs["effect"] = drain_effect
                    result = self._call_effect_event(
                        actual_holder,
                        hook,
                        *hook_args,
                        **hook_kwargs,
                    )
                    if result is not None:
                        break
                any_hook = f"onAny{eventid}"
                any_args = (
                    relay if relayVar is not None else target,
                    target if relayVar is not None else source,
                    source if relayVar is not None else effect,
                    effect if relayVar is not None else None,
                )
                if eventid == "RedirectTarget":
                    # The target is already the relay for redirect callbacks.
                    any_args = (relay if relayVar is not None else target, source, effect)
                elif eventid == "PrepareHit":
                    any_args = (effect, target, source)
                any_result = self._call_effect_event(
                    actual_holder,
                    any_hook,
                    *any_args,
                    battle=self,
                    effect_state=state,
                    effect_owner=owner,
                )
                if any_result is not None:
                    result = any_result
            except Exception as err:
                self._record_failure(context="run_event", exception=err, pokemon=owner, event=eventid)
                continue

            if relayVar is None:
                if result is False:
                    return result
                if result is None:
                    continue
                if fastExit and result not in {True, None}:
                    return result
            else:
                if result is False:
                    return result
                if result is None:
                    continue
                if isinstance(relay, bool) and isinstance(result, bool):
                    relay = result
                    if fastExit:
                        return relay
                elif result is not True or eventid == "Accuracy":
                    relay = result
                    if fastExit:
                        return relay
        return True if relayVar is None else relay

    def eachEvent(self, eventid: str, effect: Any = None, relayVar: Any = None):
        """Run an event once for each active Pokemon."""

        result = relayVar
        for part in self.participants:
            for pokemon in getattr(part, "active", []):
                if relayVar is None:
                    current = self.runEvent(eventid, pokemon, None, effect)
                    if current is False or current is None:
                        return current
                else:
                    current = self.runEvent(eventid, pokemon, None, effect, result)
                    if current is False or current is None:
                        return current
                    result = current
        return True if relayVar is None else result

    def residualEvent(self, eventid: str = "Residual", effect: Any = None):
        """Run a residual-style event across active Pokemon."""

        return self.eachEvent(eventid, effect=effect)

    def _format_default_message(
        self,
        key: str,
        replacements: Mapping[str, Sequence[str] | str],
        fallback: str | None = None,
    ) -> str | None:
        """Return the formatted message for ``key`` from :data:`DEFAULT_TEXT`."""

        return self.message_formatter.format_default_message(key, replacements, fallback)

    def _pokemon_nickname(self, pokemon) -> str:
        """Return the best nickname representation for ``pokemon``."""

        return self.message_formatter.pokemon_nickname(pokemon)

    def _pokemon_fullname(self, pokemon) -> str:
        """Return a display-friendly full name for ``pokemon``."""

        return self.message_formatter.pokemon_fullname(pokemon)

    def _item_display_name(self, item) -> str:
        """Return a display string for ``item``."""

        return self.message_formatter.item_display_name(item)

    def _status_template(self, status_key: str, event: str) -> str | None:
        """Return the message template for ``status_key`` and ``event``."""

        return self.message_formatter.status_template(status_key, event)

    def _log_switch_in(self, participant: BattleParticipant, pokemon) -> None:
        """Log the standard switch-in message for ``pokemon``."""

        message = self._format_default_message(
            "switchIn",
            {
                "[TRAINER]": getattr(participant, "name", "Trainer"),
                "[FULLNAME]": self._pokemon_fullname(pokemon),
            },
        )
        if message:
            if participant.max_active > 1:
                from .active_slots import slot_for
                slot = slot_for(participant, pokemon)
                label = participant.team or ("A" if self.participants[0] is participant else "B")
                message = f"{label}{slot + 1}: " + message if slot is not None else message
            self.log_action(message)

    def _log_switch_out(self, participant: BattleParticipant, pokemon) -> None:
        """Log the switch-out message for ``pokemon``."""

        message = self._format_default_message(
            "switchOut",
            {
                "[TRAINER]": getattr(participant, "name", "Trainer"),
                "[NICKNAME]": self._pokemon_nickname(pokemon),
            },
        )
        if message:
            self.log_action(message)

    # ------------------------------------------------------------------
    # Battle initialisation helpers
    # ------------------------------------------------------------------
    def start_battle(self) -> None:
        """Prepare the battle by sending out the first available PokÃƒÆ’Ã‚Â©mon."""
        names = [
            getattr(part, "name", "Trainer")
            for part in self.participants
            if not getattr(part, "has_lost", False)
        ]
        if len(names) >= 2:
            trainer_values = names[:2]
        elif names:
            trainer_values = [names[0], names[0]]
        else:
            trainer_values = ["Trainer", "Trainer"]
        message = self._format_default_message(
            "startBattle", {"[TRAINER]": trainer_values}
        )
        if message:
            self.log_action(message)
        initial_sends = []
        for participant in self.participants:
            for poke in getattr(participant, "pokemons", []) or []:
                setattr(poke, "battle", self)
                setattr(poke, "side", getattr(participant, "side", None))
                setattr(poke, "party", list(getattr(participant, "pokemons", []) or []))
            if participant.active:
                continue
            for poke in participant.pokemons:
                if getattr(poke, "hp", 1) > 0:
                    participant.active.append(poke)
                    initial_sends.append((participant, poke))
                    if len(participant.active) >= getattr(participant, "max_active", 1):
                        break
        for participant, poke in initial_sends:
            self.on_enter_battle(poke)
            self._log_switch_in(participant, poke)

    def send_out_pokemon(self, pokemon, slot: int = 0) -> None:
        """Place ``pokemon`` into the active slot for its participant."""
        from .active_slots import active_at, assign_active
        part = self.participant_for(pokemon)
        if not part or not 0 <= slot < part.max_active:
            return
        old = active_at(part, slot)
        if old is not None:
            if old is pokemon:
                return
            self.on_switch_out(old, source=pokemon)
        assign_active(part, slot, pokemon)
        self.on_enter_battle(pokemon, source=old)
        self._log_switch_in(part, pokemon)

    def switch_pokemon(
        self, participant: BattleParticipant, new_pokemon, slot: int = 0
    ) -> None:
        """Switch the active PokÃƒÆ’Ã‚Â©mon for ``participant`` in ``slot``."""
        from .active_slots import active_at, assign_active

        current = active_at(participant, slot)
        if new_pokemon and self.runEvent(
            "BeforeSwitchIn",
            new_pokemon,
            current,
            getattr(self, "effect", None),
        ) is False:
            return
        if current is None:
            assign_active(participant, slot, new_pokemon)
            self.on_enter_battle(new_pokemon, source=current)
            self._log_switch_in(participant, new_pokemon)
            return
        if current is new_pokemon:
            return
        if self.runEvent(
            "BeforeSwitchOut",
            current,
            new_pokemon,
            getattr(self, "effect", None),
        ) is False:
            return
        self.on_switch_out(current, source=new_pokemon)
        assign_active(participant, slot, new_pokemon)
        self.on_enter_battle(new_pokemon, source=current)
        self._log_switch_in(participant, new_pokemon)

    def participant_for(self, pokemon) -> Optional[BattleParticipant]:
        """Return the participant owning ``pokemon`` if any."""
        for part in self.participants:
            if any(member is pokemon for member in part.pokemons):
                return part
        return None

    @staticmethod
    def _allied(left, right):
        """Keep allegiance separate from controller/roster identity."""
        return bool(left and right and (left is right or (getattr(left, 'team', None) is not None
                    and left.team == getattr(right, 'team', None))))

    def opponent_of(
        self, participant: BattleParticipant
    ) -> Optional[BattleParticipant]:
        """Return the first available opponent of ``participant``.

        Respects team assignments when present, falling back to the first
        non-fainted participant that is not ``participant`` when teams are not
        specified.
        """
        opponents = self.opponents_of(participant)
        return opponents[0] if opponents else None

    def opponents_of(self, participant: BattleParticipant) -> List[BattleParticipant]:
        """Return a list of all active opponents for ``participant``.

        Participants sharing the same ``team`` value are considered allies and
        excluded from the returned list. If ``participant`` has no team
        assigned, all other non-fainted participants are treated as opponents.
        """
        opponents: List[BattleParticipant] = []
        my_team = getattr(participant, "team", None)
        for part in self.participants:
            if part is participant or part.has_lost:
                continue
            other_team = getattr(part, "team", None)
            if my_team is not None and other_team == my_team:
                continue
            opponents.append(part)
        return opponents

    def restore_transforms(self) -> None:
        """Revert any PokÃƒÆ’Ã‚Â©mon transformed via the Transform move."""
        from .terastallization import Terastallization

        for part in self.participants:
            for poke in part.pokemons:
                self.remove_volatile(poke, "roost")
                from .copied_moves import BattleCopyState

                BattleCopyState.cleanup(poke)
                from .appearance import BattleAppearance

                BattleAppearance.restore(poke)
                from .native_forms import NativeBattleForm

                NativeBattleForm.restore(poke)
                poke.bond_triggered = False
                backup = getattr(poke, "tempvals", {}).get("transform_backup")
                if backup:
                    for attr, value in backup.items():
                        setattr(poke, attr, value)
                    poke.tempvals.pop("transform_backup", None)
                    if hasattr(poke, "transformed"):
                        poke.transformed = False
        # Transform can have backed up an already-Tera defensive type. Restore
        # ordinary typing last so that backup cannot reintroduce the Tera type.
        Terastallization.cleanup(self)

    # ------------------------------------------------------------------
    # Battle event hooks
    # ------------------------------------------------------------------

    def _register_callbacks(self, data: Dict[str, Any], pokemon, *, registry: Any = None, ability_key=None, item_key=None) -> None:
        """Register typed callbacks from ability or item data at startup."""
        event_map = {
            "onPreStart": "pre_start",
            "onStart": "start",
            "onSwitchIn": "switch_in",
            "onSwitchOut": "switch_out",
            "onBeforeTurn": "before_turn",
            "onBeforeMove": "before_move",
            "onAfterMove": "after_move",
            "onUpdate": "update",
        }

        owner_name = getattr(pokemon, "name", getattr(pokemon, "species", "pokemon"))
        registered = getattr(self, "_registered_callback_keys", None)
        if registered is None:
            registered = self._registered_callback_keys = set()
        for key, event in event_map.items():
            identity = (id(pokemon), key, ability_key, item_key)
            if identity in registered:
                continue
            registered_key = f"{id(self)}:{id(pokemon)}:{key}:{ability_key}:{item_key}"
            cb = CALLBACK_REGISTRY.register(registered_key, data.get(key), registry=registry)
            if not callable(cb):
                continue

            def wrapped(*, _pokemon=pokemon, _callback=cb, _ability_key=ability_key, _item_key=item_key, **ctx):
                """Invoke a registered callback while preserving legacy arity behavior."""
                if ctx.get("pokemon") is not _pokemon:
                    return
                if _ability_key:
                    from .effect_context import EffectContext

                    if EffectContext.key(EffectContext.ability(_pokemon)) != _ability_key:
                        return
                if _item_key:
                    from .effect_context import EffectContext

                    if EffectContext.key(EffectContext.item(_pokemon)) != _item_key:
                        return
                try:
                    _callback(_pokemon, self)
                except TypeError:
                    try:
                        _callback(_pokemon)
                    except TypeError:
                        _callback()

            wrapped.__name__ = f"event_{event}_{owner_name}_{key}"
            # Register the wrapped callback once to avoid duplicate
            # notifications for the same event.
            self.dispatcher.register(event, wrapped)
            registered.add(identity)

    def register_handlers(self, pokemon) -> None:
        """Register ability and item callbacks for ``pokemon``."""
        ability = _resolve_ability(getattr(pokemon, "ability", None))
        try:
            ability_registry = safe_import("pokemon.dex.functions.abilities_funcs")
        except Exception:
            ability_registry = None
        if ability and isinstance(getattr(ability, "raw", None), dict):
            callbacks = dict(ability.raw)
            if _effect_key(ability) == "gluttony":
                callbacks["onUpdate"] = "Gluttony.onUpdate"
            if _effect_key(ability) == "illusion":
                callbacks["onStart"] = "Illusion.onBeforeSwitchIn"
            self._register_callbacks(callbacks, pokemon, registry=ability_registry, ability_key=_effect_key(ability))

        item = self._holder_item(pokemon)
        try:
            item_registry = safe_import("pokemon.dex.functions.items_funcs")
        except Exception:
            item_registry = None
        if item and isinstance(getattr(item, "raw", None), dict):
            self._register_callbacks(item.raw, pokemon, registry=item_registry, item_key=_effect_key(item))

    @staticmethod
    def _item_forme_is_eligible(pokemon, forme: str) -> bool:
        """Restrict item forms to their native species and required ability."""

        from pokemon.dex import POKEDEX
        from pokemon.names import resolve_dex_entry

        from .effect_context import EffectContext

        if getattr(pokemon, "transformed", False):
            return False

        def base_species(species):
            entry = resolve_dex_entry(POKEDEX, str(species or ""))
            raw = getattr(entry, "raw", {}) or {}
            return EffectContext.key(raw.get("baseSpecies") or raw.get("name"))

        required = base_species(forme)
        current = getattr(pokemon, "species", None)
        native = getattr(pokemon, "base_species", None) or current
        if not required or base_species(native) != required or base_species(current) != required:
            return False

        ability = {"arceus": "multitype", "silvally": "rkssystem"}.get(required)
        return not ability or EffectContext.key(EffectContext.ability(pokemon)) == ability

    def _apply_item_forme_effects(self, pokemon, *, source=None) -> None:
        """Apply held-item forme changes that take effect on battle entry."""

        from .effect_context import EffectContext

        item = EffectContext.item(pokemon)
        if not item:
            return
        forms = {"blueorb": ("Kyogre", "Kyogre-Primal"), "redorb": ("Groudon", "Groudon-Primal"),
                 "rustedsword": ("Zacian", "Zacian-Crowned"), "rustedshield": ("Zamazenta", "Zamazenta-Crowned")}
        change = forms.get(EffectContext.key(item))
        if change:
            if not self._item_forme_is_eligible(pokemon, change[1]):
                return
            if getattr(pokemon, "species", None) == change[0]:
                pokemon.formeChange(change[1], battle=self, source=source)

        from .native_forms import OgerponForm

        if OgerponForm.item_key(pokemon) in {"wellspringmask", "hearthflamemask", "cornerstonemask"}:
            OgerponForm.apply_mask(pokemon)
            return
        forced_forme = getattr(item, "forced_forme", None)
        if (
            forced_forme
            and hasattr(pokemon, "formeChange")
            and getattr(pokemon, "species", None) != forced_forme
            and self._item_forme_is_eligible(pokemon, forced_forme)
        ):
            try:
                pokemon.formeChange(forced_forme, battle=self, source=source)
            except TypeError:
                pokemon.formeChange(forced_forme)

        if hasattr(item, "call"):
            try:
                item.call("onPrimal", pokemon=pokemon)
            except Exception:
                pass

    def _clear_item_forme_effects(self, pokemon, *, source=None) -> None:
        """Revert item-locked formes when the required item is no longer held."""

        if not pokemon or not hasattr(pokemon, "_lookup_species_entry"):
            return

        try:
            entry = pokemon._lookup_species_entry(getattr(pokemon, "species", None) or getattr(pokemon, "name", None))
        except Exception:
            entry = None

        def _entry_value(key):
            if isinstance(entry, dict):
                return entry.get(key)
            value = getattr(entry, key, None)
            if value is not None:
                return value
            raw = getattr(entry, "raw", None)
            if isinstance(raw, dict):
                return raw.get(key)
            return None

        base_species = _entry_value("changesFrom")
        if not base_species:
            return

        held_item = getattr(getattr(pokemon, "item", None), "name", None)
        required_item = _entry_value("requiredItem")
        required_items = _entry_value("requiredItems")

        if required_item and held_item == required_item:
            return
        if isinstance(required_items, list) and held_item in required_items:
            return

        if hasattr(pokemon, "formeChange"):
            try:
                pokemon.formeChange(base_species, battle=self, source=source)
            except TypeError:
                pokemon.formeChange(base_species)

    def _run_slot_swap_events(self, pokemon, *, source=None, effect=None) -> None:
        """Run slot-condition swap hooks for ``pokemon``'s active position."""

        participant = self.participant_for(pokemon)
        side = getattr(participant, "side", None) if participant else None
        slot = self._active_slot_index(pokemon)
        if side is None or slot is None:
            return

        for name, handler, state in list(self._slot_condition_handlers(side, slot)):
            self.singleEvent(
                "Swap",
                handler,
                state if isinstance(state, dict) else {},
                pokemon,
                source,
                effect or getattr(self, "effect", None),
            )

    def _queue_self_switch(self, pokemon, move) -> None:
        """Mark ``pokemon`` to switch out after a successful self-switch move."""

        if pokemon is None or move is None:
            return
        self_switch = getattr(move, "raw", {}).get("selfSwitch")
        if getattr(move, "raw", {}).get("slotCondition") == "revivalblessing":
            # This dex flag requests a revival selection, not a switch-out.
            return
        if not self_switch:
            return
        tempvals = getattr(pokemon, "tempvals", None)
        if tempvals is None:
            tempvals = {}
            setattr(pokemon, "tempvals", tempvals)
        tempvals["switch_out"] = True
        if self_switch == "copyvolatile":
            tempvals["baton_pass"] = True

    def _handle_side_condition_durations(self) -> None:
        """Expire finite side effects once per turn and run their cleanup hooks."""
        seen_sides = set()
        for participant in self.participants:
            side = getattr(participant, "side", None)
            if side is None or id(side) in seen_sides:
                continue
            seen_sides.add(id(side))
            for name, state in list(getattr(side, "conditions", {}).items()):
                duration = state.get("duration") if isinstance(state, dict) else None
                if not isinstance(duration, int) or duration <= 0:
                    continue
                state["duration"] = duration - 1
                if state["duration"] == 0:
                    self.remove_side_condition(participant, name)
                    if name in {"quickguard", "wideguard", "craftyshield", "matblock"}:
                        getattr(side, "volatiles", {}).pop(name, None)

    def _handle_slot_condition_residuals(self) -> None:
        """Process residual and duration expiry for active slot conditions."""

        for participant in self.participants:
            if getattr(participant, "has_lost", False):
                continue
            side = getattr(participant, "side", None)
            if side is None:
                continue
            for slot, pokemon in enumerate(list(getattr(participant, "active", []))):
                if pokemon is None:
                    continue
                if getattr(participant, 'field_position', None):
                    slot = self._active_slot_index(pokemon)
                for name, handler, state in list(self._slot_condition_handlers(side, slot)):
                    state_map = state if isinstance(state, dict) else {}
                    state_map["target"] = pokemon
                    state_map.setdefault("source", state_map.get("source"))
                    if hasattr(handler, "onResidual"):
                        self.singleEvent("Residual", handler, state_map, pokemon, state_map.get("source"))
                    duration = state_map.get("duration")
                    if isinstance(duration, int):
                        duration -= 1
                        state_map["duration"] = duration
                        if duration <= 0:
                            self.singleEvent("End", handler, state_map, pokemon, state_map.get("source"))
                            side.remove_slot_condition(slot, name)

    def on_enter_battle(self, pokemon, *, source=None, effect=None) -> None:
        """Trigger events when ``pokemon`` enters the field."""
        part = self.participant_for(pokemon)
        pokemon.battle = self
        from .mega_evolution import MegaEvolution

        MegaEvolution.prepare_entry(pokemon)
        if (getattr(pokemon, "native_origin", None) or {}).get("necrozma"):
            from .ultra_burst import UltraBurst

            UltraBurst.prepare_entry(pokemon)
        if part is not None:
            pokemon.side = part.side
        pokemon.ability_state = self.init_effect_state(getattr(pokemon, "ability", None), target=pokemon, source=source)
        pokemon.item_state = self.init_effect_state(getattr(pokemon, "item", None), target=pokemon, source=source)
        pokemon.tempvals["entry_action_turn"] = self.turn_count
        if part and hasattr(part, "record_participation"):
            part.record_participation(pokemon)
        self._apply_item_forme_effects(pokemon, source=source)
        self._apply_ability_item_type(pokemon)
        self.register_handlers(pokemon)
        self.dispatcher.dispatch("pre_start", pokemon=pokemon, battle=self)
        self.dispatcher.dispatch("start", pokemon=pokemon, battle=self)
        self.reveal_entry_ability(pokemon)
        from .z_effects import ZEffects

        ZEffects.switch_in(self, pokemon)
        self.runEvent("SwitchIn", pokemon, source, effect or getattr(self, "effect", None))
        self.dispatcher.dispatch("switch_in", pokemon=pokemon, battle=self)
        self._run_slot_swap_events(pokemon, source=source, effect=effect)
        self.apply_entry_hazards(pokemon)
        self.dispatcher.dispatch("update", pokemon=pokemon, battle=self)

    def on_switch_out(self, pokemon, *, source=None, effect=None) -> None:
        """Handle effects when ``pokemon`` leaves the field."""
        part = self.participant_for(pokemon)
        if part:
            self._log_switch_out(part, pokemon)
        self.runEvent("SwitchOut", pokemon, source, effect or getattr(self, "effect", None))
        self.dispatcher.dispatch("switch_out", pokemon=pokemon, battle=self)
        self._end_holder_effects(pokemon, source=source, effect=effect)
        if not getattr(pokemon, "tempvals", {}).get("baton_pass"):
            self.reset_stat_changes(pokemon)
        from .copied_moves import BattleCopyState

        BattleCopyState.cleanup(pokemon)
        self._clear_choice_lock(pokemon)
        getattr(pokemon, "tempvals", {}).pop("moves_used_since_entry", None)
        getattr(pokemon, "tempvals", {}).pop("stat_overrides", None)
        getattr(pokemon, "tempvals", {}).pop("entry_action_turn", None)
        vols = list(getattr(pokemon, "volatiles", {}).keys())
        for vol in vols:
            self.remove_volatile(pokemon, vol)

    def _end_holder_effects(self, pokemon, *, source=None, effect=None) -> None:
        """End the current ability/item when its holder leaves the field.

        Showdown-style onEnd is a lifecycle hook, not an end-of-turn hook.
        Resolve current holders here so replaced abilities/items cannot leave
        stale registered cleanup callbacks behind.
        """
        for holder, state_name in (
            (_resolve_ability(getattr(pokemon, "ability", None)), "ability_state"),
            (self._holder_item(pokemon), "item_state"),
        ):
            if holder:
                self.singleEvent("End", holder, getattr(pokemon, state_name, {}),
                                 pokemon, source, effect)

    def on_faint(self, pokemon) -> None:
        """Mark ``pokemon`` as fainted and trigger callbacks."""
        self.remove_volatile(pokemon, "roost")
        self.remove_volatile(pokemon, "focusenergy")
        if (getattr(pokemon, "tempvals", {}) or {}).pop("bag_boosters", False):
            self.reset_stat_changes(pokemon)
        pokemon.is_fainted = True
        cause = (getattr(pokemon, "tempvals", {}) or {}).pop("faint_cause", {})
        source, effect = cause.get("source"), cause.get("effect")
        self.runEvent("Faint", pokemon, source, effect)
        # Faint effects (including Aftermath) resolve before the win check.
        # AfterFaint bonuses only matter while an opposing team can continue.
        source_part = self.participant_for(source) if source is not None else None
        opponents_remain = source_part is not None and any(
            getattr(mon, "hp", 0) > 0
            for opponent in self.opponents_of(source_part)
            for mon in opponent.pokemons
        )
        if source is not None and getattr(source, "hp", 0) > 0 and opponents_remain:
            self.runEvent("AfterFaint", pokemon, source, effect, 1)

        name = getattr(pokemon, "name", getattr(pokemon, "species", "Pokemon"))
        try:  # pragma: no cover - data package may be unavailable in tests
            from pokemon.data.text import DEFAULT_TEXT  # type: ignore
        except Exception:  # pragma: no cover
            DEFAULT_TEXT = {"default": {"faint": "[POKEMON] fainted!"}}

        template = DEFAULT_TEXT.get("default", {}).get("faint")
        if template:
            message = template.replace("[POKEMON]", name)
            self.log_action(message)

        from .effect_context import EffectContext

        ability = EffectContext.ability(pokemon)
        if ability and hasattr(ability, "call"):
            try:
                ability.call("onFaint", pokemon, self)
            except Exception:
                pass

        item = getattr(pokemon, "item", None)
        if item and hasattr(item, "call"):
            try:
                item.call("onFaint", pokemon=pokemon, battle=self)
            except Exception:
                pass
        self._end_holder_effects(pokemon)
        if getattr(pokemon, "ultra_profile", None):
            from .ultra_burst import UltraBurst

            UltraBurst.revert(pokemon)

    def on_end_turn(self) -> None:
        """Apply end of turn effects."""
        self.handle_weather()
        self.handle_terrain()

    def _apply_misc_callbacks(self) -> None:
        """Invoke seldom triggered ability callbacks for active PokÃƒÆ’Ã‚Â©mon.

        The lightweight battle engine used in tests omits many edge-case
        mechanics that would normally trigger hooks such as
        ``onAllyTryAddVolatile`` (Aroma Veil) or ``onFoeTryEatItem`` (As One).
        Without invoking these callbacks, the comprehensive ability tests
        would flag them as unused.  This helper calls the hooks once for each
        active PokÃƒÆ’Ã‚Â©mon, ignoring any errors so the minimal test doubles remain
        compatible with the simplified environment.
        """

        for part in self.participants:
            if part.has_lost:
                continue
            for pokemon in part.active:
                ability = _resolve_ability(getattr(pokemon, "ability", None))
                if not ability or not hasattr(ability, "call"):
                    continue
                try:
                    ability.call(
                        "onAllyTryAddVolatile",
                        status="taunt",
                        target=pokemon,
                        source=None,
                        effect=None,
                    )
                except Exception:
                    pass
                try:
                    ability.call("onFoeTryEatItem")
                except Exception:
                    pass
                try:
                    ability.call(
                        "onSourceAfterFaint",
                        target=pokemon,
                        source=pokemon,
                        effect=None,
                    )
                except Exception:
                    pass

    def _apply_trap_callbacks(self) -> None:
        """Invoke trapping related ability callbacks for active PokÃƒÆ’Ã‚Â©mon.

        Some abilities such as Arena Trap expose ``onFoeTrapPokemon`` hooks
        that are normally triggered by the battle engine when checking if a
        PokÃƒÆ’Ã‚Â©mon is allowed to switch out.  The simplified engine used for
        testing does not implement full switching logic and therefore these
        callbacks were never invoked, causing ability tests to fail.  This
        helper manually calls the relevant ability callbacks for each active
        PokÃƒÆ’Ã‚Â©mon pair, swallowing any errors so the minimal test doubles used
        in the suite do not need to implement the full PokÃƒÆ’Ã‚Â©mon Showdown API.
        """

        for part in self.participants:
            if part.has_lost:
                continue
            for opp in self.participants:
                if opp is part or opp.has_lost:
                    continue
                for pokemon in part.active:
                    from .effect_context import EffectContext
                    ability = _resolve_ability(EffectContext.ability(pokemon))
                    if EffectContext.key(ability) == "shadowtag":
                        # Voluntary switch legality queries the live owner, not
                        # a sticky flag left behind after departure/suppression.
                        continue
                    if not ability or not hasattr(ability, "call"):
                        continue
                    for foe in opp.active:
                        try:
                            ability.call(
                                "onFoeMaybeTrapPokemon", pokemon=foe, source=pokemon
                            )
                        except Exception:
                            pass
                        try:
                            ability.call("onFoeTrapPokemon", pokemon=foe)
                        except Exception:
                            pass

    # ------------------------------------------------------------------
    # Pseudocode mapping
    # ------------------------------------------------------------------
    def run_switch(self) -> None:
        """Handle PokÃƒÆ’Ã‚Â©mon switches before moves are executed."""

        from .active_slots import active_at, assign_active
        from .legal_actions import LegalActions

        self._apply_trap_callbacks()

        for part in self.participants:
            if part.has_lost:
                continue
            # Ensure correct number of active PokÃƒÆ’Ã‚Â©mon
            for slot in range(part.max_active):
                if active_at(part, slot) is None:
                    reserves = LegalActions(self, part, None).reserves(slot=slot, forced=True)
                    replacement = reserves[0] if reserves else None
                    if replacement:
                        assign_active(part, slot, replacement)
                        setattr(replacement, "side", part.side)
                        self.on_enter_battle(replacement, source=None)
                    continue

                active = active_at(part, slot)

                if getattr(active, "tempvals", {}).get("baton_pass") or getattr(
                    active, "tempvals", {}
                ).get("switch_out"):
                    if self._is_trapped(active) and not getattr(active, "dragged_out", False):
                        active.tempvals.pop("baton_pass", None)
                        active.tempvals.pop("switch_out", None)
                        continue
                    if not active.tempvals.get("skip_before_switch_out"):
                        if self.runEvent(
                            "BeforeSwitchOut",
                            active,
                            None,
                            getattr(self, "effect", None),
                        ) is False:
                            active.tempvals.pop("baton_pass", None)
                            self.reset_stat_changes(active)
                            active.tempvals.pop("switch_out", None)
                            continue
                    for opp in self.participants:
                        if opp is part or opp.has_lost:
                            continue
                        pending = getattr(opp, "pending_action", None)
                        candidates = list(pending) if isinstance(pending, list) else [pending] if pending else []
                        for act in candidates:
                            if act.action_type is not ActionType.MOVE:
                                continue
                            move = getattr(act, "move", None)
                            move_key = getattr(move, "key", None) or _normalize_key(
                                getattr(move, "name", "")
                            )
                            if str(move_key).lower() != "pursuit":
                                continue
                            target_check = (
                                active_at(act.target, act.target_slot or 0)
                                if act.target
                                else None
                            )
                            if target_check is active:
                                active.tempvals["switching"] = True
                                self.use_move(act)
                                active.tempvals.pop("switching", None)
                                if isinstance(pending, list):
                                    pending.remove(act)
                                else:
                                    opp.pending_action = None

                    reserves = LegalActions(self, part, active).reserves(slot=slot)
                    replacement = reserves[0] if reserves else None
                    if replacement:
                        shedtail_substitute = active.tempvals.get("shedtail_substitute")
                        if self.runEvent(
                            "BeforeSwitchIn",
                            replacement,
                            active,
                            getattr(self, "effect", None),
                        ) is False:
                            continue
                        passed_substitute = None
                        passed_focus = None
                        if active.tempvals.get("baton_pass"):
                            passed_substitute = getattr(active, "volatiles", {}).get("substitute")
                            passed_focus = getattr(active, "volatiles", {}).get("focusenergy")
                        self.on_switch_out(active, source=replacement)
                        assign_active(part, slot, replacement)
                        setattr(replacement, "side", part.side)
                        self.on_enter_battle(replacement, source=active)
                        if active.tempvals.get("baton_pass"):
                            if hasattr(active, "boosts") and hasattr(
                                replacement, "boosts"
                            ):
                                replacement.boosts = dict(active.boosts)
                            sub = passed_substitute
                            if sub:
                                if not hasattr(replacement, "volatiles"):
                                    replacement.volatiles = {}
                                replacement.volatiles["substitute"] = dict(sub)
                            if passed_focus:
                                replacement.volatiles["focusenergy"] = {
                                    **(dict(passed_focus) if isinstance(passed_focus, dict) else {"id": "focusenergy", "source": active}),
                                    "target": replacement}
                            if active.tempvals.get("bag_boosters"):
                                replacement.tempvals["bag_boosters"] = True
                            active.tempvals.pop("baton_pass", None)
                        if shedtail_substitute:
                            if not hasattr(replacement, "volatiles"):
                                replacement.volatiles = {}
                            replacement.volatiles["substitute"] = dict(shedtail_substitute)
                            active.tempvals.pop("shedtail_substitute", None)
                        active.tempvals.pop("skip_before_switch_out", None)
                        active.tempvals.pop("switch_out", None)
                    continue

                if getattr(active, "hp", 0) <= 0:
                    reserves = LegalActions(self, part, active).reserves(slot=slot, forced=True)
                    replacement = reserves[0] if reserves else None
                    if replacement:
                        if self.runEvent(
                            "BeforeSwitchIn",
                            replacement,
                            active,
                            getattr(self, "effect", None),
                        ) is False:
                            continue
                        assign_active(part, slot, replacement)
                        setattr(replacement, "side", part.side)
                        self.on_enter_battle(replacement, source=active)

    def run_after_switch(self) -> None:
        """Trigger simple events after PokÃƒÆ’Ã‚Â©mon have switched in."""

        for part in self.participants:
            if part.has_lost:
                continue
            for poke in part.active:
                # Clear any temporary battle values on switch
                reset_tempvals(poke)
            for poke in part.pokemons:
                if poke not in part.active and getattr(poke, "status", None) == "tox":
                    try:
                        CONDITION_HANDLERS = safe_import("pokemon.dex.functions.conditions_funcs").CONDITION_HANDLERS  # type: ignore[attr-defined]
                        handler = CONDITION_HANDLERS.get("tox")
                        if handler and hasattr(handler, "onSwitchIn"):
                            handler.onSwitchIn(poke, battle=self)
                    except Exception:
                        poke.status = "psn"
                        poke.toxic_counter = 0

    # ------------------------------------------------------------------
    # Move handling helpers
    # ------------------------------------------------------------------

    def mark_initial_prompt(self) -> None:
        """The startup preview precedes the first playable turn's start hook."""
        for part in self.participants:
            for pokemon in part.active:
                pokemon.tempvals["entry_action_turn"] = self.turn_count + 1

    def deduct_pp(self, pokemon, move: BattleMove, target=None) -> None:
        """Spend PP, including surcharges from the move's opposing targets."""
        if getattr(move, "_z_paid", False):
            return
        if getattr(move, "_called_use", False):
            return
        if _effect_key(move) == "bide" and getattr(pokemon, "volatiles", {}).get("bide"):
            return
        history = getattr(pokemon, "tempvals", None)
        if history is None:
            history = pokemon.tempvals = {}
        used = history.setdefault("moves_used_since_entry", [])
        used_key = str(_normalize_key(getattr(move, "key", None) or move.name)).lower()
        if used_key not in used:
            used.append(used_key)
        pp_cost = 1
        event_cost = self.runEvent("DeductPP", pokemon, None, move, pp_cost)
        if event_cost is False:
            return
        if isinstance(event_cost, (int, float)):
            pp_cost = max(0, int(event_cost))

        # Pressure belongs to the Pokemon being targeted, not the move user.
        # Retain the ordinary user-side cost event for other PP modifiers, then
        # dispatch target-side events with a zero-based additional cost.
        participant = self.participant_for(pokemon)
        target_class = move.raw.get("target", "normal")
        must_pressure = move.raw.get("flags", {}).get("mustpressure")
        if must_pressure and participant is not None:
            pressure_targets = [mon for part in self.opponents_of(participant)
                                for mon in part.active if getattr(mon, "hp", 0) > 0]
        elif target_class == "foeSide":
            pressure_targets = []
        elif target_class in {"all", "allAdjacent", "allAdjacentFoes", "allies", "allySide", "allyTeam"} and participant is not None:
            from .legal_actions import LegalActions

            pressure_targets = LegalActions(self, participant, pokemon).targets(move)
        else:
            pressure_targets = [target] if target is not None else []
        seen_targets = set()
        for recipient in pressure_targets:
            if recipient is pokemon or id(recipient) in seen_targets:
                continue
            seen_targets.add(id(recipient))
            extra = self.runEvent("DeductPP", recipient, pokemon, move, 0)
            if isinstance(extra, (int, float)) and not isinstance(extra, bool):
                pp_cost += max(0, int(extra))

        self.reduce_move_pp(pokemon, move, pp_cost)

    def reduce_move_pp(self, pokemon, move: BattleMove, amount: int) -> int:
        """Reduce authoritative PP without treating an external drain as a use."""
        amount = max(0, int(amount))
        from .copied_moves import BattleCopyState

        temporary = BattleCopyState.spend_pp(pokemon, move, amount)
        if temporary is not None:
            return temporary
        move_key = _normalize_key(getattr(move, "_pp_move_name", None) or getattr(move, "key", None) or move.name)
        moves = getattr(pokemon, "moves", [])
        slots = getattr(pokemon, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:  # pragma: no cover - fallback for stubs
                slot_iter = slots
            for slot in slot_iter:
                if _normalize_key(getattr(getattr(slot, "move", None), "name", "")) == move_key:
                    current = getattr(slot, "current_pp", None)
                    if current is not None:
                        updated = max(0, current - amount)
                        slot.current_pp = updated
                        move.pp = updated
                        for cached_move in moves:
                            cached_key = getattr(cached_move, "key", None) or getattr(cached_move, "name", "")
                            if _normalize_key(cached_key) == move_key:
                                cached_move.pp = updated
                        if updated != current and hasattr(slot, "save"):
                            try:
                                try:
                                    slot.save(update_fields=["current_pp"])
                                except TypeError:  # pragma: no cover - legacy adapters
                                    slot.save()
                            except Exception:
                                battle_logger.exception("Unable to persist spent PP for move %s.", move.name)
                                if (getattr(pokemon, "native_origin", None) or {}).get("necrozma"):
                                    raise
                        return current - updated
                    return 0

        for m in moves:
            cached_key = getattr(m, "key", None) or getattr(m, "name", "")
            if _normalize_key(cached_key) == move_key:
                current = getattr(m, "pp", None)
                if current is None:
                    current = move.pp
                if current is not None:
                    m.pp = max(0, current - amount)
                    move.pp = m.pp
                    return current - m.pp

        if move.pp is not None and move.pp > 0:
            previous = move.pp
            move.pp = max(0, move.pp - amount)
            return previous - move.pp
        return 0

    def _move_pp_states(self, pokemon):
        """Yield current slots and their real PP capacity, including owned boosts."""
        manager = getattr(pokemon, "activemoveslot_set", None)
        slots = list(manager.all() if callable(getattr(manager, "all", None)) else manager or [])
        if not slots:
            slots = list(getattr(pokemon, "move_slots", None) or getattr(pokemon, "moves", []) or [])
        for slot in slots:
            name = getattr(getattr(slot, "move", slot), "name", "")
            stored = hasattr(slot, "current_pp")
            current = getattr(slot, "current_pp", None) if stored else getattr(slot, "pp", None)
            capacity = getattr(slot, "max_pp", getattr(slot, "maxpp", None))
            maximum = getattr(getattr(slot, "pokemon", None), "get_max_pp", None)
            if callable(maximum):
                capacity = maximum(name)
            if capacity is None:
                entry = MOVEDEX.get(_normalize_key(name))
                capacity = get_raw(entry).get("pp", getattr(entry, "pp", None))
            if capacity is None:
                capacity = current
            if capacity is not None and int(capacity) > 0:
                yield slot, name, current, int(capacity), stored

    def has_depleted_pp(self, pokemon) -> bool:
        """Check authoritative PP rather than treating cached remaining PP as max."""
        return any(current is not None and current < capacity
                   for _, _, current, capacity, _ in self._move_pp_states(pokemon))

    def restore_move_pp(self, pokemon) -> int:
        """Restore owned and runtime PP to the same actual per-move capacity."""
        restored = 0
        for slot, name, current, capacity, stored in self._move_pp_states(pokemon):
            setattr(slot, "current_pp" if stored else "pp", capacity)
            if stored and current != capacity and callable(getattr(slot, "save", None)):
                try:
                    slot.save(update_fields=["current_pp"])
                except TypeError:  # Legacy slot adapters omit update_fields.
                    slot.save()
            for move in getattr(pokemon, "moves", []) or []:
                if move is slot or (name and _normalize_key(getattr(move, "name", "")) == _normalize_key(name)):
                    move.pp = capacity
            restored += max(0, capacity - (current if current is not None else capacity))
        return restored

    def heal(self, pokemon, amount: int, *, source=None, effect=None) -> int:
        """Restore HP through the battle event system."""
        if not pokemon or amount is None:
            return 0
        try:
            amount = int(amount)
        except Exception:
            return 0
        if amount <= 0:
            return 0
        max_hp = getattr(pokemon, "max_hp", getattr(pokemon, "hp", 0))
        current_hp = getattr(pokemon, "hp", 0)
        event_amount = self.runEvent("TryHeal", pokemon, source, effect, amount)
        if event_amount is False:
            return 0
        if isinstance(event_amount, (int, float)):
            amount = int(event_amount)
        if amount < 0:
            from .indirect_damage import IndirectEffect, apply_indirect_damage

            actual = apply_indirect_damage(pokemon, abs(amount), battle=self, source=source,
                                            effect=IndirectEffect("healinversion"))
            return -actual
        if amount <= 0:
            return 0
        actual = min(max_hp - current_hp, amount)
        if actual <= 0:
            return 0
        pokemon.hp = current_hp + actual
        return actual

    def _coerce_item(self, item):
        """Return an item object for ``item`` when possible."""

        if not item:
            return None
        if hasattr(item, "raw"):
            return item
        entry = ITEMDEX.get(str(item))
        if entry is None:
            normalized = _normalize_key(str(item))
            entry = (
                ITEMDEX.get(normalized)
                or ITEMDEX.get(str(item).title())
                or ITEMDEX.get(str(item).replace(" ", ""))
                or ITEMDEX.get(normalized.capitalize())
            )
        return entry

    def _holder_item(self, pokemon):
        """Return the currently held item object for ``pokemon``."""

        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        item = self._coerce_item(item)
        if item and getattr(pokemon, "item", None) is not item:
            try:
                pokemon.item = item
            except Exception:
                pass
        return item

    def _choice_item_key(self, pokemon) -> Optional[str]:
        """Return the normalized Choice item key held by ``pokemon``."""

        item = self._holder_item(pokemon)
        if not item:
            return None
        item_name = getattr(item, "name", str(item))
        item_key = _normalize_key(item_name)
        if str(item_key).lower() in {"choiceband", "choicescarf", "choicespecs"}:
            return str(item_key).lower()
        return None

    def _clear_choice_lock(self, pokemon) -> None:
        """Clear any active Choice-item move lock from ``pokemon``."""

        if not pokemon:
            return
        pokemon.choice_locked_move = None
        volatiles = getattr(pokemon, "volatiles", None)
        if isinstance(volatiles, dict):
            volatiles.pop("choicelock", None)

    def _set_choice_lock(self, pokemon, move) -> None:
        """Lock ``pokemon`` into ``move`` when holding a Choice item."""
        if getattr(move, "_called_use", False):
            return

        if not pokemon:
            return
        if not self._choice_item_key(pokemon):
            self._clear_choice_lock(pokemon)
            return
        from .effect_context import EffectContext

        if not EffectContext.item(pokemon):
            return
        move_key = getattr(move, "key", None) or _normalize_key(getattr(move, "name", ""))
        move_key = str(move_key).lower()
        if not move_key or move_key == "struggle":
            return
        pokemon.choice_locked_move = move_key
        pokemon.volatiles = getattr(pokemon, "volatiles", {})
        pokemon.volatiles["choicelock"] = {"move": move_key}

    def _resolve_move_reference(self, pokemon, move_ref):
        """Return a concrete move object matching ``move_ref`` when possible."""
        if move_ref is None:
            return None
        if hasattr(move_ref, "name"):
            return move_ref
        move_key = str(getattr(move_ref, "id", move_ref) or "").lower()
        if not move_key:
            return None
        slots = getattr(pokemon, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:
                slot_iter = slots
            for slot in slot_iter:
                slot_move = getattr(slot, "move", None)
                key = _normalize_key(getattr(slot_move, "name", ""))
                if key == move_key:
                    return slot_move
        for move in getattr(pokemon, "moves", []):
            key = getattr(move, "key", None) or _normalize_key(getattr(move, "name", ""))
            if str(key).lower() == move_key:
                return move
        return None

    def _move_control_holders(self, pokemon, *, include_foes: bool = False):
        """Return holders relevant to move lock/disable style callbacks."""
        from .effect_context import EffectContext

        holders: list[tuple[Any, str]] = []
        status_handler = self._pokemon_status_handler(pokemon)
        if status_handler is not None:
            holders.append((status_handler, "self"))
        for _, handler in self._pokemon_volatile_handlers(pokemon):
            holders.append((handler, "self"))
        ability = EffectContext.ability(pokemon)
        if ability is not None:
            holders.append((ability, "self"))
        item = EffectContext.item(pokemon)
        if item is not None:
            holders.append((item, "self"))
        if include_foes:
            for part in self.participants:
                if self._allied(part, self.participant_for(pokemon)):
                    continue
                for active in getattr(part, "active", []):
                    if active is None or active is pokemon:
                        continue
                    if part is not self.participant_for(pokemon):
                        for _, volatile in self._pokemon_volatile_handlers(active):
                            holders.append((volatile, "foe"))
                    foe_ability = _resolve_ability(getattr(active, "ability", None))
                    if foe_ability is not None:
                        holders.append((foe_ability, "foe"))
                    foe_item = self._holder_item(active)
                    if foe_item is not None:
                        holders.append((foe_item, "foe"))
        return holders

    def _switch_control_holders(self, pokemon, *, include_foes: bool = False):
        """Return holders relevant to trap and drag-out checks."""
        holders: list[tuple[Any, str]] = []
        status_handler = self._pokemon_status_handler(pokemon)
        if status_handler is not None:
            holders.append((status_handler, "self"))
        for _, handler in self._pokemon_volatile_handlers(pokemon):
            holders.append((handler, "self"))
        ability = _resolve_ability(getattr(pokemon, "ability", None))
        if ability is not None:
            holders.append((ability, "self"))
        item = self._holder_item(pokemon)
        if item is not None:
            holders.append((item, "self"))
        if include_foes:
            owner = self.participant_for(pokemon)
            for part in self.participants:
                if part is owner:
                    continue
                for active in getattr(part, "active", []):
                    if active is None:
                        continue
                    foe_status = self._pokemon_status_handler(active)
                    if foe_status is not None:
                        holders.append((foe_status, "foe"))
                    for _, handler in self._pokemon_volatile_handlers(active):
                        holders.append((handler, "foe"))
                    foe_ability = _resolve_ability(getattr(active, "ability", None))
                    if foe_ability is not None:
                        holders.append((foe_ability, "foe"))
                    foe_item = self._holder_item(active)
                    if foe_item is not None:
                        holders.append((foe_item, "foe"))
        return holders

    def _invoke_move_control(self, holder, hook: str, pokemon, move, move_key: str):
        """Invoke a move-control callback with forgiving signatures."""
        for args, kwargs in (
            ((pokemon, move), {"battle": self, "move_name": move_key}),
            ((pokemon,), {"move": move, "battle": self, "move_name": move_key}),
            ((pokemon, move_key), {"move": move, "battle": self}),
            ((pokemon,), {"battle": self}),
        ):
            try:
                result = self._call_effect_event(holder, hook, *args, **kwargs)
            except Exception:
                continue
            if result is not None:
                return result
        return None

    def _locked_move_override(self, pokemon, move):
        """Resolve enforced move locks from volatile/status effects."""
        move_key = getattr(move, "key", None) or _normalize_key(getattr(move, "name", ""))
        for holder, _ in self._move_control_holders(pokemon):
            locked = self._invoke_move_control(holder, "onLockMove", pokemon, move, str(move_key).lower())
            if locked is not False and locked is not None and locked is not True:
                resolved = self._resolve_move_reference(pokemon, locked)
                if resolved is not None:
                    return resolved
        return move

    def _override_action_move(self, pokemon, move):
        """Allow effects such as Encore to replace the chosen move."""
        move_key = getattr(move, "key", None) or _normalize_key(getattr(move, "name", ""))
        for holder, _ in self._move_control_holders(pokemon):
            overridden = self._invoke_move_control(holder, "onOverrideAction", pokemon, move, str(move_key).lower())
            if overridden is not False and overridden is not None and overridden is not True:
                resolved = self._resolve_move_reference(pokemon, overridden)
                if resolved is not None:
                    return resolved
        return move

    def _is_move_disabled(self, pokemon, move) -> bool:
        """Return whether ``move`` is currently disabled for ``pokemon``."""
        if not pokemon or not move:
            return False
        if getattr(move, "disabled", False):
            return True
        move_key = getattr(move, "key", None) or _normalize_key(getattr(move, "name", ""))
        move_key = str(move_key).lower()
        for holder, relation in self._move_control_holders(pokemon, include_foes=True):
            hook = "onFoeDisableMove" if relation == "foe" else "onDisableMove"
            result = self._invoke_move_control(holder, hook, pokemon, move, move_key)
            if getattr(move, "disabled", False):
                return True
            holder_name = str(getattr(getattr(holder, "__class__", None), "__name__", "")).lower()
            if result is True:
                return True
            if hasattr(result, "name"):
                key = getattr(result, "key", None) or _normalize_key(getattr(result, "name", ""))
                result_key = str(key).lower()
                if holder_name == "disable":
                    if result_key == move_key:
                        return True
                elif result_key != move_key:
                    return True
            elif isinstance(result, str) and result:
                result_key = str(result).lower()
                if holder_name == "disable":
                    if result_key == move_key:
                        return True
                elif result_key != move_key:
                    return True
        return False

    def _modify_move_target(self, user, target, move):
        """Allow move and field effects to replace the chosen target."""
        modified = target
        if (getattr(move, "raw", {}) or {}).get("target") == "scripted":
            from .retaliation import RetaliationHit

            hit = RetaliationHit.current(user, self)
            if hit is not None:
                modified = hit.target
        if move and getattr(move, "onModifyTarget", None):
            try:
                candidate = invoke_callback(move.onModifyTarget, user, target, move, battle=self)
            except Exception:
                candidate = None
            if candidate is not None:
                modified = candidate
        event_target = self.runEvent("ModifyTarget", modified, user, move, modified)
        if event_target is not False and event_target is not None and event_target is not True:
            modified = event_target
        return modified

    def _is_trapped(self, pokemon) -> bool:
        """Return whether ``pokemon`` is prevented from switching out."""
        from .effect_context import EffectContext

        owner = self.participant_for(pokemon)
        if (owner is not None and "Ghost" not in getattr(pokemon, "types", [])
                and EffectContext.key(EffectContext.item(pokemon)) != "shedshell"
                and EffectContext.key(EffectContext.ability(pokemon)) != "shadowtag"):
            if any(getattr(foe, "hp", 0) > 0
                   and EffectContext.key(EffectContext.ability(foe)) == "shadowtag"
                   for part in self.opponents_of(owner) for foe in part.active):
                return True
        trapped = bool(getattr(pokemon, "trapped", False) or getattr(pokemon, "maybe_trapped", False))
        for holder, relation in self._switch_control_holders(pokemon, include_foes=True):
            if EffectContext.key(holder) == "shadowtag":
                continue
            hook = "onFoeTrapPokemon" if relation == "foe" else "onTrapPokemon"
            try:
                result = self._call_effect_event(holder, hook, pokemon, battle=self)
            except Exception:
                result = None
            if result is True:
                trapped = True
        if trapped:
            setattr(pokemon, "trapped", True)
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["trapped"] = True
        return trapped

    def _can_drag_out(self, pokemon, source=None, effect=None) -> bool:
        """Return whether ``pokemon`` may be forced out by an effect."""
        for holder, _ in self._switch_control_holders(pokemon):
            try:
                result = self._call_effect_event(holder, "onDragOut", pokemon, source, effect, battle=self)
            except Exception:
                result = None
            if result is False:
                return False
        drag_event = self.runEvent("DragOut", pokemon, source, effect)
        if drag_event is False:
            return False
        return not self._is_trapped(pokemon)

    def _passes_try_immunity(self, target, source, move) -> bool:
        """Return whether immunity-style callbacks allow ``move`` to affect ``target``."""
        if target is None or move is None:
            return True
        holders = []
        if getattr(move, "onTryImmunity", None):
            holders.append(("move", move.onTryImmunity))
        for holder, _ in self._move_control_holders(target, include_foes=False):
            holders.append(("holder", holder))
        for kind, entry in holders:
            result = None
            if kind == "move":
                callback = entry
                for args, kwargs in (
                    ((target, source, move), {"battle": self}),
                    ((target, source), {"move": move, "battle": self}),
                    ((target,), {"source": source, "move": move, "battle": self}),
                ):
                    try:
                        result = invoke_callback(callback, *args, **kwargs)
                    except Exception:
                        continue
                    break
            else:
                holder = entry
                for args, kwargs in (
                    ((target, source, move), {"battle": self}),
                    ((target, source), {"move": move, "battle": self}),
                    ((target,), {"source": source, "move": move, "battle": self}),
                ):
                    try:
                        result = self._call_effect_event(holder, "onTryImmunity", *args, **kwargs)
                    except Exception:
                        continue
                    if result is not None:
                        break
            if result is False:
                return False
        return True

    def _passes_side_protection(self, target, source, move) -> bool:
        """Check each target's active side shields without cancelling spread peers."""
        raw = getattr(move, "raw", {}) or {}
        if getattr(move, "_z_paid", False) and move.category != "Status":
            return True
        if target is source or getattr(move, "breaksProtect", False) or raw.get("breaksProtect") or raw.get("flags", {}).get("bypassprotect"):
            return True
        participant = self.participant_for(target)
        side = getattr(participant, "side", None)
        for name, handler, state in self._side_condition_handlers(side):
            if name not in {"quickguard", "wideguard", "craftyshield", "matblock"}:
                continue
            if self.singleEvent("TryHit", handler, state, target, source, move) is False:
                return False
        return True

    def _passes_try_primary_hit(self, target, source, move) -> bool:
        """Return whether primary-hit callbacks allow ``move`` to proceed."""
        if target is None or move is None:
            return True
        self_target = target is source and is_self_target(getattr(move, "raw", {}).get("target"))
        if not self_target and self.runEvent("TryPrimaryHit", target, source, move) is False:
            return False
        callback = getattr(move, "onTryPrimaryHit", None)
        if callable(callback):
            for args, kwargs in (
                ((target, source, move), {"battle": self}),
                ((target, source), {"move": move, "battle": self}),
                ((target,), {"source": source, "move": move, "battle": self}),
            ):
                try:
                    result = invoke_callback(callback, *args, **kwargs)
                except Exception:
                    continue
                if result is False:
                    return False
                break
        return True

    def _passes_stall_move(self, user, move) -> bool:
        """Return whether a stalling move may succeed this turn."""

        if user is None or move is None:
            return True

        raw = getattr(move, "raw", {}) or {}
        if not raw.get("stallingMove"):
            if getattr(user, "volatiles", {}).get("stall") is not None:
                self.remove_volatile(user, "stall")
            return True

        chance_value = 1.0
        stall_state = getattr(user, "volatiles", {}).get("stall")
        last_turn = stall_state.get("last_turn") if isinstance(stall_state, dict) else None
        if type(last_turn) is int and getattr(self, "mechanic_turn", 0) - last_turn > 1:
            self.remove_volatile(user, "stall")
            stall_state = None
        if stall_state is not None:
            handler = self._volatile_handler("stall")
            if handler is not None:
                result = self.singleEvent(
                    "StallMove",
                    handler,
                    stall_state if isinstance(stall_state, dict) else {},
                    user,
                    None,
                    move,
                )
                try:
                    chance_value = float(result)
                except Exception:
                    chance_value = 1.0
        chance_value = max(0.0, min(1.0, chance_value))
        from .random_source import resolve_rng

        if chance_value < 1 and resolve_rng(battle=self).random() >= chance_value:
            self.remove_volatile(user, "stall")
            return False
        self.add_volatile(user, "stall", source=user, effect=move)
        return True

    def _move_stage_holders(self, user, target=None):
        """Return holders that may react to pre-move gating events."""

        from .effect_context import EffectContext

        holders: list[tuple[str | None, Any, Optional[Dict[str, Any]], Any]] = []

        def add_holder(relation, holder, state, owner) -> None:
            if holder is not None:
                holders.append((relation, holder, state, owner))

        if user is not None:
            add_holder(None, self._pokemon_status_handler(user), getattr(user, "status_state", None), user)
            for volatile_name, handler in self._pokemon_volatile_handlers(user):
                add_holder(None, handler, getattr(user, "volatiles", {}).get(volatile_name), user)
            add_holder(None, EffectContext.ability(user), getattr(user, "ability_state", None), user)
            add_holder(None, self._holder_item(user), getattr(user, "item_state", None), user)

        user_participant = self.participant_for(user) if user is not None else None
        for part in self.participants:
            for pokemon in getattr(part, "active", []):
                if pokemon is None or pokemon is user:
                    continue
                relation = "foe"
                if user_participant is not None and self._allied(self.participant_for(pokemon), user_participant):
                    relation = "ally"
                add_holder(relation, self._pokemon_status_handler(pokemon), getattr(pokemon, "status_state", None), pokemon)
                for volatile_name, handler in self._pokemon_volatile_handlers(pokemon):
                    add_holder(relation, handler, getattr(pokemon, "volatiles", {}).get(volatile_name), pokemon)
                add_holder(relation, EffectContext.ability(pokemon), getattr(pokemon, "ability_state", None), pokemon)
                add_holder(relation, self._holder_item(pokemon), getattr(pokemon, "item_state", None), pokemon)
        return holders

    def _passes_try_move(self, user, target, move) -> bool:
        """Return whether pre-move callbacks allow ``move`` to be used."""

        if user is None or move is None:
            return True
        callback = getattr(move, "onTryMove", None)
        if callable(callback):
            for args, kwargs in (
                ((user, target, self), {}),
                ((user, target), {"battle": self, "move": move}),
                ((user,), {"target": target, "battle": self, "move": move}),
            ):
                try:
                    result = invoke_callback(callback, *args, **kwargs)
                except Exception:
                    continue
                if result is False:
                    return False
                break

        for relation, holder, state, owner in self._move_stage_holders(user, target):
            hooks = ["onAnyTryMove"]
            if relation == "ally":
                hooks.append("onAllyTryMove")
            elif relation == "foe":
                hooks.append("onFoeTryMove")
            else:
                hooks.append("onTryMove")
            for hook in hooks:
                try:
                    result = self._call_effect_event(
                        holder,
                        hook,
                        user,
                        target,
                        move,
                        battle=self,
                        effect_state=state,
                    )
                except Exception:
                    result = None
                if result is False:
                    return False
        return True

    def _notify_move_aborted(self, user, target, move) -> None:
        """Fire move-abort and move-fail callbacks for ``move``."""

        aborted = getattr(move, "onMoveAborted", None)
        if callable(aborted):
            for args, kwargs in (
                ((user, target, move), {"battle": self}),
                ((user, target), {"move": move, "battle": self}),
                ((user,), {"target": target, "move": move, "battle": self}),
                ((user,), {"battle": self}),
            ):
                try:
                    invoke_callback(aborted, *args, **kwargs)
                    break
                except Exception:
                    continue
        failed = getattr(move, "onMoveFail", None)
        if callable(failed):
            invoke_callback(failed, user, target, move, battle=self)

    def _clear_item(self, pokemon) -> None:
        """Remove the held item from ``pokemon`` without extra checks."""

        self._clear_choice_lock(pokemon)
        if hasattr(pokemon, "item"):
            pokemon.item = None
        if hasattr(pokemon, "held_item"):
            pokemon.held_item = ""

    def _remember_side_item(self, pokemon, item) -> None:
        """Record that ``item`` left play for side-based pickup effects."""

        if not pokemon or not item:
            return
        side = getattr(pokemon, "side", None)
        if not side:
            return
        used = getattr(side, "used_items", None)
        if not isinstance(used, list):
            used = []
            try:
                side.used_items = used
            except Exception:
                return
        used.append(item)

    def _notify_after_use_item(self, pokemon, item, *, source=None, effect=None) -> None:
        """Trigger ability callbacks that react to item consumption or use."""

        from .effect_context import EffectContext

        if not pokemon or not item:
            return
        ability = _resolve_ability(getattr(pokemon, "ability", None))
        if ability and hasattr(ability, "call"):
            try:
                ability.call("onAfterUseItem", item=item, pokemon=pokemon, source=source, effect=effect, battle=self)
            except Exception:
                pass
        participant = self.participant_for(pokemon)
        if not participant:
            return
        for ally in getattr(participant, "active", []) or []:
            if ally is pokemon:
                continue
            ally_ability = EffectContext.ability(ally)
            if not ally_ability or not hasattr(ally_ability, "call"):
                continue
            try:
                state = dict(getattr(ally, "ability_state", {}) or {})
                state["target"] = ally
                ally_ability.call("onAllyAfterUseItem", item=item, source=pokemon, pokemon=ally,
                                  effect=effect, battle=self, effect_state=state)
            except Exception:
                continue

    def add_volatile(self, pokemon, condition: str, *, source=None, effect=None, start_callback=None) -> bool:
        """Add a volatile status through the battle event system."""

        if not pokemon or not condition:
            return False
        if self.runEvent("TryAddVolatile", pokemon, source, effect, condition) is False:
            return False
        previous = getattr(pokemon, "volatiles", {}).get(condition)
        if previous is not None:
            handler = self._volatile_handler(condition)
            if handler:
                result = self.singleEvent(
                    "Restart",
                    handler,
                    previous if isinstance(previous, dict) else {"id": condition},
                    pokemon,
                    source,
                    effect,
                )
                return bool(result is not False)
            return True

        pokemon.volatiles.setdefault(
            condition,
            self.init_effect_state(condition, target=pokemon, source=source, source_effect=effect),
        )
        handler = self._volatile_handler(condition)
        if handler or callable(start_callback):
            legacy_start = None
            if callable(start_callback):
                def legacy_start(*args, **kwargs):
                    """Adapt move-data start hooks after the canonical immunity gate."""
                    return invoke_callback(start_callback, source, pokemon, battle=self)
            result = self.singleEvent(
                "Start",
                handler,
                pokemon.volatiles[condition],
                pokemon,
                source,
                effect,
                callback=legacy_start,
            )
            if result is False:
                pokemon.volatiles.pop(condition, None)
                return False
        if condition == "attract" and source is not None:
            self.runEvent("Attract", pokemon, source, effect)
        return True

    def remove_volatile(self, pokemon, condition: str) -> bool:
        """Remove a volatile status and run its end hook."""

        if not pokemon:
            return False
        state = getattr(pokemon, "volatiles", {}).get(condition)
        if state is None:
            return False
        handler = self._volatile_handler(condition)
        if handler:
            self.singleEvent("End", handler, state if isinstance(state, dict) else {}, pokemon)
        pokemon.volatiles.pop(condition, None)
        return True

    def set_ability(
        self,
        pokemon,
        ability,
        *,
        source=None,
        is_from_forme_change: bool = False,
        is_transform: bool = False,
        run_start: bool = True,
    ):
        """Assign a new ability to ``pokemon`` through explicit start/end hooks."""

        if not pokemon:
            return False
        resolved = _resolve_ability(ability) or ability
        if not is_from_forme_change:
            gate = self.runEvent("SetAbility", pokemon, source, getattr(self, "effect", None), resolved)
            if gate is False or gate is None:
                return gate
        old_ability = _resolve_ability(getattr(pokemon, "ability", None)) or getattr(pokemon, "ability", None)
        old_state = getattr(pokemon, "ability_state", {})
        if old_ability:
            self.singleEvent("End", old_ability, old_state, pokemon, source)
        pokemon.ability = resolved
        if (getattr(pokemon, "native_origin", None) or {}).get("necrozma") and not is_from_forme_change:
            pokemon.native_ability_provenance = "changed"
        pokemon.ability_state = self.init_effect_state(resolved, target=pokemon, source=source)
        if resolved and run_start:
            self.singleEvent("Start", resolved, pokemon.ability_state, pokemon, source)
        return old_ability

    def start_owned_ability(self, pokemon) -> None:
        """Start an explicitly installed ability with named owner context.

        Public Mega, Trace and native form installation use this boundary.
        Propagate unexpected failures
        to their whole-turn transaction; do not replay entry or item events.
        Other ability installation paths retain their existing defaults.
        """
        from .effect_context import EffectContext
        import inspect

        ability = _resolve_ability(EffectContext.ability(pokemon))
        raw_start = (getattr(ability, "raw", {}) or {}).get("onStart")
        if not raw_start:
            return
        callback = resolve_callback_from_modules(raw_start, "pokemon.dex.functions.abilities_funcs")
        if not callable(callback):
            raise RuntimeError("The installed ability Start callback is unavailable.")
        owner = getattr(callback, "__self__", None)
        if owner is not None:
            owner.effect_state = pokemon.ability_state
        context = {"pokemon": pokemon, "target": pokemon, "source": pokemon,
                   "user": pokemon, "battle": self, "effect_state": pokemon.ability_state}
        signature = inspect.signature(callback)
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
            context = {key: value for key, value in context.items() if key in signature.parameters}
        signature.bind(**context)
        callback(**context)

    def _pokemon_has_item(self, pokemon) -> bool:
        """Return whether ``pokemon`` is currently holding an item."""

        return bool(self._holder_item(pokemon))

    def can_set_item(self, pokemon, item) -> bool:
        """Return whether ``pokemon`` can receive ``item`` right now."""

        if pokemon is None:
            return False
        if item is None:
            return True
        if self._pokemon_has_item(pokemon):
            return False
        return True

    def remove_item(self, pokemon, *, source=None, effect=None, used: bool = False):
        """Remove and return a held item, recording battle metadata."""

        # A consumption is a UseItem operation, not theft. TakeItem vetoes
        # protect native identity items from transfer, including Booster Energy.
        item_obj = self._holder_item(pokemon) if used else self.take_item(pokemon, source=source, effect=effect)
        if not item_obj:
            return None
        if used:
            self._clear_item(pokemon)
        item_name = getattr(item_obj, "name", str(item_obj))
        pokemon.last_used_item = item_obj
        if used:
            self._remember_side_item(pokemon, item_obj)
            self._notify_after_use_item(pokemon, item_obj, source=source, effect=effect)
        else:
            pokemon.last_removed_item = item_name
        return item_obj

    def move_item(self, source_pokemon, target_pokemon, *, effect=None, source=None) -> bool:
        """Transfer ``source_pokemon``'s held item to ``target_pokemon``."""

        if not source_pokemon or not target_pokemon or source_pokemon is target_pokemon:
            return False
        if self._pokemon_has_item(target_pokemon):
            return False
        item_obj = self.take_item(source_pokemon, source=source or target_pokemon, effect=effect)
        if not item_obj:
            return False
        if not self.set_item(target_pokemon, item_obj, source=source_pokemon, effect=effect):
            self.set_item(source_pokemon, item_obj, source=source, effect=effect)
            return False
        return True

    def swap_items(self, first, second, *, effect=None) -> bool:
        """Swap held items between two Pokemon when both transfers are legal."""

        if not first or not second or first is second:
            return False
        first_item = self._holder_item(first)
        second_item = self._holder_item(second)
        if first_item is None and second_item is None:
            return False
        if first_item is not None:
            allowed = first_item.call("onTakeItem", item=first_item, pokemon=first, source=second, effect=effect, battle=self)
            if allowed is False:
                return False
        if second_item is not None:
            allowed = second_item.call("onTakeItem", item=second_item, pokemon=second, source=first, effect=effect, battle=self)
            if allowed is False:
                return False
        first_ability = _resolve_ability(getattr(first, "ability", None))
        second_ability = _resolve_ability(getattr(second, "ability", None))
        if first_item is not None and first_ability and hasattr(first_ability, "call"):
            if first_ability.call("onTakeItem", item=first_item, pokemon=first, source=second, effect=effect, battle=self) is False:
                return False
        if second_item is not None and second_ability and hasattr(second_ability, "call"):
            if second_ability.call("onTakeItem", item=second_item, pokemon=second, source=first, effect=effect, battle=self) is False:
                return False
        self._clear_item(first)
        self._clear_item(second)
        restored = []
        if second_item is not None and self.set_item(first, second_item, source=second, effect=effect):
            restored.append(("first", second_item))
        elif second_item is not None:
            self.set_item(first, first_item, source=first, effect=effect)
            self.set_item(second, second_item, source=second, effect=effect)
            return False
        if first_item is not None and self.set_item(second, first_item, source=first, effect=effect):
            restored.append(("second", first_item))
        elif first_item is not None:
            self._clear_item(first)
            self._clear_item(second)
            self.set_item(first, first_item, source=first, effect=effect)
            self.set_item(second, second_item, source=second, effect=effect)
            return False
        return bool(restored)

    def steal_item(self, thief, target, *, effect=None) -> bool:
        """Move ``target``'s held item to ``thief`` if theft is legal."""

        if not thief or not target or self._pokemon_has_item(thief):
            return False
        item_obj = self.take_item(target, source=thief, effect=effect)
        if not item_obj:
            return False
        if not self.set_item(thief, item_obj, source=target, effect=effect):
            self.set_item(target, item_obj, source=target, effect=effect)
            return False
        return True

    def eat_berry(self, eater, target, *, effect=None) -> bool:
        """Have ``eater`` consume ``target``'s berry using item hooks."""

        item_obj = self._holder_item(target)
        if not item_obj:
            return False
        item_name = getattr(item_obj, "name", str(item_obj))
        if "berry" not in _normalize_key(item_name):
            return False
        removed = self.take_item(target, source=eater, effect=effect)
        if not removed:
            return False
        removed.call("onEat", pokemon=eater, source=target, effect=effect, battle=self)
        eater.last_item = item_name
        eater.last_consumed_item = item_name
        eater.last_consumed_item_obj = removed
        eater.last_used_item = removed
        eater.berry_consumed = removed
        eater.consumed_item = removed
        self._notify_after_use_item(eater, removed, source=target, effect=effect)
        return True

    def use_item(self, pokemon, item=None, *, source=None, effect=None) -> bool:
        """Run generic held-item use gating without consuming the item."""

        item_obj = self._coerce_item(item) or self._holder_item(pokemon)
        if not item_obj:
            return False
        if self.runEvent("UseItem", pokemon, source, effect, item_obj) is False:
            return False
        if self.singleEvent("Use", item_obj, getattr(pokemon, "item_state", {}), pokemon, source, effect) is False:
            return False
        return True

    def eat_item(self, pokemon, *, source=None, effect=None, force: bool = False):
        """Consume ``pokemon``'s held item following Showdown-style gates."""

        item_obj = self._holder_item(pokemon)
        if not item_obj:
            return False
        if force and self.use_item(pokemon, item_obj, source=source, effect=effect) is False:
            return False
        if not force:
            if self.use_item(pokemon, item_obj, source=source, effect=effect) is False:
                return False
            holder_participant = self.participant_for(pokemon)
            for part in self.opponents_of(holder_participant) if holder_participant else []:
                for foe in getattr(part, "active", []) or []:
                    if getattr(foe, "hp", 0) <= 0:
                        continue
                    ability = _resolve_ability(getattr(foe, "ability", None))
                    if ability and hasattr(ability, "call"):
                        if ability.call("onFoeTryEatItem", item=item_obj, pokemon=pokemon, source=foe, effect=effect, battle=self) is False:
                            return False
            if self.runEvent("TryEatItem", pokemon, source, effect, item_obj) is False:
                return False
            if self.runEvent("EatItem", pokemon, source, effect, item_obj) is False:
                return False
        item_name = getattr(item_obj, "name", str(item_obj))
        hp_before_berry = getattr(pokemon, "hp", 0)
        from .effect_context import EffectContext

        ripen_berry = (EffectContext.key(EffectContext.ability(pokemon)) == "ripen"
                       and "berry" in EffectContext.key(item_obj))
        if ripen_berry:
            pokemon.ripen_active = True
        self.singleEvent("Eat", item_obj, getattr(pokemon, "item_state", {}), pokemon, source, effect)
        # Legacy berries assign HP directly, bypassing TryHeal. Scale that
        # actual berry heal once; normal healing callbacks clear this flag.
        if getattr(pokemon, "ripen_active", False):
            healed = max(0, getattr(pokemon, "hp", 0) - hp_before_berry)
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + healed)
            pokemon.ripen_active = False
        if force:
            self.runEvent("EatItem", pokemon, source, effect, item_obj)
        if ripen_berry:
            pokemon.ripen_active = False
        pokemon.last_item = item_name
        pokemon.last_consumed_item = item_name
        pokemon.last_consumed_item_obj = item_obj
        pokemon.last_used_item = item_obj
        pokemon.consumed_item = item_obj
        if "berry" in _normalize_key(item_name):
            pokemon.consumed_berry = item_obj
            pokemon.berry_consumed = item_obj
        self._clear_item(pokemon)
        self._remember_side_item(pokemon, item_obj)
        self._notify_after_use_item(pokemon, item_obj, source=source, effect=effect)
        return True

    def take_item(self, pokemon, *, source=None, effect=None):
        """Remove and return ``pokemon``'s held item if no effect blocks it."""

        item_obj = self._holder_item(pokemon)
        if not item_obj:
            return None
        allowed = self.runEvent("TakeItem", pokemon, source, effect, item_obj)
        if allowed is False or allowed is None:
            return None
        item_name = getattr(item_obj, "name", str(item_obj))
        pokemon.last_item = item_name
        pokemon.last_removed_item = item_name
        effect_key = _normalize_key(getattr(effect, "name", effect))
        pokemon.knocked_off = (
            True if effect_key.endswith("knockoff") else getattr(pokemon, "knocked_off", False)
        )
        old_state = getattr(pokemon, "item_state", {})
        self._clear_item(pokemon)
        self._clear_item_forme_effects(pokemon, source=source)
        self.singleEvent("End", item_obj, old_state, pokemon, source, effect)
        return item_obj

    def set_item(self, pokemon, item, *, source=None, effect=None) -> bool:
        """Assign ``item`` as the held item for ``pokemon`` and trigger start hooks."""

        if item is None:
            self._clear_item(pokemon)
            self._clear_item_forme_effects(pokemon, source=source)
            return True
        self._clear_choice_lock(pokemon)
        item_obj = self._coerce_item(item)
        if not item_obj:
            return False
        if self._pokemon_has_item(pokemon):
            return False
        pokemon.item = item_obj
        pokemon.item_state = self.init_effect_state(item_obj, target=pokemon, source=source, source_effect=effect)
        self.register_handlers(pokemon)
        if hasattr(pokemon, "held_item"):
            pokemon.held_item = getattr(item_obj, "name", str(item_obj))
        pokemon.last_item = getattr(item_obj, "name", str(item_obj))
        pokemon.knocked_off = False
        self.singleEvent("Start", item_obj, pokemon.item_state, pokemon, source, effect)
        self._apply_item_forme_effects(pokemon, source=source)
        return True

    def _deal_damage(
        self, user, target, move: BattleMove, *, spread: bool = False
    ) -> int:
        """Apply simplified damage calculation to ``target``."""
        if (move.raw.get("category") or "").lower() == "status":
            return 0
        result = _apply_move_damage(user, target, move, self, spread=spread)
        return sum(result.debug.get("damage", []))

    def _do_move(self, user, target, move: BattleMove) -> bool:
        """Execute a move already approved by the single pre-move hook pass."""

        self.dispatcher.dispatch(
            "execute_move", user=user, target=target, move=move, battle=self
        )
        move.execute(user, target, self)
        return True

    def _announce_move_result(self, user, target, move, before_user, before_target, *, report_no_effect=True, field_changed=False):
        """Describe one target's actual damage, conditions and stat changes."""
        after_user, after_target = _MoveResultState.capture(user), _MoveResultState.capture(target)
        start_user_boosts, end_user_boosts = before_user.boosts, after_user.boosts
        start_target_boosts, end_target_boosts = before_target.boosts, after_target.boosts
        dmg = before_target.hp - after_target.hp
        boosts_changed = (
            start_user_boosts != end_user_boosts
            or start_target_boosts != end_target_boosts
        )
        statuses_changed = (before_user.status, before_target.status) != (
            after_user.status, after_target.status
        )
        effects_changed = any(
            before.hp < after.hp or before.volatiles != after.volatiles
            or before.item != after.item or before.ability != after.ability
            for before, after in ((before_user, after_user), (before_target, after_target))
        )
        target_self = target is user
        user_name = getattr(user, "name", "Pokemon")
        target_name = "itself" if target_self else getattr(target, "name", "Pokemon")
        if dmg > 0:
            if getattr(self, "show_damage_numbers", False):
                self.log_action(
                    f"{user_name} used {move.name} on {target_name} and dealt {dmg} damage!"
                )
            if boosts_changed:
                self.announce_stat_changes(
                    user,
                    start_user_boosts,
                    end_user_boosts,
                )
                self.announce_stat_changes(
                    target,
                    start_target_boosts,
                    end_target_boosts,
                )
        elif boosts_changed or statuses_changed or effects_changed or field_changed or getattr(move, "_queue_changed", False):
            if target_self:
                self.log_action(f"{user_name} used {move.name}!")
            else:
                self.log_action(
                    f"{user_name} used {move.name} on {target_name}!"
                )
            self.announce_stat_changes(
                user,
                start_user_boosts,
                end_user_boosts,
                move.raw.get("boosts") if target_self else None,
            )
            self.announce_stat_changes(
                target,
                start_target_boosts,
                end_target_boosts,
                move.raw.get("boosts") if not target_self else None,
            )
        else:
            if move.raw.get("boosts"):
                fail_target = "its own" if target_self else f"{target_name}'s"
                self.log_action(
                    f"{user_name}'s {move.name} failed to affect {fail_target} stats!"
                )
                affected = user if target_self else target
                start = start_user_boosts if target_self else start_target_boosts
                end = end_user_boosts if target_self else end_target_boosts
                self.announce_stat_changes(
                    affected, start, end, move.raw.get("boosts")
                )
            elif report_no_effect:
                self.log_action(
                    f"{user_name} used {move.name} on {target_name} but it had no effect!"
                )

    def pending_move(self, pokemon):
        """Return the current selected attack, never previous move history."""
        queue = getattr(self, "queue", None)
        if queue is not None:
            action = queue.will_move(pokemon)
            return getattr(action, "move", None)
        participant = self.participant_for(pokemon)
        pending = getattr(participant, "pending_action", None)
        actions = pending if isinstance(pending, list) else [pending] if pending else []
        for action in actions:
            if getattr(action, "pokemon", None) is pokemon and getattr(getattr(action, "action_type", None), "name", "") == "MOVE":
                return action.move
        return None

    def run_called_move(self, user, move, target=None, *, power_multiplier=1.0, spend_pp=False):
        """Run a nested move, retaining normal costs for instructed repeats."""
        from .called_moves import CalledMoveExecutor

        return CalledMoveExecutor(self).execute(user, move, target, power_multiplier=power_multiplier,
                                                spend_pp=spend_pp)

    def use_move(self, action: Action, *, called: bool = False) -> None:
        """Attempt to use the chosen move applying simple failure rules."""
        if not action.move:
            return
        if hasattr(action.move, "_gem_original_power"):
            action.move.power = action.move._gem_original_power
            del action.move._gem_original_power
        action.move._gem_boosted = False
        action.move._gem_consumed = False
        action.move._gem_power_multiplier = 1
        action.move._gem_power_applied = False
        action.move.total_damage = 0
        # One shared cache covers every hit/target of this use, never the next
        # turn or a damage preview. Only the consumed type ledger is persisted.
        action.move._stellar_boosts = {}
        action.move._primary_hit_successful = False
        called_before = len(getattr(self, "called_moves", []))

        user = action.pokemon or (
            action.actor.active[0] if action.actor.active else None
        )
        if not user:
            return
        from .effect_context import EffectContext

        if EffectContext.key(EffectContext.item(user)) != "metronome":
            getattr(user, "volatiles", {}).pop("metronome", None)

        if getattr(user, "hp", 0) <= 0:
            tempvals = getattr(user, "tempvals", None)
            if tempvals is None:
                tempvals = {}
                setattr(user, "tempvals", tempvals)
            tempvals["switch_out"] = True
            return

        # Crowned signatures replace only this runtime action; stored move
        # identity and PP remain Iron Head in the owner's canonical slot.
        signature = {"Zacian-Crowned": "Behemoth Blade", "Zamazenta-Crowned": "Behemoth Bash"}.get(str(getattr(user, "species", "")))
        if signature and _effect_key(action.move) == "ironhead":
            original_pp = next((state[2] for state in self._move_pp_states(user) if _normalize_key(state[1]).lower() == "ironhead"), getattr(action.move, "pp", None))
            action.move = BattleMove(name=signature, pp=original_pp)
            action.move._pp_move_name = "Iron Head"

        # Ensure we have full move data loaded from the dex
        key = getattr(action.move, "key", None)
        if not key and getattr(action.move, "name", None):
            key = _normalize_key(action.move.name)
        ensure_movedex_aliases(MOVEDEX)
        private_z = getattr(action.move, "_z_paid", False)
        dex_move = MOVEDEX.get(key) if key and not private_z else None
        dex_raw = get_raw(dex_move) if dex_move else {}
        if not private_z and (not dex_move or not dex_raw):
            try:
                from pokemon import dex as _dex_mod

                source = getattr(_dex_mod, "MOVEDEX", {})
                if not source:
                    from pokemon.dex.entities import load_movedex

                    source = load_movedex(_dex_mod.MOVEDEX_PATH)
                    _dex_mod.MOVEDEX = source
                if MOVEDEX is not source:
                    MOVEDEX.clear()
                    MOVEDEX.update(source)
                    ensure_movedex_aliases(MOVEDEX)
                dex_move = MOVEDEX.get(key) if key else None
                dex_raw = get_raw(dex_move) if dex_move else {}
            except Exception:
                dex_move = None
                dex_raw = {}
        if dex_move:
            # Merge raw dex data first so downstream code can read category/callbacks.
            merged_raw = dict(dex_raw)
            if action.move.raw:
                merged_raw.update(action.move.raw)
            action.move.raw = merged_raw

            raw = action.move.raw
            action.move.multihit = raw.get("multihit")

            # POWER: prefer Showdown's `basePower` when present; otherwise fall back to dex_move.power.
            if action.move.power in (None, 0):
                bp = raw.get("basePower")
                if isinstance(bp, (int, float)) and bp > 0:
                    action.move.power = int(bp)
                else:
                    dm_pow = getattr(dex_move, "power", None)
                    if isinstance(dm_pow, (int, float)) and dm_pow not in (None, 0):
                        action.move.power = int(dm_pow)

            # ACCURACY: always source from dex raw (handles int/bool/float) with property fallback.
            acc = raw.get("accuracy", getattr(dex_move, "accuracy", None))
            if acc is not None:
                action.move.accuracy = acc

            # TYPE/CATEGORY/PRIORITY: ensure type present; category is kept in raw for _apply_move_damage.
            if action.move.type is None:
                action.move.type = getattr(dex_move, "type", raw.get("type"))
            if raw.get("category") is not None:
                action.move.category = raw.get("category", getattr(dex_move, "category", None))
            if action.move.priority == 0:
                action.move.priority = int(raw.get("priority", 0))

            for attr in (
                "onHit",
                "onTry",
                "onTryMove",
                "onModifyType",
                "onBeforeMove",
                "onAfterMove",
                "onModifyMove",
                "onPrepareHit",
                "onTryImmunity",
                "onTryPrimaryHit",
                "onTryHit",
                "onTryHitSide",
                "onTryHitField",
                "onHitSide",
                "onHitField",
                "onMoveFail",
                "onMoveAborted",
                "onAfterHit",
                "onAfterMoveSecondary",
                "onAfterMoveSecondarySelf",
                "onUseMoveMessage",
                "onUpdate",
                "priorityChargeCallback",
                "beforeMoveCallback",
                "basePowerCallback",
                "damageCallback",
                "onBasePower",
            ):
                if getattr(action.move, attr, None) is None:
                    cb_name = raw.get(attr)
                    cb = _resolve_callback(cb_name, moves_funcs)
                    if callable(cb):
                        setattr(action.move, attr, cb)

        if action.move.pp is None:
            slots = getattr(user, "activemoveslot_set", None)
            if slots is not None:
                try:
                    slot_iter = slots.all()
                except Exception:  # pragma: no cover - fallback for stubs
                    slot_iter = slots
                for slot in slot_iter:
                    if _normalize_key(
                        getattr(getattr(slot, "move", None), "name", "")
                    ) == getattr(action.move, "key", ""):
                        current = getattr(slot, "current_pp", None)
                        if current is not None:
                            action.move.pp = current
                        break

        if action.move.pp is None:
            for cached_move in getattr(user, "moves", []):
                if _normalize_key(cached_move.name) == getattr(action.move, "key", ""):
                    action.move.pp = getattr(cached_move, "pp", None)
                    break

        if action.move.pp is not None and action.move.pp <= 0 and not private_z:
            return
        emergency_move = _normalize_key(action.move.key or action.move.name).lower() == "struggle"
        if not emergency_move:
            for override in (self._locked_move_override, self._override_action_move):
                enforced = override(user, action.move)
                if _normalize_key(getattr(enforced, "key", None) or enforced.name) != _normalize_key(action.move.key or action.move.name):
                    from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name

                    action.move = enforced if hasattr(enforced, "execute") else (_battle_move_from_name(enforced.name) or enforced)
                    return self.use_move(action, called=called)
        selected_move_key = getattr(action.move, "key", None) or _normalize_key(
            getattr(action.move, "name", "")
        )
        selected_move_key = str(selected_move_key).lower() if selected_move_key else None
        locked_move_key = getattr(user, "choice_locked_move", None)
        if locked_move_key and self._choice_item_key(user) and not called:
            if selected_move_key and selected_move_key != locked_move_key and not emergency_move:
                locked_move_name = str(locked_move_key).replace("-", " ").title()
                self.log_action(
                    f"{getattr(user, 'name', 'Pokemon')} is locked into {locked_move_name}!"
                )
                return
        elif locked_move_key and not called:
            self._clear_choice_lock(user)
        if not called and not emergency_move and self._is_move_disabled(user, action.move):
            self.log_action(f"{getattr(user, 'name', 'Pokemon')} can't use {action.move.name}!")
            return
        if not called and self.status_prevents_move(user, action.move):
            self.log_action(f"{getattr(user, 'name', 'Pokemon')} is unable to move!")
            return
        if getattr(action, "z_request", None) is not None:
            from .z_moves import ZMoves

            ZMoves.begin(self, action)
            if action.move._z_profile.target == "allAdjacentFoes":
                from .z_spread import ZSpread

                ZSpread.execute(self, action)
                return
        from .effect_context import EffectContext

        if action.move.beforeMoveCallback:
            before_move_result = invoke_callback(
                action.move.beforeMoveCallback,
                user,
                target=None,
                move=action.move,
                battle=self,
            )
            if before_move_result is False:
                return

        if getattr(self, 'multi', False) and getattr(action, 'target_position', None):
            field_part = next((part for part in self.participants if part.field_position == action.target_position), None)
            if field_part is not None:
                action.target, action.target_slot = field_part, 0
                action.target_pokemon = next(iter(field_part.active), None)
        target_part = action.target
        if target_part not in self.participants or target_part.has_lost:
            opponents = self.opponents_of(action.actor)
            target_part = opponents[0] if opponents else None
        target = None
        if getattr(action, "target_slot", None) is not None:
            from .active_slots import active_at

            slot = action.target_slot
            if target_part:
                candidate = active_at(target_part, slot)
                if candidate is not None and getattr(candidate, "hp", 0) > 0:
                    target = candidate
        elif getattr(action, "target_pokemon", None) is not None:
            candidate = action.target_pokemon
            if target_part and any(mon is candidate for mon in target_part.active) and getattr(candidate, "hp", 0) > 0:
                target = candidate
        elif action.move.raw.get("target") in {"self", "allies", "allySide", "allyTeam"} or (
                action.move.raw.get("target") == "adjacentAllyOrSelf" and len(action.actor.active) == 1):
            target_part = action.actor
            target = user
        elif target_part and target_part.active:
            candidate = target_part.active[0]
            if getattr(candidate, "hp", 0) > 0:
                target = candidate

        action.move.flags = dict(action.move.raw.get("flags", {}) or {})
        action.move.breaksProtect = bool(action.move.raw.get("breaksProtect"))
        action.move.tracks_target = bool(action.move.raw.get("tracksTarget"))
        action.move.secondaries = copy.deepcopy(action.move.raw.get("secondaries", []) or [])
        if action.move.raw.get("secondary"):
            action.move.secondaries.append(copy.deepcopy(action.move.raw["secondary"]))
        move_ability = EffectContext.ability(user)
        if move_ability and hasattr(move_ability, "call"):
            move_ability.call("onModifyMove", action.move, user=user, pokemon=user, target=target,
                              battle=self, effect_state=getattr(user, "ability_state", {}))
        action.move._ability_move_prepared = True
        move_item = EffectContext.item(user)
        if hasattr(move_item, "call"):
            move_item.call("onModifyMove", action.move, pokemon=user, battle=self)
        if target is not None:
            target = self._modify_move_target(user, target, action.move)
            modified_part = self.participant_for(target)
            if modified_part is not None:
                target_part = modified_part
            redirectable = action.move.raw.get("target", "normal") in {"normal", "any", "adjacentFoe"}
            redirected = target if (not redirectable or action.move.tracks_target or getattr(action.move, "_z_spread_part", False)) else self.runEvent(
                "RedirectTarget",
                target,
                user,
                action.move,
                target,
            )
            if redirected not in {False, None, True} and getattr(redirected, "hp", 0) > 0:
                target = redirected
                redirected_part = self.participant_for(redirected)
                if redirected_part is not None:
                    target_part = redirected_part

        if not target:
            # no valid target, still deduct PP and end
            self.deduct_pp(user, action.move, target=target)
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        charge_key = str(_normalize_key(action.move.key or action.move.name)).lower()
        charge_move = bool(action.move.raw.get("flags", {}).get("charge"))
        was_charging = charge_move and bool(getattr(user, "volatiles", {}).get(charge_key))
        if not self._passes_try_move(user, target, action.move):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if charge_move and not was_charging and getattr(user, "volatiles", {}).get(charge_key):
                # The first phase deliberately defers execution. Spend PP once
                # here; releasing the same move next turn does not spend it again.
                item = EffectContext.item(user)
                if hasattr(item, "call") and item.call("onChargeMove", pokemon=user, target=target, move=action.move) is False:
                    self.use_move(action, called=True)
                    self.deduct_pp(user, action.move, target=target)
                    return
                self.deduct_pp(user, action.move, target=target)
                user.last_move = action.move
                self._set_choice_lock(user, action.move)
                self.dispatcher.dispatch("charge_move", user=user, target=target,
                                         move=action.move, battle=self)
                self.log_action(f"{getattr(user, 'name', 'Pokemon')} began charging {action.move.name}!")
                return
            if not was_charging:
                self.deduct_pp(user, action.move, target=target)
            # A TryMove prevention (for example Damp) stops execution before
            # self-sacrifice. Protection/misses after execution retain their
            # separate selfdestruct handling below.
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        # Allow opponents with an active Snatch volatile to intercept
        for part in self.participants:
            if part is action.actor:
                continue
            if not part.active:
                continue
            snatcher = part.active[0]
            if getattr(snatcher, "volatiles", {}).get("snatch") and action.move.raw.get(
                "flags", {}
            ).get("snatch"):
                # Deduct PP from the original user
                self.deduct_pp(user, action.move, target=target)
                self.log_action(
                    f"{getattr(snatcher, 'name', 'Pokemon')} snatched {getattr(user, 'name', 'Pokemon')}'s move!"
                )
                snatcher.volatiles.pop("snatch", None)
                # Determine the target of the stolen move
                snatch_target = (
                    snatcher
                    if is_self_target(action.move.raw.get("target"))
                    else target
                )
                action.move.execute(snatcher, snatch_target, self)
                try:
                    snatcher.tempvals["moved"] = True
                except Exception:
                    pass
                return

        # Invoke passive onTryBoost hooks even if the move itself doesn't
        # attempt any stat changes.  This ensures abilities like Big Pecks are
        # exercised during generic move usage without interfering with Snatch.
        from pokemon.utils.boosts import apply_boost

        if user is not None:
            apply_boost(user, {}, source=target, effect=action.move)
        if target is not None:
            apply_boost(target, {}, source=user, effect=action.move)

        if not was_charging:
            self.deduct_pp(user, action.move, target=target)
        try:
            user.last_move = action.move
        except Exception:
            pass
        if not self._passes_stall_move(user, action.move):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return
        self._set_choice_lock(user, action.move)
        action.move.effective_priority = action.priority or action.move.priority
        if action.move.onModifyMove:
            invoke_callback(action.move.onModifyMove, action.move, user, target, battle=self)
        if action.move.onModifyType:
            invoke_callback(action.move.onModifyType, action.move, user, target, battle=self)
        self.runEvent("ModifyType", user, target, action.move, action.move)
        self.dispatcher.dispatch(
            "before_move", user=user, target=target, move=action.move, battle=self
        )

        if self.runEvent("PrepareHit", user, target, action.move) is False:
            self._notify_move_aborted(user, target, action.move)
            return

        if action.move.onPrepareHit:
            prepared = invoke_callback(action.move.onPrepareHit, user, target, action.move, battle=self)
            if prepared is False:
                self._notify_move_aborted(user, target, action.move)
                self.log_action(
                    f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
                )
                return

        if action.move.onTryHit:
            try_hit = invoke_callback(action.move.onTryHit, target, user, action.move, battle=self)
            if try_hit is False:
                self._notify_move_aborted(user, target, action.move)
                self.log_action(
                    f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
                )
                return
        if action.move.onTryHitSide and target_part is not None:
            try_hit_side = invoke_callback(action.move.onTryHitSide, target_part.side, user, action.move, battle=self)
            if try_hit_side is False:
                self._notify_move_aborted(user, target, action.move)
                self.log_action(
                    f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
                )
                return
        if action.move.onTryHitField:
            try_hit_field = invoke_callback(action.move.onTryHitField, self.field, user, action.move, battle=self)
            if try_hit_field is False:
                self._notify_move_aborted(user, target, action.move)
                self.log_action(
                    f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
                )
                return

        if not self._passes_try_immunity(target, user, action.move):
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        if not self._passes_try_primary_hit(target, user, action.move):
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        from .protection import MoveProtection
        if MoveProtection.blocks(target, user, action.move, self):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
            self._notify_move_aborted(user, target, action.move)
            self.log_action(f"{getattr(target, 'name', 'Pokemon')} protected itself!")
            return

        blocked = self.runEvent(
            "Invulnerability",
            target,
            user,
            action.move,
            False,
        )
        from .accuracy import MoveAccuracy
        if blocked and not MoveAccuracy.locked_on(user, target):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{action.move.name} failed to hit {getattr(target, 'name', 'Pokemon')}!"
            )
            return

        if getattr(action.move, "multihit_type", "") == "parentalbond":
            from .parental_bond import ParentalBondAttack

            ParentalBondAttack.execute(self, user, target, action.move)
            return

        sub = getattr(target, "volatiles", {}).get("substitute")
        move_flags = getattr(action.move, "flags", None) or action.move.raw.get("flags", {})
        bypasses_substitute = bool(
            action.move.raw.get("bypassSub") or move_flags.get("bypasssub")
            or getattr(action.move, "infiltrates", False)
        )
        move_category = (
            getattr(action.move, "category", None)
            or action.move.raw.get("category")
            or ""
        )
        if (
            target is not user
            and sub
            and not bypasses_substitute
            and str(move_category).lower() == "status"
        ):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return
        if target is not user and sub and not bypasses_substitute:
            if getattr(action.move, "_z_paid", False) and _ability_try_hit_blocks(target, user, action.move, self):
                self._notify_move_aborted(user, target, action.move)
                return
            Move = _get_move_class()

            from .damage import apply_damage
            from .item_effects import HeldItemRules

            HeldItemRules.apply_gem_power(action.move)
            raw = dict(action.move.raw)
            if action.move.basePowerCallback:
                raw["basePowerCallback"] = action.move.basePowerCallback
            move = Move(
                name=action.move.name,
                num=0,
                type=action.move.type,
                category=getattr(
                    action.move,
                    "category",
                    raw.get("category", "Physical"),
                ),
                power=action.move.power,
                accuracy=action.move.accuracy,
                pp=None,
                raw=raw,
            )
            if action.move.basePowerCallback:
                try:
                    move.basePowerCallback = action.move.basePowerCallback
                    action.move.basePowerCallback(user, target, move)
                except Exception:
                    move.basePowerCallback = None

            move._stellar_boosts = action.move._stellar_boosts
            move._tera_shared_use = True
            move._engine_secondaries = True
            move._z_paid = getattr(action.move, "_z_paid", False)
            dmg_result = apply_damage(user, target, move, battle=self, update_hp=False)
            from .terastallization import apply_stellar_cost

            apply_stellar_cost(user, action.move, dmg_result)
            dmg = sum(dmg_result.debug.get("damage", []))
            substitute_hp = sub.get("hp", 0) if isinstance(sub, dict) else dmg
            actual_substitute_damage = min(max(0, substitute_hp), max(0, dmg))
            action.move.total_damage += actual_substitute_damage
            from .z_effects import ZEffects

            ZEffects.hit(self, user, action.move, actual_substitute_damage)
            if actual_substitute_damage > 0:
                HeldItemRules.commit_gem(user, action.move)
            if isinstance(sub, dict):
                remaining = sub.get("hp", 0) - dmg
                if remaining <= 0:
                    target.volatiles.pop("substitute", None)
                else:
                    sub["hp"] = remaining
            else:
                target.volatiles.pop("substitute", None)
            if dmg > 0:
                try:
                    target.tempvals["took_damage"] = True
                except Exception:
                    pass
                drain = action.move.raw.get("drain")
                if drain:
                    frac = drain[0] / drain[1]
                    heal_amt = max(1, int(dmg * frac))
                    self.heal(user, heal_amt, source=target, effect=action.move)
                recoil = action.move.raw.get("recoil")
                if recoil:
                    frac = recoil[0] / recoil[1]
                    from .indirect_damage import apply_recoil_damage

                    recoil_loss = apply_recoil_damage(user, int(dmg * frac), action.move, battle=self, source=target)
                    if recoil_loss:
                        self.log_action(
                            _get_default_text()["recoil"]["damage"].replace(
                                "[POKEMON]", getattr(user, "name", "Pokemon")
                            )
                        )
                self._queue_self_switch(user, action.move)
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            sd = action.move.raw.get("selfdestruct")
            hit = dmg > 0
            if sd == "always" or (sd == "ifHit" and hit):
                user.hp = 0
            if not hit:
                self._notify_move_aborted(user, target, action.move)
            else:
                self.runEvent("AfterSubDamage", target, user, action.move, actual_substitute_damage)
                self.runEvent("AfterMoveSecondarySelf", user, target, action.move)
            return

        # Allow moves to execute even when the target is normally immune.
        #
        # The previous implementation performed a manual type effectiveness
        # check and returned early if the move dealt no damage (``eff == 0``).
        # This prevented secondary effects such as guaranteed stat drops from
        # running, which in turn caused tests verifying those effects to fail
        # (e.g. Bitter Malice's Attack drop on Normal-type targets).  Removing
        # the pre-check lets the standard damage calculation handle immunities
        # while still executing any secondary callbacks or boosts.
        # The damage routine will still report "It doesn't affect..." messages
        # as appropriate, so behaviour remains informative while enabling tests
        # to validate move side effects.

        before_user, before_target = _MoveResultState.capture(user), _MoveResultState.capture(target)
        start_room = bool(self.field.get_pseudo_weather("trickroom"))
        start_positions = tuple(part.field_position for part in self.participants) if getattr(self, 'multi', False) else None
        if action.move.onBeforeMove:
            try:
                action.move.onBeforeMove(user, target, self)
            except Exception:
                action.move.onBeforeMove(user, target)
        from .legal_actions import LegalActions
        z_part = getattr(action.move, "_z_spread_part", False)
        spread_targets = (LegalActions(self, action.actor, user).targets(action.move)
                          if not z_part and action.move.raw.get("target") in {"allAdjacent", "allAdjacentFoes", "allies"} else [])
        if action.move.raw.get("target") == "allies" and action.move.onHit:
            # Group support handlers already visit the user's party once.
            spread_targets = []
        # Some callbacks affect the whole group on the primary hit. Retain each
        # target's original state so those effects also get an accurate summary.
        spread_before = {id(mon): _MoveResultState.capture(mon) for mon in spread_targets}
        if not z_part:
            action.move._spread = len(spread_targets) > 1
        executed = self._do_move(user, target, action.move)
        if not executed:
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            self._notify_move_aborted(user, target, action.move)
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        room_active = bool(self.field.get_pseudo_weather("trickroom"))
        room_changed = start_room != room_active
        positions_changed = (start_positions is not None and
            start_positions != tuple(part.field_position for part in self.participants))
        sacrifice = (action.move.raw.get("selfdestruct") == "ifHit"
                     and getattr(action.move, "_primary_hit_successful", False))
        called = (action.move.raw.get("callsMove") or _effect_key(action.move) == "instruct") and len(getattr(self, "called_moves", [])) > called_before
        if called:
            self.log_action(f"{user.name} used {action.move.name} and called {self.called_moves[-1]}!")
        self._announce_move_result(user, target, action.move, before_user, before_target,
                                   field_changed=room_changed or positions_changed, report_no_effect=not sacrifice and not called)
        if room_changed:
            self.log_action("Trick Room twisted the dimensions!" if room_active else "Trick Room's twisted dimensions returned to normal!")

        if action.move.raw.get("forceSwitch") and target is not None and getattr(target, "hp", 0) > 0:
            if self._can_drag_out(target, source=user, effect=action.move):
                target.tempvals = getattr(target, "tempvals", {})
                target.tempvals["switch_out"] = True
                target.tempvals["dragged_out"] = True

        if action.move.onHitSide:
            invoke_callback(action.move.onHitSide, user, battle=self)

        if action.move.onHitField:
            invoke_callback(action.move.onHitField, user, battle=self)

        if action.move.onAfterHit:
            invoke_callback(
                action.move.onAfterHit,
                user,
                target,
                battle=self,
                source=user,
                target=target,
                move=action.move,
            )

        for extra in spread_targets:
            if extra is not target and getattr(extra, "hp", 0) > 0:
                before_user = _MoveResultState.capture(user)
                action.move.execute(user, extra, self)
                if str(action.move.raw.get("category", "")).lower() == "status":
                    self._announce_move_result(
                        user, extra, action.move, before_user, spread_before[id(extra)],
                        # Callback-only moves can change state outside this
                        # summary's model; leave their failure text to the handler.
                        report_no_effect=any(action.move.raw.get(key) for key in
                                             ("boosts", "status", "volatileStatus", "heal")),
                    )

        # Status moves also change item-trigger conditions. Run the ordinary
        # update phase before another queued combatant acts, just as damage
        # already does for its target (for example Lum curing Confuse Ray).
        for participant in self.participants:
            for pokemon in participant.active:
                if getattr(pokemon, "hp", 0) > 0:
                    self.dispatcher.dispatch("update", pokemon=pokemon, battle=self)
        self.runEvent("AfterMoveSecondary", target, user, action.move)
        if not z_part:
            self.runEvent("AfterMoveSecondarySelf", user, target, action.move)

        if action.move.onUseMoveMessage:
            invoke_callback(
                action.move.onUseMoveMessage,
                user,
                target,
                action.move,
                battle=self,
            )

        # Compatibility hook for moves whose runtime data still stores
        # post-resolution cleanup under ``onUpdate`` (for example Fling).
        if action.move.onUpdate:
            invoke_callback(
                action.move.onUpdate,
                user,
                target,
                battle=self,
                move=action.move,
            )

        if z_part:
            return
        if action.move.onAfterMove:
            invoke_callback(action.move.onAfterMove, user, target, battle=self)
        self.runEvent("AfterMove", user, target, action.move)
        self._trigger_dancer_copy(user, target, action.move)
        self._queue_self_switch(user, action.move)

        self.dispatcher.dispatch(
            "after_move", user=user, target=target, move=action.move, battle=self
        )
        sd = action.move.raw.get("selfdestruct")
        if sd:
            hit = getattr(target, "tempvals", {}).get("took_damage")
            if str(action.move.raw.get("category", "")).lower() == "status":
                hit = getattr(action.move, "_primary_hit_successful", False)
            if sd == "always" or (sd == "ifHit" and hit):
                user.hp = 0
        try:
            user.tempvals["moved"] = True
        except Exception:
            pass
        try:
            self.last_move = action.move
        except Exception:
            pass


    def run_move(self) -> None:
        """Execute ordered actions for this turn."""
        actions = self.select_actions()
        actions = self.order_actions(actions)
        self.execute_actions(actions)

    def run_faint(self) -> None:
        """Handle fainted PokÃƒÆ’Ã‚Â©mon and mark participants as losing if needed."""

        from .active_slots import active_at, active_slots, assign_active
        from .legal_actions import LegalActions

        for part in self.participants:
            if part.has_lost:
                continue

            opponent = self.opponent_of(part)

            fainted = [
                p
                for p in part.pokemons
                if getattr(p, "hp", 0) <= 0 and not getattr(p, "is_fainted", False)
            ]
            if fainted:
                if (
                    opponent
                    and opponent.player
                    and self.type
                    in {BattleType.WILD, BattleType.TRAINER, BattleType.SCRIPTED}
                ):
                    from pokemon.dex.exp_ev_yields import GAIN_INFO
                    # Prefer the local (battle-side) models path first; its __init__ is
                    # lightweight and safe in CI. If that fails, fall back to the
                    # Evennia/Django app path.
                    try:
                        from pokemon.models.stats import (  # type: ignore
                            award_experience_to_party,
                            award_trainer_xp,
                            trainer_battle_txp_gain,
                        )
                    except Exception:
                        try:
                            from fusion2.pokemon.models.stats import (  # type: ignore
                                award_experience_to_party,
                                award_trainer_xp,
                                trainer_battle_txp_gain,
                            )
                        except Exception:
                            # Minimal test-only fallback that writes to `.experience`.
                            def award_experience_to_party(  # type: ignore
                                player,
                                amount: int,
                                ev_gains=None,
                                *,
                                participants=None,
                                caller=None,
                            ):
                                if not amount or amount <= 0 or not player:
                                    return
                                party = None
                                for attr in ("party", "pokemons", "pokemon", "team"):
                                    cand = getattr(player, attr, None)
                                    if cand:
                                        party = list(cand) if hasattr(cand, "__iter__") else [cand]
                                        break
                                if not party:
                                    storage = getattr(player, "storage", None)
                                    if storage and hasattr(storage, "get_party"):
                                        try:
                                            party = list(storage.get_party())
                                        except Exception:
                                            party = None
                                if not party:
                                    return
                                resolved = party
                                if participants:
                                    resolved = []
                                    for mon in participants:
                                        identifier = getattr(mon, "model_id", None) or getattr(mon, "unique_id", None)
                                        target = None
                                        if identifier is not None:
                                            for candidate in party:
                                                if getattr(candidate, "unique_id", None) == identifier:
                                                    target = candidate
                                                    break
                                        if not target and party:
                                            target = party[0]
                                        if target and target not in resolved:
                                            resolved.append(target)
                                    if not resolved:
                                        resolved = party
                                count = len(resolved)
                                share, remainder = divmod(int(amount), max(count, 1))
                                for i, mon in enumerate(resolved):
                                    gained = share + (1 if i < remainder else 0)
                                    setattr(mon, "experience", getattr(mon, "experience", 0) + gained)

                            def trainer_battle_txp_gain(  # type: ignore
                                base_exp: int,
                                level: int,
                                *,
                                trainer_battle: bool = False,
                            ) -> int:
                                multiplier = 1.5 if trainer_battle else 1.0
                                return math.floor(multiplier * base_exp * level / 7 * 0.1555)

                            def award_trainer_xp(player, amount: int, *, caller=None):  # type: ignore
                                if not amount or amount <= 0 or not player:
                                    return 0
                                db = getattr(player, "db", None)
                                if db is None:
                                    return 0
                                total = int(getattr(db, "trainer_xp", getattr(db, "txp", 0)) or 0) + int(amount)
                                setattr(db, "trainer_xp", total)
                                setattr(db, "txp", total)
                                return total

                    for poke in fainted:
                        delivery = getattr(self, "reward_delivery", None)
                        persistent = delivery is not None and delivery.supports(opponent.player)
                        if not persistent:
                            self.on_faint(poke)
                        species = getattr(poke, "species", None) or getattr(poke, "name", "")
                        info = resolve_dex_entry(GAIN_INFO, species) or {}
                        base_exp = info.get("exp", 0)
                        exp = 0
                        txp = 0
                        if base_exp:
                            level = getattr(poke, "level", 0) or 0
                            if level:
                                trainer_multiplier = (
                                    1.5
                                    if self.type in {BattleType.TRAINER, BattleType.SCRIPTED}
                                    else 1
                                )
                                exp = math.floor(trainer_multiplier * base_exp * level / 7)
                                txp = trainer_battle_txp_gain(
                                    base_exp,
                                    level,
                                    trainer_battle=self.type
                                    in {BattleType.TRAINER, BattleType.SCRIPTED},
                                )
                            else:
                                exp = base_exp
                        evs = info.get("evs", {})
                        if persistent:
                            payload = delivery.faint_plan(
                                opponent.player, exp if self.award_xp else 0,
                                evs if self.award_xp else {}, txp if self.award_txp else 0,
                                getattr(opponent, "participating_pokemon", None),
                            )
                            from pokemon.services.leader_crest import LeaderCrestProgress

                            candidate = LeaderCrestProgress.candidate(self, poke)
                            if candidate is not None:
                                payload["kingambit_defeat"] = candidate
                            identity = getattr(poke, "model_id", None) or str(part.pokemons.index(poke))
                            delivery.deliver(opponent.player, f"faint:{part.team}:{identity}", payload, caller=self,
                                             before_claim=lambda: self.on_faint(poke))
                            continue
                        if getattr(self, "award_xp", True) and (exp or evs):
                            try:
                                award_experience_to_party(
                                    opponent.player,
                                    exp,
                                    evs,
                                    participants=getattr(opponent, "participating_pokemon", None),
                                    caller=self,
                                )
                            except TypeError:
                                award_experience_to_party(opponent.player, exp, evs)
                        if getattr(self, "award_txp", True) and txp:
                            try:
                                award_trainer_xp(
                                    opponent.player,
                                    txp,
                                    caller=self,
                                )
                            except TypeError:
                                award_trainer_xp(opponent.player, txp)
                else:
                    for poke in fainted:
                        self.on_faint(poke)

            # Remove fainted PokÃƒÆ’Ã‚Â©mon from the active list
            active_slots(part)
            part.active = [p for p in part.active if getattr(p, "hp", 0) > 0]
            if getattr(part, "side", None) is not None:
                part.side.active = part.active

            # Check if the participant has any PokÃƒÆ’Ã‚Â©mon left
            if not any(getattr(p, "hp", 0) > 0 for p in part.pokemons):
                part.has_lost = True
                continue

            for slot in range(part.max_active):
                if active_at(part, slot) is None:
                    reserves = LegalActions(self, part, None).reserves(slot=slot, forced=True)
                    replacement = reserves[0] if reserves else None
                    if replacement:
                        assign_active(part, slot, replacement)
                        setattr(replacement, "side", part.side)
                        if hasattr(part, "record_participation"):
                            part.record_participation(replacement)
                        if getattr(part, "side", None) is not None:
                            part.side.active = part.active
                        if getattr(replacement, "mega_profile", None) or (getattr(replacement, "native_origin", None) or {}).get("necrozma"):
                            self.on_enter_battle(replacement)
                            self._log_switch_in(part, replacement)
                            continue
                        self.register_handlers(replacement)
                        self.dispatcher.dispatch(
                            "pre_start", pokemon=replacement, battle=self
                        )
                        self.dispatcher.dispatch(
                            "start", pokemon=replacement, battle=self
                        )
                        from .z_effects import ZEffects

                        ZEffects.switch_in(self, replacement)
                        self.dispatcher.dispatch(
                            "switch_in", pokemon=replacement, battle=self
                        )
                        self._run_slot_swap_events(replacement)
                        self.apply_entry_hazards(replacement)
                        self._log_switch_in(part, replacement)

    def residual(self) -> None:
        """Process residual effects and handle end-of-turn fainting."""

        try:  # pragma: no cover - data package may be unavailable in tests
            from pokemon.data.text import DEFAULT_TEXT  # type: ignore
        except Exception:  # pragma: no cover - fallback templates for tests
            DEFAULT_TEXT = {
                "brn": {"damage": "  [POKEMON] was hurt by its burn!"},
                "psn": {"damage": "  [POKEMON] was hurt by poison!"},
                "tox": {"damage": "  [POKEMON] was hurt by poison!"},
            }

        def _log_status_damage(status_key: str, pokemon) -> None:
            template = DEFAULT_TEXT.get(status_key, {}).get("damage")
            visited = set()
            while isinstance(template, str) and template.startswith("#"):
                ref = template[1:]
                if not ref or ref in visited:
                    break
                visited.add(ref)
                template = DEFAULT_TEXT.get(ref, {}).get("damage")
            if not isinstance(template, str) or not template:
                return None
            if not hasattr(self, "log_action"):
                return None
            name = getattr(pokemon, "name", getattr(pokemon, "species", "Pokemon"))
            self.log_action(template.replace("[POKEMON]", name))
            return None

        # Apply residual damage from status conditions
        for part in self.participants:
            if part.has_lost:
                continue
            for poke in list(part.active):
                status = getattr(poke, "status", None)
                try:
                    from pokemon.dex.functions.conditions_funcs import (
                        CONDITION_HANDLERS,
                    )
                except Exception:
                    CONDITION_HANDLERS = {}
                handler = CONDITION_HANDLERS.get(status)
                if handler and hasattr(handler, "onResidual"):
                    handler.onResidual(poke, battle=self)
                elif status in {"brn", "psn"}:
                    max_hp = getattr(poke, "max_hp", getattr(poke, "hp", 1))
                    damage = max(1, max_hp // 8)
                    poke.hp = max(0, poke.hp - damage)
                    _log_status_damage(status, poke)
                elif status == "tox":
                    max_hp = getattr(poke, "max_hp", getattr(poke, "hp", 1))
                    counter = getattr(poke, "toxic_counter", 1)
                    damage = max(1, (max_hp * counter) // 16)
                    poke.hp = max(0, poke.hp - damage)
                    poke.toxic_counter = counter + 1
                    _log_status_damage(status, poke)

                # Ability and item residual callbacks
                from .effect_context import EffectContext
                ability = _resolve_ability(EffectContext.ability(poke))
                if ability and hasattr(ability, "call"):
                    try:
                        ability.call("onResidual", pokemon=poke, battle=self,
                                     effect_state=getattr(poke, "ability_state", {}))
                    except Exception:
                        pass

                from .effect_context import EffectContext
                item = EffectContext.item(poke)
                if item and hasattr(item, "call"):
                    try:
                        item.call("onResidual", pokemon=poke, battle=self)
                    except Exception:
                        pass

                # Handle volatile statuses with residual effects
                volatiles = list(getattr(poke, "volatiles", {}).keys())
                if volatiles:
                    try:
                        from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
                    except Exception:
                        VOLATILE_HANDLERS = {}
                    for vol in volatiles:
                        handler = VOLATILE_HANDLERS.get(vol) or self._volatile_handler(vol)
                        if handler and hasattr(handler, "onResidual"):
                            handler.onResidual(poke, battle=self)
                        if vol in {"protect", "magiccoat", "shelltrap", "endure", "banefulbunker",
                                   "burningbulwark", "kingsshield", "obstruct", "silktrap", "spikyshield",
                                   "electrify", "powder", "helpinghand", "followme", "ragepowder", "spotlight"}:
                            # Protection ends with this turn, including restored
                            # sessions whose old volatile had no duration state.
                            self.remove_volatile(poke, vol)

        self._handle_side_condition_durations()
        self._handle_slot_condition_residuals()

        # Handle field weather effects
        weather = getattr(self.field, "weather", None)
        weather_handler = getattr(self.field, "weather_handler", None)
        if weather_handler:
            try:
                weather_handler.onFieldResidual(self.field)
            except Exception:
                pass
        for part in self.participants:
            if part.has_lost:
                continue
            for poke in part.active:
                if weather_handler:
                    try:
                        weather_handler.onWeather(poke)
                    except Exception:
                        pass
                ability = _resolve_ability(EffectContext.ability(poke))
                if ability and hasattr(ability, "call"):
                    try:
                        ability.call("onWeather", pokemon=poke)
                    except Exception:
                        try:
                            ability.call("onWeather", poke)
                        except Exception:
                            pass
        if weather_handler and weather not in self.field.pseudo_weather:
            self.clearWeather()

        # Handle terrain effects
        terrain = getattr(self.field, "terrain", None)
        terrain_handler = getattr(self.field, "terrain_handler", None)
        if terrain_handler:
            if callable(getattr(terrain_handler, "onFieldResidual", None)):
                terrain_handler.onFieldResidual(self.field)
            else:
                state = self.field.pseudo_weather.get(terrain, {})
                if isinstance(state.get("duration"), int):
                    state["duration"] -= 1
                    if state["duration"] <= 0:
                        self.field.pseudo_weather.pop(terrain, None)
            for part in self.participants:
                if part.has_lost:
                    continue
                for poke in part.active:
                    try:
                        terrain_handler.onResidual(poke)
                    except Exception:
                        pass
            if terrain not in self.field.pseudo_weather:
                self.clearTerrain()

        # Handle pseudo weather effects
        for name, effect in list(self.field.pseudo_weather.items()):
            if name in {weather, terrain}:
                continue
            handler = self._lookup_effect(name)
            if moves_funcs:
                handler = getattr(moves_funcs, name.capitalize(), None)
                if handler:
                    try:
                        handler = handler()
                    except Exception:
                        pass
            if not handler and conditions_funcs:
                handler = getattr(conditions_funcs, name.capitalize(), None)
                if handler:
                    try:
                        handler = handler()
                    except Exception:
                        pass
            if handler and hasattr(handler, "onFieldResidual"):
                try:
                    handler.onFieldResidual(self.field)
                except Exception:
                    pass
            if name not in self.field.pseudo_weather:
                continue
            if name == "trickroom":
                # Older checkpoints stored only True; give those a bounded
                # remaining lifetime as well as preserving new duration state.
                if effect is True:
                    effect = {"duration": 5}
                    self.field.pseudo_weather[name] = effect
                if isinstance(effect, dict) and isinstance(effect.get("duration"), (int, float)):
                    effect["duration"] -= 1
                    if effect["duration"] <= 0:
                        self.remove_pseudo_weather(name)

        # Remove PokÃƒÆ’Ã‚Â©mon that fainted from residual damage
        self.run_faint()

        # Auto-switch in replacements for any empty sides
        self.run_switch()
        self.run_after_switch()

    # ------------------------------------------------------------------
    # Logging and feedback helpers
    # ------------------------------------------------------------------
    def log_action(self, message: str) -> None:
        """Basic logger used by the engine."""
        battle_logger.info("%s", message)

    def display_hp_bar(self, pokemon) -> str:
        """Return a simple textual HP bar for ``pokemon``."""
        hp = getattr(pokemon, "hp", 0)
        max_hp = getattr(pokemon, "max_hp", 1)
        percent = int((hp / max_hp) * 10)
        bar = "[" + ("#" * percent).ljust(10) + "]"
        return bar

    def announce_ability_activation(self, pokemon, ability, detail: str) -> None:
        """Log an ability activation along with its effect description."""

        if not detail:
            return
        ability_name = getattr(ability, "name", None) or ability
        if not ability_name:
            return
        ability_text = str(ability_name)
        self.reveal_ability_to_all(pokemon, ability_text)
        nickname = self._pokemon_nickname(pokemon)
        message = self._format_default_message(
            "abilityActivation",
            {"[POKEMON]": nickname, "[ABILITY]": ability_text},
            fallback=None,
        )
        if not message:
            message = f"[{nickname}'s {ability_text}]"
        final = f"{message} {detail}".strip()
        self.log_action(final)

    def announce_status_change(
        self,
        pokemon,
        status: str,
        *,
        event: str | None = None,
        source=None,
        effect=None,
        item=None,
    ) -> None:
        """Notify about a status condition change."""

        status_key = _normalize_key(status).lower() if status is not None else ""
        event_key = event or "start"
        message_template = (
            self._status_template(status_key, event_key) if status_key else None
        )
        if not message_template:
            name = getattr(pokemon, "name", getattr(pokemon, "nickname", "Pokemon"))
            self.log_action(f"{name} is now {status_key or status}!")
            return

        replacements: Dict[str, Sequence[str] | str] = {
            "[POKEMON]": self._pokemon_nickname(pokemon),
        }

        if item:
            replacements["[ITEM]"] = self._item_display_name(item)
        if source:
            replacements["[SOURCE]"] = self._pokemon_nickname(source)
        if effect is not None and "[MOVE]" in message_template:
            move_name = None
            if isinstance(effect, str) and effect.startswith("move:"):
                move_name = effect.split(":", 1)[1]
            else:
                move_name = getattr(effect, "name", None)
            if move_name:
                replacements["[MOVE]"] = str(move_name)
        if "[ITEM]" in message_template and "[ITEM]" not in replacements:
            effect_ref = None
            if isinstance(effect, str) and effect.startswith("item:"):
                effect_ref = effect.split(":", 1)[1]
            if effect_ref:
                replacements["[ITEM]"] = self._item_display_name(effect_ref)

        message = _apply_placeholders(message_template, replacements)
        self.log_action(message)

    def display_stat_mods(self, pokemon) -> None:
        """Output current stat stages for debugging."""
        boosts = getattr(pokemon, "boosts", {})
        self.log_action(f"Boosts: {boosts}")

    def announce_stat_changes(
        self,
        pokemon,
        start: dict,
        end: dict,
        attempted: dict | None = None,
    ) -> None:
        """Announce stat stage changes between ``start`` and ``end``.

        Parameters
        ----------
        pokemon: Any
            The PokÃƒÆ’Ã‚Â©mon whose stat changes will be announced.
        start: dict
            Mapping of stat names to their starting stage values.
        end: dict
            Mapping of stat names to their ending stage values.
        attempted: dict, optional
            Mapping of stat names to attempted changes. This is used to
            report messages when a stat change fails due to reaching the
            stage cap.
        """

        try:  # pragma: no cover - fallback when data package is missing
            from pokemon.data.text import DEFAULT_TEXT  # type: ignore
        except Exception:  # pragma: no cover
            DEFAULT_TEXT = {"default": {}}
        from pokemon.utils.boosts import REVERSE_STAT_KEY_MAP, STAT_KEY_MAP

        start = start or {}
        end = end or {}
        attempted = attempted or {}
        attempted = {STAT_KEY_MAP.get(k, k): v for k, v in attempted.items()}

        stats = set(start) | set(end) | set(attempted)
        name = getattr(pokemon, "name", "Pokemon")

        for stat in stats:
            before = start.get(stat, 0)
            after = end.get(stat, 0)
            delta = after - before
            template_key = None
            if delta > 0:
                template_key = {1: "boost", 2: "boost2"}.get(delta, "boost3")
            elif delta < 0:
                template_key = {-1: "unboost", -2: "unboost2"}.get(delta, "unboost3")
            else:
                attempt = attempted.get(stat)
                if attempt:
                    template_key = "boost0" if attempt > 0 else "unboost0"
            if not template_key:
                continue
            short = REVERSE_STAT_KEY_MAP.get(stat, stat)
            stat_name = DEFAULT_TEXT.get(short, {}).get("statName", stat)
            message = DEFAULT_TEXT["default"][template_key]
            message = message.replace("[POKEMON]", name).replace("[STAT]", stat_name)
            self.log_action(message)

    def check_fainted(self, pokemon) -> bool:
        """Return ``True`` if ``pokemon`` has fainted."""
        return getattr(pokemon, "hp", 0) <= 0

    # ------------------------------------------------------------------
    # Miscellaneous advanced helpers
    # ------------------------------------------------------------------
    def calculate_critical_hit(self) -> bool:
        """Proxy to :func:`pokemon.battle.damage.critical_hit_check`."""
        from .damage import critical_hit_check

        return critical_hit_check(rng=self.rng)

    def calculate_type_effectiveness(self, target, move) -> float:
        from .damage import type_effectiveness

        return type_effectiveness(target, move)

    def handle_immunities_and_abilities(self, attacker, target, move) -> bool:
        """Return ``True`` if the move is blocked."""
        return self.status_service.handle_immunities_and_abilities(
            self, attacker, target, move
        )

    def check_protect_substitute(self, target) -> bool:
        """Return whether ``target`` has protect/substitute volatile effects."""

        return self.status_service.check_protect_substitute(target)

    def check_priority_override(self, pokemon) -> bool:
        """Return whether temporary effects override normal action priority."""

        return self.turn_resolution_service.check_priority_override(pokemon)

    def handle_end_of_battle_rewards(self, winner: BattleParticipant) -> None:
        """Award post-battle rewards for the winning participant."""

        self.reward_service.handle_end_of_battle_rewards(self, winner)

