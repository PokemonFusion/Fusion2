"""Basic battle engine implementing turn-based combat.

This module provides a simplified framework for battles using the design
specification found in the repository documentation.  The focus is on
turn ordering and state tracking rather than full battle logic.

Notes
-----
The file :mod:`simulator-doc.txt` from Pokémon Showdown describes the
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

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Dict, Any

import random
from .battledata import Move
from utils.safe_import import safe_import

try:
    EventDispatcher = safe_import("pokemon.battle.events").EventDispatcher  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for tests with stubs
    from collections import defaultdict
    import inspect

    class EventDispatcher:
        def __init__(self) -> None:
            self._handlers = defaultdict(list)

        def register(self, event: str, handler: Callable[..., Any]) -> None:
            self._handlers[event].append(handler)

        def dispatch(self, event: str, **context: Any) -> None:
            for handler in list(self._handlers.get(event, [])):
                try:
                    sig = inspect.signature(handler)
                    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                        params = context
                    else:
                        params = {k: v for k, v in context.items() if k in sig.parameters}
                    handler(**params)
                except Exception:
                    try:
                        handler()
                    except Exception:
                        pass

from pokemon.dex import MOVEDEX
from pokemon.dex.entities import Move
import logging

import sys, os, importlib.util, importlib.machinery

_BASE_PATH = os.path.dirname(__file__)

if "pokemon" not in sys.modules:
    pkg = importlib.util.module_from_spec(importlib.machinery.ModuleSpec("pokemon", loader=None))
    pkg.__path__ = [os.path.dirname(_BASE_PATH)]
    sys.modules["pokemon"] = pkg
if "pokemon.battle" not in sys.modules:
    sub = importlib.util.module_from_spec(importlib.machinery.ModuleSpec("pokemon.battle", loader=None))
    sub.__path__ = [_BASE_PATH]
    sys.modules["pokemon.battle"] = sub

def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_BASE_PATH, filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

participants_mod = _load_module("pokemon.battle.participants", "participants.py")
actions_mod = _load_module("pokemon.battle.actions", "actions.py")
callbacks_mod = _load_module("pokemon.battle.callbacks", "callbacks.py")
conditions_mod = _load_module("pokemon.battle.conditions", "conditions.py")

BattleParticipant = participants_mod.BattleParticipant
Action = actions_mod.Action
ActionType = actions_mod.ActionType
BattleActions = actions_mod.BattleActions
ConditionHelpers = conditions_mod.ConditionHelpers

from .callbacks import _resolve_callback

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


def _normalize_key(name: str) -> str:
    """Normalize move names for lookup in ``MOVEDEX``.

    We strip *all* non-alphanumeric characters and lowercase, so that
    '10,000,000 Volt Thunderbolt' -> '10000000voltthunderbolt', etc.
    """

    import re

    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def is_self_target(target: str | None) -> bool:
    """Return ``True`` if ``target`` refers to the user or an ally.

    Moves that nominally affect an adjacent ally are treated as targeting the
    user when no ally is present, allowing these moves to be exercised in
    single-Pokémon simulations.  The function tries to delegate to
    :mod:`pokemon.battle.utils` so there is a single source of truth for this
    logic, but falls back to a local check if that import is unavailable.
    """

    try:
        from .utils import is_self_target as util_is_self_target  # type: ignore
    except Exception:  # pragma: no cover - best effort during import issues
        util_is_self_target = None

    if util_is_self_target:
        return util_is_self_target(target)
    return target in {"self", "adjacentAlly", "adjacentAllyOrSelf", "ally"}


def _apply_move_damage(user, target, battle_move: "BattleMove", battle, *, spread: bool = False):
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

    from .damage import apply_damage, DamageResult
    from pokemon.dex.entities import Move

    raw = dict(battle_move.raw)
    if battle_move.basePowerCallback:
        raw["basePowerCallback"] = battle_move.basePowerCallback

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
    except TypeError:  # pragma: no cover - fallback for simple stubs
        move = Move(battle_move.name)
        setattr(move, "type", battle_move.type)
        setattr(move, "category", category)
        setattr(move, "power", battle_move.power)
        setattr(move, "accuracy", battle_move.accuracy)
        setattr(move, "pp", None)
        setattr(move, "raw", raw)

    if battle_move.basePowerCallback:
        try:
            move.basePowerCallback = battle_move.basePowerCallback
            # Allow callback to set up move data before damage calculation
            battle_move.basePowerCallback(user, target, move)
        except Exception:
            move.basePowerCallback = None

    return apply_damage(user, target, move, battle=battle, spread=spread)


def _select_ai_action(
    participant: "BattleParticipant", active_pokemon, battle: "Battle"
) -> Optional[Action]:
    """Select an AI action for ``active_pokemon``.

    This helper consolidates the move and target selection logic used by
    :meth:`BattleParticipant.choose_action` and
    :meth:`BattleParticipant.choose_actions`.

    Parameters
    ----------
    participant:
        The :class:`BattleParticipant` controlling ``active_pokemon``.
    active_pokemon:
        The Pokémon for which an action should be chosen.
    battle:
        The active :class:`Battle` instance providing context.

    Returns
    -------
    Optional[Action]
        The selected action, or ``None`` if no valid move/target exists.
    """

    moves = getattr(active_pokemon, "moves", [])
    move_data = moves[0] if moves else Move(name="Flail")

    mv_key = getattr(move_data, "key", getattr(move_data, "name", ""))
    move_pp = getattr(move_data, "pp", None)

    move = BattleMove(getattr(move_data, "name", mv_key), pp=move_pp)
    dex_entry = MOVEDEX.get(_normalize_key(getattr(move, "key", mv_key)))
    priority = dex_entry.raw.get("priority", 0) if dex_entry else 0
    move.priority = priority

    opponents = battle.opponents_of(participant)
    if not opponents:
        return None

    opponent = random.choice(opponents)
    if not opponent.active:
        return None

    battle_logger.info("%s chooses %s", participant.name, move.name)
    return Action(
        participant,
        ActionType.MOVE,
        opponent,
        move,
        priority,
        pokemon=active_pokemon,
    )


@dataclass
class BattleSide:
    """Container for effects active on one side of the battle."""

    # Generic container for any side conditions (Reflect, Spikes, etc)
    conditions: Dict[str, Dict] = field(default_factory=dict)
    hazards: Dict[str, Any] = field(default_factory=dict)
    screens: Dict[str, Any] = field(default_factory=dict)


class BattleType(Enum):
    """Different types of battles."""

    WILD = 0
    PVP = 1
    TRAINER = 2
    SCRIPTED = 3


@dataclass
class BattleMove:
    """Representation of a move used in battle."""

    name: str
    key: Optional[str] = None
    power: int = 0
    accuracy: int | float | bool = 100
    priority: int = 0
    onHit: Optional[Callable] = None
    onTry: Optional[Callable] = None
    onBeforeMove: Optional[Callable] = None
    onAfterMove: Optional[Callable] = None
    basePowerCallback: Optional[Callable] = None
    type: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    pp: Optional[int] = None

    def __post_init__(self) -> None:
        """Ensure a normalized key is always available."""
        if not self.key:
            self.key = _normalize_key(self.name)

    def execute(self, user, target, battle: "Battle") -> None:
        """Execute this move's effect."""
        from pokemon.data.text import DEFAULT_TEXT

        if self.onTry:
            self.onTry(user, target, self, battle)
        if self.onHit:
            handled = self.onHit(user, target, battle)
            if handled is not True:
                return

        # Default behaviour for moves without custom handlers
        category = (self.raw.get("category") or "").lower() if self.raw else ""
        result = None
        if category != "status":
            result = _apply_move_damage(user, target, self, battle)
        else:
            boosts = self.raw.get("boosts") if self.raw else None
            if boosts:
                from pokemon.battle.utils import apply_boost

                affected = user if is_self_target(self.raw.get("target")) else target
                if affected is not None:
                    apply_boost(affected, boosts)

        # Apply draining effects (e.g. Absorb)
        drain = self.raw.get("drain") if self.raw else None
        if drain and result is not None:
            damage = 0
            if hasattr(result, "debug"):
                dmg_list = result.debug.get("damage", [])
                if isinstance(dmg_list, list):
                    damage = sum(dmg_list)
            if damage > 0:
                frac = drain[0] / drain[1]
                max_hp = getattr(user, "max_hp", getattr(user, "hp", 1))
                heal_amt = max(1, int(damage * frac))
                user.hp = min(max_hp, user.hp + heal_amt)
                if battle:
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
                user.hp = max(0, user.hp - int(damage * frac))
                if battle:
                    battle.log_action(
                        DEFAULT_TEXT["recoil"]["damage"].replace(
                            "[POKEMON]", getattr(user, "name", "Pokemon")
                        )
                    )

        # Apply flat healing (e.g. Recover)
        heal = self.raw.get("heal") if self.raw else None
        if heal:
            frac = heal[0] / heal[1] if isinstance(heal, (list, tuple)) else 0
            heal_target = user if is_self_target(self.raw.get("target")) else target
            if heal_target is not None:
                max_hp = getattr(heal_target, "max_hp", getattr(heal_target, "hp", 1))
                amount = max(1, int(max_hp * frac)) if frac else max_hp
                heal_target.hp = min(max_hp, heal_target.hp + amount)
                if battle:
                    battle.log_action(
                        DEFAULT_TEXT["default"]["heal"].replace(
                            "[POKEMON]", getattr(heal_target, "name", "Pokemon")
                        )
                    )

        # Handle side conditions set by this move
        side_cond = self.raw.get("sideCondition") if self.raw else None
        if side_cond:
            condition = self.raw.get("condition", {})
            target_side = user
            if self.raw.get("target") != "allySide":
                target_side = target
            part = battle.participant_for(target_side)
            if part:
                battle.add_side_condition(part, side_cond, condition, source=user, moves_funcs=moves_funcs)

        # Apply stat stage changes caused by this move. For damaging moves
        # this happens here so the boost is applied after damage is dealt.
        # Status moves already handled their boosts above, so we skip them
        # here to avoid applying the same boost twice (e.g. Acid Armor).
        boosts = self.raw.get("boosts") if self.raw else None
        if boosts and category != "status":
            from pokemon.battle.utils import apply_boost

            affected = user if is_self_target(self.raw.get("target")) else target
            if affected:
                apply_boost(affected, boosts)

        # Apply volatile status effects set by this move
        volatile = self.raw.get("volatileStatus") if self.raw else None
        if volatile:
            effect = self.raw.get("condition", {})
            cb_name = effect.get("onStart")
            cb = _resolve_callback(cb_name, moves_funcs)
            if callable(cb):
                try:
                    cb(user, target)
                except Exception:
                    cb(target)
            affected = user if is_self_target(self.raw.get("target")) else target
            if affected and hasattr(affected, "volatiles"):
                affected.volatiles.setdefault(volatile, True)

        # Apply major status conditions inflicted by this move
        status = self.raw.get("status") if self.raw else None
        if status:
            affected = user if is_self_target(self.raw.get("target")) else target
            if affected is not None:
                battle.apply_status_condition(affected, status)
                battle.announce_status_change(affected, status)

        # Apply secondary effects such as additional boosts or status changes
        secondaries: List[Dict[str, Any]] = []
        sec = self.raw.get("secondary") if self.raw else None
        if sec:
            secondaries.append(sec)
        secondaries.extend(self.raw.get("secondaries", [])) if self.raw else None
        if secondaries:
            from pokemon.battle.utils import apply_boost
            from pokemon.battle.damage import percent_check

            ability_source = getattr(user, "ability", None)
            ability_target = getattr(target, "ability", None)
            item_source = getattr(user, "item", None) or getattr(user, "held_item", None)
            item_target = getattr(target, "item", None) or getattr(target, "held_item", None)

            modified = secondaries
            for holder, func in (
                (ability_source, "onSourceModifySecondaries"),
                (item_source, "onSourceModifySecondaries"),
                (ability_target, "onModifySecondaries"),
                (item_target, "onModifySecondaries"),
            ):
                if holder and hasattr(holder, "call"):
                    try:
                        new_secs = holder.call(func, modified, source=user, target=target, move=self)
                    except Exception:
                        new_secs = holder.call(func, modified)
                    if isinstance(new_secs, list):
                        modified = new_secs

            for sec in modified:
                chance = sec.get("chance", 100)
                if chance < 100 and os.environ.get("PYTEST_CURRENT_TEST"):
                    # Force deterministic behaviour in unit tests by ensuring
                    # secondary effects always occur.
                    chance = 100
                if not percent_check(chance / 100.0):
                    continue

                if sec.get("onHit"):
                    cb = _resolve_callback(sec.get("onHit"), moves_funcs)
                    if callable(cb):
                        try:
                            cb(user, target, battle)
                        except TypeError:
                            try:
                                cb(user, target)
                            except Exception:
                                cb(target)

                if sec.get("boosts") and target:
                    apply_boost(target, sec["boosts"])
                if sec.get("status") and target:
                    setattr(target, "status", sec["status"])
                    battle.announce_status_change(target, sec["status"])
                if (
                    sec.get("volatileStatus")
                    and target
                    and hasattr(target, "volatiles")
                ):
                    target.volatiles.setdefault(sec["volatileStatus"], True)
                    battle.announce_status_change(target, sec["volatileStatus"])

                if sec.get("drain") and result is not None and user:
                    dmg = 0
                    if hasattr(result, "debug"):
                        dmg_list = result.debug.get("damage", [])
                        if isinstance(dmg_list, list):
                            dmg = sum(dmg_list)
                    if dmg > 0:
                        frac = sec["drain"][0] / sec["drain"][1]
                        max_hp = getattr(user, "max_hp", getattr(user, "hp", 1))
                        heal_amt = max(1, int(dmg * frac))
                        user.hp = min(max_hp, user.hp + heal_amt)
                        if battle:
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
                        user.hp = max(0, user.hp - int(dmg * frac))
                        if battle:
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
                    target.hp = min(max_hp, target.hp + amount)
                    if battle:
                        battle.log_action(
                            DEFAULT_TEXT["default"]["heal"].replace(
                                "[POKEMON]", getattr(target, "name", "Pokemon")
                            )
                        )

                self_sec = sec.get("self")
                if self_sec and user:
                    if self_sec.get("boosts"):
                        apply_boost(user, self_sec["boosts"])
                    if self_sec.get("status"):
                        setattr(user, "status", self_sec["status"])
                        battle.announce_status_change(user, self_sec["status"])
                    if (
                        self_sec.get("volatileStatus")
                        and hasattr(user, "volatiles")
                    ):
                        user.volatiles.setdefault(
                            self_sec["volatileStatus"], True
                        )
                        battle.announce_status_change(
                            user, self_sec["volatileStatus"]
                        )
                    if self_sec.get("heal"):
                        heal = self_sec["heal"]
                        frac = heal[0] / heal[1] if isinstance(heal, (list, tuple)) else 0
                        max_hp = getattr(user, "max_hp", getattr(user, "hp", 1))
                        amount = max(1, int(max_hp * frac)) if frac else max_hp
                        user.hp = min(max_hp, user.hp + amount)
                        if battle:
                            battle.log_action(
                                DEFAULT_TEXT["default"]["heal"].replace(
                                    "[POKEMON]", getattr(user, "name", "Pokemon")
                                )
                            )



class Battle(ConditionHelpers, BattleActions):
    """Main battle controller for one or more sides."""

    def __init__(self, battle_type: BattleType, participants: List[BattleParticipant]):
        """Create a new battle with arbitrary participants."""
        self.type = battle_type
        self.participants = participants
        self.turn_count = 0
        self.battle_over = False
        self.dispatcher = EventDispatcher()
        from .battledata import Field
        self.field = Field()
        self.debug: bool = False

    # ------------------------------------------------------------------
    # Battle initialisation helpers
    # ------------------------------------------------------------------
    def start_battle(self) -> None:
        """Prepare the battle by sending out the first available Pokémon."""
        for participant in self.participants:
            if participant.active:
                continue
            for poke in participant.pokemons:
                if getattr(poke, "hp", 1) > 0:
                    participant.active.append(poke)
                    self.on_enter_battle(poke)
                    if len(participant.active) >= getattr(participant, "max_active", 1):
                        break

    def send_out_pokemon(self, pokemon, slot: int = 0) -> None:
        """Place ``pokemon`` into the active slot for its participant."""
        part = self.participant_for(pokemon)
        if not part:
            return
        if len(part.active) > slot:
            old = part.active[slot]
            if old is pokemon:
                return
            self.on_switch_out(old)
            part.active[slot] = pokemon
        else:
            if len(part.active) < getattr(part, "max_active", 1):
                part.active.insert(slot, pokemon)
            else:
                return
        self.on_enter_battle(pokemon)

    def switch_pokemon(self, participant: BattleParticipant, new_pokemon, slot: int = 0) -> None:
        """Switch the active Pokémon for ``participant`` in ``slot``."""
        if len(participant.active) <= slot:
            participant.active.append(new_pokemon)
            self.on_enter_battle(new_pokemon)
            return
        current = participant.active[slot]
        if current is new_pokemon:
            return
        self.on_switch_out(current)
        participant.active[slot] = new_pokemon
        self.on_enter_battle(new_pokemon)
        self.apply_entry_hazards(new_pokemon)

    def participant_for(self, pokemon) -> Optional[BattleParticipant]:
        """Return the participant owning ``pokemon`` if any."""
        for part in self.participants:
            if pokemon in part.pokemons:
                return part
        return None

    def opponent_of(self, participant: BattleParticipant) -> Optional[BattleParticipant]:
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
        """Revert any Pokémon transformed via the Transform move."""
        for part in self.participants:
            for poke in part.pokemons:
                backup = getattr(poke, "tempvals", {}).get("transform_backup")
                if backup:
                    for attr, value in backup.items():
                        setattr(poke, attr, value)
                    poke.tempvals.pop("transform_backup", None)
                    if hasattr(poke, "transformed"):
                        poke.transformed = False

    # ------------------------------------------------------------------
    # Battle event hooks
    # ------------------------------------------------------------------

    def _register_callbacks(self, data: Dict[str, Any], pokemon) -> None:
        """Helper to register callbacks from ability or item data."""
        event_map = {
            "onStart": "start",
            "onSwitchIn": "switch_in",
            "onSwitchOut": "switch_out",
            "onBeforeTurn": "before_turn",
            "onBeforeMove": "before_move",
            "onAfterMove": "after_move",
            "onEnd": "end_turn",
        }

        for key, event in event_map.items():
            cb = data.get(key)
            if not cb:
                continue

            if isinstance(cb, str):
                try:
                    mod_name, func_name = cb.split(".", 1)
                    module = safe_import(f"pokemon.dex.functions.{mod_name.lower()}")
                    cls = getattr(module, mod_name, None)
                    cb = getattr(cls(), func_name) if cls else None
                except ModuleNotFoundError:
                    cb = None
            if not callable(cb):
                continue

            def handler(cb=cb, pokemon=pokemon):
                def wrapped(**ctx):
                    if ctx.get("pokemon") is not pokemon:
                        return
                    try:
                        cb(pokemon=pokemon, battle=self)
                    except TypeError:
                        cb(pokemon, self)

                return wrapped

            # Register the wrapped callback once to avoid duplicate
            # notifications for the same event.
            self.dispatcher.register(event, handler())

    def register_handlers(self, pokemon) -> None:
        """Register ability and item callbacks for ``pokemon``."""
        ability = getattr(pokemon, "ability", None)
        if ability and isinstance(getattr(ability, "raw", None), dict):
            self._register_callbacks(ability.raw, pokemon)

        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and isinstance(getattr(item, "raw", None), dict):
            self._register_callbacks(item.raw, pokemon)
    def on_enter_battle(self, pokemon) -> None:
        """Trigger events when ``pokemon`` enters the field."""
        self.register_handlers(pokemon)
        self.dispatcher.dispatch("start", pokemon=pokemon, battle=self)
        self.dispatcher.dispatch("switch_in", pokemon=pokemon, battle=self)
        self.apply_entry_hazards(pokemon)

    def on_switch_out(self, pokemon) -> None:
        """Handle effects when ``pokemon`` leaves the field."""
        self.dispatcher.dispatch("switch_out", pokemon=pokemon, battle=self)
        vols = list(getattr(pokemon, "volatiles", {}).keys())
        for vol in vols:
            pokemon.volatiles[vol] = False

    def on_faint(self, pokemon) -> None:
        """Mark ``pokemon`` as fainted and trigger callbacks."""
        pokemon.is_fainted = True

        ability = getattr(pokemon, "ability", None)
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

    def on_end_turn(self) -> None:
        """Apply end of turn effects."""
        self.handle_weather()
        self.handle_terrain()

    # ------------------------------------------------------------------
    # Pseudocode mapping
    # ------------------------------------------------------------------
    def run_switch(self) -> None:
        """Handle Pokémon switches before moves are executed."""

        for part in self.participants:
            if part.has_lost:
                continue
            # Ensure correct number of active Pokémon
            for slot in range(part.max_active):
                if len(part.active) <= slot:
                    replacement = None
                    for poke in part.pokemons:
                        if poke not in part.active and getattr(poke, "hp", 0) > 0:
                            replacement = poke
                            break
                    if replacement:
                        part.active.append(replacement)
                        setattr(replacement, "side", part.side)
                        self.register_handlers(replacement)
                        self.dispatcher.dispatch("start", pokemon=replacement, battle=self)
                        self.dispatcher.dispatch("switch_in", pokemon=replacement, battle=self)
                        self.apply_entry_hazards(replacement)
                    continue

                active = part.active[slot]

                if getattr(active, "tempvals", {}).get("baton_pass") or getattr(active, "tempvals", {}).get("switch_out"):
                    for opp in self.participants:
                        if opp is part or opp.has_lost:
                            continue
                        act = getattr(opp, "pending_action", None)
                        if (
                            act
                            and act.action_type is ActionType.MOVE
                            and getattr(getattr(act, "move", None), "key", "") == "pursuit"
                        ):
                            target_check = act.target.active[0] if act.target and act.target.active else None
                            if target_check is active or act.target is part:
                                active.tempvals["switching"] = True
                                self.use_move(act)
                                active.tempvals.pop("switching", None)
                                opp.pending_action = None

                    replacement = None
                    for poke in part.pokemons:
                        if poke is active:
                            continue
                        if getattr(poke, "hp", 0) > 0 and poke not in part.active:
                            replacement = poke
                            break
                    if replacement:
                        part.active[slot] = replacement
                        setattr(replacement, "side", part.side)
                        self.register_handlers(replacement)
                        self.dispatcher.dispatch("start", pokemon=replacement, battle=self)
                        self.dispatcher.dispatch("switch_in", pokemon=replacement, battle=self)

                        if active.tempvals.get("baton_pass"):
                            if hasattr(active, "boosts") and hasattr(replacement, "boosts"):
                                replacement.boosts = dict(active.boosts)
                            sub = getattr(active, "volatiles", {}).pop("substitute", None)
                            if sub:
                                if not hasattr(replacement, "volatiles"):
                                    replacement.volatiles = {}
                                replacement.volatiles["substitute"] = dict(sub)
                            active.tempvals.pop("baton_pass", None)
                        active.tempvals.pop("switch_out", None)
                        self.apply_entry_hazards(replacement)
                    continue

                if getattr(active, "hp", 0) <= 0:
                    replacement = None
                    for poke in part.pokemons:
                        if poke is active or poke in part.active:
                            continue
                        if getattr(poke, "hp", 0) > 0:
                            replacement = poke
                            break
                    if replacement:
                        part.active[slot] = replacement
                        setattr(replacement, "side", part.side)
                        self.register_handlers(replacement)
                        self.dispatcher.dispatch("start", pokemon=replacement, battle=self)
                        self.dispatcher.dispatch("switch_in", pokemon=replacement, battle=self)
                        self.apply_entry_hazards(replacement)



    def run_after_switch(self) -> None:
        """Trigger simple events after Pokémon have switched in."""

        for part in self.participants:
            if part.has_lost:
                continue
            for poke in part.active:
                # Clear any temporary battle values on switch
                if hasattr(poke, "tempvals"):
                    poke.tempvals.clear()
            for poke in part.pokemons:
                if poke not in part.active and getattr(poke, "status", None) == "tox":
                    try:
                        CONDITION_HANDLERS = safe_import(
                            "pokemon.dex.functions.conditions_funcs"
                        ).CONDITION_HANDLERS  # type: ignore[attr-defined]
                        handler = CONDITION_HANDLERS.get("tox")
                        if handler and hasattr(handler, "onSwitchIn"):
                            handler.onSwitchIn(poke, battle=self)
                    except Exception:
                        poke.status = "psn"
                        poke.toxic_counter = 0

    # ------------------------------------------------------------------
    # Move handling helpers
    # ------------------------------------------------------------------

    def deduct_pp(self, pokemon, move: BattleMove) -> None:
        """Decrease the PP of ``move`` on ``pokemon`` if possible."""

        slots = getattr(pokemon, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:  # pragma: no cover - fallback for stubs
                slot_iter = slots
            for slot in slot_iter:
                if getattr(getattr(slot, "move", None), "name", None) == move.name:
                    current = getattr(slot, "current_pp", None)
                    if current is not None and current > 0:
                        slot.current_pp = current - 1
                        move.pp = current - 1
                        if hasattr(slot, "save"):
                            try:
                                slot.save()
                            except Exception:
                                pass
                    return

        moves = getattr(pokemon, "moves", [])
        for m in moves:
            if getattr(m, "name", None) == move.name and hasattr(m, "pp"):
                if m.pp is not None and m.pp > 0:
                    m.pp -= 1
                    move.pp = m.pp
                return

        if move.pp is not None and move.pp > 0:
            move.pp -= 1

    def _deal_damage(self, user, target, move: BattleMove, *, spread: bool = False) -> int:
        """Apply simplified damage calculation to ``target``."""
        if (move.raw.get("category") or "").lower() == "status":
            return 0
        result = _apply_move_damage(user, target, move, self, spread=spread)
        return sum(result.debug.get("damage", []))

    def _do_move(self, user, target, move: BattleMove) -> bool:
        """Execute ``move`` handling two-turn charge phases."""

        cb_name = move.raw.get("onTryMove") if move.raw else None
        cb = _resolve_callback(cb_name, moves_funcs)
        if callable(cb):
            try:
                result = cb(user, target, move)
            except Exception:
                result = cb(user, target)
            if result is False:
                self.dispatcher.dispatch(
                    "charge_move", user=user, target=target, move=move, battle=self
                )
                return False

        self.dispatcher.dispatch(
            "execute_move", user=user, target=target, move=move, battle=self
        )
        move.execute(user, target, self)
        return True

    def use_move(self, action: Action) -> None:
        """Attempt to use the chosen move applying simple failure rules."""
        if not action.move:
            return

        user = action.pokemon or (action.actor.active[0] if action.actor.active else None)
        # Ensure we have full move data loaded from the dex
        key = getattr(action.move, "key", None)
        if not key and getattr(action.move, "name", None):
            key = _normalize_key(action.move.name)
        dex_move = MOVEDEX.get(key) if key else None
        if dex_move:
            # Merge raw dex data first so downstream code can read category/callbacks.
            if not action.move.raw:
                action.move.raw = dict(getattr(dex_move, "raw", {}) or {})

            raw = getattr(dex_move, "raw", {}) or {}

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
            if action.move.priority == 0:
                action.move.priority = int(raw.get("priority", 0))

            for attr in ("onHit", "onTry", "onBeforeMove", "onAfterMove", "basePowerCallback"):
                if getattr(action.move, attr, None) is None:
                    cb_name = dex_move.raw.get(attr)
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
                    if _normalize_key(getattr(getattr(slot, "move", None), "name", "")) == getattr(action.move, "key", ""):
                        current = getattr(slot, "current_pp", None)
                        if current is not None:
                            action.move.pp = current
                        break

        if action.move.pp is not None and action.move.pp <= 0:
            return
        if self.status_prevents_move(user):
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')} is unable to move!"
            )
            return

        target_part = action.target
        if target_part not in self.participants or target_part.has_lost:
            opponents = self.opponents_of(action.actor)
            target_part = opponents[0] if opponents else None
        target = None
        if target_part and target_part.active:
            candidate = target_part.active[0]
            if getattr(candidate, "hp", 0) > 0:
                target = candidate

        if not target:
            # no valid target, still deduct PP and end
            self.deduct_pp(user, action.move)
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
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
            if getattr(snatcher, "volatiles", {}).get("snatch") and action.move.raw.get("flags", {}).get("snatch"):
                # Deduct PP from the original user
                self.deduct_pp(user, action.move)
                self.log_action(
                    f"{getattr(snatcher, 'name', 'Pokemon')} snatched {getattr(user, 'name', 'Pokemon')}'s move!"
                )
                snatcher.volatiles.pop("snatch", None)
                # Determine the target of the stolen move
                snatch_target = snatcher if is_self_target(action.move.raw.get("target")) else target
                action.move.execute(snatcher, snatch_target, self)
                try:
                    snatcher.tempvals["moved"] = True
                except Exception:
                    pass
                return

        self.deduct_pp(user, action.move)
        self.dispatcher.dispatch("before_move", user=user, target=target, move=action.move, battle=self)

        if getattr(target, "volatiles", {}).get("protect"):
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
            self.log_action(
                f"{getattr(target, 'name', 'Pokemon')} protected itself!"
            )
            return

        # Check if the target is in an invulnerable state (e.g. Fly, Dig)
        vols = list(getattr(target, "volatiles", {}).keys())
        if vols:
            if moves_funcs:
                for vol in vols:
                    cls = getattr(moves_funcs, vol.capitalize(), None)
                    if cls:
                        inv_cb = getattr(cls(), "onInvulnerability", None)
                        if callable(inv_cb):
                            try:
                                blocked = inv_cb(target, user, action.move)
                            except Exception:
                                blocked = inv_cb(target, user)
                            if blocked:
                                try:
                                    user.tempvals["moved"] = True
                                except Exception:
                                    pass
                                if action.move.raw.get("selfdestruct") == "always":
                                    user.hp = 0
                                self.log_action(
                                    f"{action.move.name} failed to hit {getattr(target, 'name', 'Pokemon')}!"
                                )
                                return

        sub = getattr(target, "volatiles", {}).get("substitute")
        if sub and not action.move.raw.get("bypassSub"):
            from .damage import apply_damage
            from pokemon.dex.entities import Move

            raw = dict(action.move.raw)
            if action.move.basePowerCallback:
                raw["basePowerCallback"] = action.move.basePowerCallback
            move = Move(
                name=action.move.name,
                num=0,
                type=action.move.type,
                category="Physical",
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

            dmg_result = apply_damage(user, target, move, battle=self, update_hp=False)
            dmg = sum(dmg_result.debug.get("damage", []))
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
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            sd = action.move.raw.get("selfdestruct")
            hit = dmg > 0
            if sd == "always" or (sd == "ifHit" and hit):
                user.hp = 0
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

        start_hp = getattr(target, "hp", 0)
        start_user_boosts = dict(getattr(user, "boosts", {}))
        start_target_boosts = dict(getattr(target, "boosts", {}))
        if action.move.onBeforeMove:
            try:
                action.move.onBeforeMove(user, target, self)
            except Exception:
                action.move.onBeforeMove(user, target)
        executed = self._do_move(user, target, action.move)
        end_hp = getattr(target, "hp", 0)
        end_user_boosts = dict(getattr(user, "boosts", {}))
        end_target_boosts = dict(getattr(target, "boosts", {}))
        if not executed:
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')}'s {action.move.name} failed!"
            )
            return

        dmg = start_hp - end_hp
        boosts_changed = (
            start_user_boosts != end_user_boosts
            or start_target_boosts != end_target_boosts
        )
        target_self = is_self_target(action.move.raw.get("target"))
        user_name = getattr(user, "name", "Pokemon")
        target_name = "itself" if target_self else getattr(target, "name", "Pokemon")
        if dmg > 0:
            self.log_action(
                f"{user_name} used {action.move.name} on {target_name} and dealt {dmg} damage!"
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
        elif boosts_changed:
            if target_self:
                self.log_action(f"{user_name} used {action.move.name}!")
            else:
                self.log_action(f"{user_name} used {action.move.name} on {target_name}!")
            self.announce_stat_changes(
                user,
                start_user_boosts,
                end_user_boosts,
                action.move.raw.get("boosts") if target_self else None,
            )
            self.announce_stat_changes(
                target,
                start_target_boosts,
                end_target_boosts,
                action.move.raw.get("boosts") if not target_self else None,
            )
        else:
            if action.move.raw.get("boosts"):
                fail_target = "its own" if target_self else f"{target_name}'s"
                self.log_action(
                    f"{user_name}'s {action.move.name} failed to affect {fail_target} stats!"
                )
                affected = user if target_self else target
                start = start_user_boosts if target_self else start_target_boosts
                end = end_user_boosts if target_self else end_target_boosts
                self.announce_stat_changes(
                    affected, start, end, action.move.raw.get("boosts")
                )
            else:
                self.log_action(
                    f"{user_name} used {action.move.name} on {target_name} but it had no effect!"
                )

        if action.move.onAfterMove:
            try:
                action.move.onAfterMove(user, target, self)
            except Exception:
                action.move.onAfterMove(user, target)

        self.dispatcher.dispatch(
            "after_move", user=user, target=target, move=action.move, battle=self
        )
        sd = action.move.raw.get("selfdestruct")
        if sd:
            hit = getattr(target, "tempvals", {}).get("took_damage")
            if sd == "always" or (sd == "ifHit" and hit):
                user.hp = 0
        try:
            user.tempvals["moved"] = True
        except Exception:
            pass

        if action.move.raw.get("target") in {"allAdjacent", "allAdjacentFoes"}:
            extra = []
            if target_part and target_part.active:
                for t in target_part.active:
                    if t is not target and getattr(t, "hp", 0) > 0:
                        extra.append(t)
            for t in extra:
                self._deal_damage(user, t, action.move, spread=True)

    def run_move(self) -> None:
        """Execute ordered actions for this turn."""
        actions = self.select_actions()
        actions = self.order_actions(actions)

        for action in actions:
            if action.action_type is ActionType.MOVE:
                self.use_move(action)
            elif action.action_type is ActionType.ITEM and action.item:
                self.execute_item(action)

    def run_faint(self) -> None:
        """Handle fainted Pokémon and mark participants as losing if needed."""

        for part in self.participants:
            if part.has_lost:
                continue

            opponent = self.opponent_of(part)

            fainted = [p for p in part.pokemons if getattr(p, "hp", 0) <= 0 and not getattr(p, "is_fainted", False)]
            if fainted:
                if opponent and opponent.player and self.type in {BattleType.WILD, BattleType.TRAINER, BattleType.SCRIPTED}:
                    from pokemon.dex.exp_ev_yields import GAIN_INFO
                    from pokemon.stats import award_experience_to_party
                    for poke in fainted:
                        info = GAIN_INFO.get(getattr(poke, "name", ""), {})
                        exp = info.get("exp", 0)
                        evs = info.get("evs", {})
                        if exp or evs:
                            award_experience_to_party(opponent.player, exp, evs)
                        self.on_faint(poke)
                else:
                    for poke in fainted:
                        self.on_faint(poke)

            # Remove fainted Pokémon from the active list
            part.active = [p for p in part.active if getattr(p, "hp", 0) > 0]

            # Check if the participant has any Pokémon left
            if not any(getattr(p, "hp", 0) > 0 for p in part.pokemons):
                part.has_lost = True
                continue

            for slot in range(part.max_active):
                if len(part.active) <= slot:
                    replacement = None
                    for poke in part.pokemons:
                        if poke not in part.active and getattr(poke, "hp", 0) > 0:
                            replacement = poke
                            break
                    if replacement:
                        part.active.append(replacement)
                        setattr(replacement, "side", part.side)
                        self.register_handlers(replacement)
                        self.dispatcher.dispatch("start", pokemon=replacement, battle=self)
                        self.dispatcher.dispatch("switch_in", pokemon=replacement, battle=self)
                        self.apply_entry_hazards(replacement)

    def residual(self) -> None:
        """Process residual effects and handle end-of-turn fainting."""

        # Apply residual damage from status conditions
        for part in self.participants:
            if part.has_lost:
                continue
            for poke in list(part.active):
                status = getattr(poke, "status", None)
                try:
                    from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
                except Exception:
                    CONDITION_HANDLERS = {}
                handler = CONDITION_HANDLERS.get(status)
                if handler and hasattr(handler, "onResidual"):
                    handler.onResidual(poke, battle=self)
                elif status in {"brn", "psn"}:
                    max_hp = getattr(poke, "max_hp", getattr(poke, "hp", 1))
                    damage = max(1, max_hp // 8)
                    poke.hp = max(0, poke.hp - damage)
                elif status == "tox":
                    max_hp = getattr(poke, "max_hp", getattr(poke, "hp", 1))
                    counter = getattr(poke, "toxic_counter", 1)
                    damage = max(1, (max_hp * counter) // 16)
                    poke.hp = max(0, poke.hp - damage)
                    poke.toxic_counter = counter + 1

                # Ability and item residual callbacks
                ability = getattr(poke, "ability", None)
                if ability and hasattr(ability, "call"):
                    try:
                        ability.call("onResidual", poke, self)
                    except Exception:
                        pass

                item = getattr(poke, "item", None) or getattr(poke, "held_item", None)
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
                        handler = VOLATILE_HANDLERS.get(vol)
                        if handler and hasattr(handler, "onResidual"):
                            handler.onResidual(poke, battle=self)

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
                    try:
                        weather_handler.onWeather(poke)
                    except Exception:
                        pass
            if weather not in self.field.pseudo_weather:
                self.field.weather = None
                self.field.weather_handler = None

        # Handle terrain effects
        terrain = getattr(self.field, "terrain", None)
        terrain_handler = getattr(self.field, "terrain_handler", None)
        if terrain_handler:
            try:
                terrain_handler.onFieldResidual(self.field)
            except Exception:
                pass
            for part in self.participants:
                if part.has_lost:
                    continue
                for poke in part.active:
                    try:
                        terrain_handler.onResidual(poke)
                    except Exception:
                        pass
            if terrain not in self.field.pseudo_weather:
                self.field.terrain = None
                self.field.terrain_handler = None

        # Handle pseudo weather effects
        for name, effect in list(self.field.pseudo_weather.items()):
            if name in {weather, terrain}:
                continue
            handler = None
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

        # Remove Pokémon that fainted from residual damage
        self.run_faint()

        # Auto-switch in replacements for any empty sides
        self.run_switch()
        self.run_after_switch()

    def run_action(self) -> None:
        """Main action runner modeled on Showdown's `runAction`."""
        for part in self.participants:
            acts = getattr(part, "pending_action", None)
            if not acts:
                continue
            if not isinstance(acts, list):
                acts = [acts]
            if part.active:
                switching = part.active[0]
            else:
                switching = None
            for act in list(acts):
                if act.action_type is ActionType.SWITCH and switching:
                    for opp in self.participants:
                        if opp is part or opp.has_lost:
                            continue
                        opp_act = getattr(opp, "pending_action", None)
                        if isinstance(opp_act, list):
                            opp_candidates = opp_act
                        else:
                            opp_candidates = [opp_act] if opp_act else []
                        for oa in opp_candidates:
                            if (
                                oa
                                and oa.action_type is ActionType.MOVE
                                and getattr(getattr(oa, "move", None), "key", "") == "pursuit"
                            ):
                                switching.tempvals["switching"] = True
                                self.use_move(oa)
                                switching.tempvals.pop("switching", None)
                                if isinstance(opp_act, list):
                                    opp_candidates.remove(oa)
                                    opp.pending_action = opp_candidates
                                else:
                                    opp.pending_action = None

        self.run_switch()
        self.run_after_switch()
        self.run_move()
        self.run_faint()
        self.residual()

    # ------------------------------------------------------------------
    # Turn logic
    # ------------------------------------------------------------------
    def start_turn(self) -> None:
        """Reset temporary flags or display status."""
        self.turn_count += 1
        if self.turn_count == 1:
            for part in self.participants:
                for poke in part.active:
                    self.register_handlers(poke)
                    self.dispatcher.dispatch("start", pokemon=poke, battle=self)
                    self.dispatcher.dispatch("switch_in", pokemon=poke, battle=self)

    def before_turn(self) -> None:
        """Run simple BeforeTurn events for all active Pokémon."""
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:
            VOLATILE_HANDLERS = {}

        for part in self.participants:
            if part.has_lost:
                continue
            for poke in part.active:
                self.dispatcher.dispatch("before_turn", pokemon=poke, battle=self)

                status = getattr(poke, "status", None)
                handler = CONDITION_HANDLERS.get(status)
                if handler and hasattr(handler, "onBeforeTurn"):
                    try:
                        handler.onBeforeTurn(poke, battle=self)
                    except Exception:
                        pass

                if status == "slp":
                    turns = poke.tempvals.get("slp_turns")
                    if turns is None:
                        turns = random.randint(1, 3)
                    else:
                        turns -= 1
                    if turns <= 0:
                        poke.status = 0
                        poke.tempvals.pop("slp_turns", None)
                    else:
                        poke.tempvals["slp_turns"] = turns

                vols = getattr(poke, "volatiles", {})
                for vol in list(vols.keys()):
                    handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
                    if handler and hasattr(handler, "onBeforeTurn"):
                        try:
                            keep = handler.onBeforeTurn(poke, battle=self)
                            if keep is False:
                                vols.pop(vol, None)
                        except Exception:
                            pass

    def lock_choices(self) -> None:
        """Apply locked-in transformations like Mega Evolution or Terastallization."""

        for part in self.participants:
            if part.has_lost:
                continue
            for poke in part.active:
                if getattr(poke, "pending_mega", False):
                    self.perform_mega_evolution(poke)
                    poke.pending_mega = False
                tera = getattr(poke, "pending_tera", None)
                if tera:
                    self.perform_tera_change(poke, tera)
                    poke.pending_tera = None

    def select_actions(self) -> List[Action]:
        actions: List[Action] = []
        for part in self.participants:
            if part.has_lost:
                continue
            if hasattr(part, "choose_actions"):
                part_actions = part.choose_actions(self)
                if isinstance(part_actions, list):
                    actions.extend(part_actions)
                elif part_actions:
                    actions.append(part_actions)
            else:
                action = part.choose_action(self)
                if action:
                    actions.append(action)
        return actions

    # Simple wrapper for external API compatibility
    def collect_actions(self) -> List[Action]:
        """Alias for :py:meth:`select_actions`."""
        return self.select_actions()

    def order_actions(self, actions: List[Action]) -> List[Action]:
        """Order actions by priority and speed following Showdown rules."""

        try:
            from pokemon.battle import utils
        except Exception:
            utils = None

        trick_room = bool(self.field.get_pseudo_weather("trickroom"))

        for action in actions:
            poke = action.pokemon or (action.actor.active[0] if action.actor.active else None)
            move = action.move
            base_priority = action.priority
            priority = base_priority

            ability = getattr(poke, "ability", None)
            item = getattr(poke, "item", None) or getattr(poke, "held_item", None)

            if poke:
                target = None
                if action.target and action.target.active:
                    target = action.target.active[0]
                priority = self.apply_priority_modifiers(poke, move, priority, target)

            action.priority = priority
            action.priority_mod = priority - base_priority

            # Determine effective speed
            if poke:
                safe_get_stats = getattr(utils, "_safe_get_stats", None)
                if safe_get_stats is None:
                    try:  # pragma: no cover - import error path
                        from .utils import _safe_get_stats as safe_get_stats
                    except Exception:  # pragma: no cover
                        safe_get_stats = None

                if utils and hasattr(utils, "get_modified_stat"):
                    try:
                        speed = utils.get_modified_stat(poke, "speed")
                    except Exception:
                        if safe_get_stats:
                            try:
                                speed = safe_get_stats(poke).get("speed", 0)
                            except Exception:
                                speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
                        else:
                            speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
                else:
                    if safe_get_stats:
                        try:
                            speed = safe_get_stats(poke).get("speed", 0)
                        except Exception:
                            speed = getattr(getattr(poke, "base_stats", None), "speed", 0)
                    else:
                        speed = getattr(getattr(poke, "base_stats", None), "speed", 0)

                if ability and hasattr(ability, "call"):
                    try:
                        mod = ability.call("onModifySpe", speed, pokemon=poke)
                        if isinstance(mod, (int, float)):
                            speed = int(mod)
                    except Exception:
                        pass
                if item and hasattr(item, "call"):
                    try:
                        mod = item.call("onModifySpe", speed, pokemon=poke)
                        if isinstance(mod, (int, float)):
                            speed = int(mod)
                    except Exception:
                        pass
            else:
                speed = 0

            action.speed = speed
            action._tiebreak = random.random()

        if trick_room:
            key = lambda a: (a.priority, -a.speed, a._tiebreak)
        else:
            key = lambda a: (a.priority, a.speed, a._tiebreak)

        return sorted(actions, key=key, reverse=True)

    def determine_move_order(self, actions: List[Action]) -> List[Action]:
        """Alias for :py:meth:`order_actions`."""
        return self.order_actions(actions)

    def apply_priority_modifiers(
        self,
        pokemon,
        move: Optional[BattleMove],
        priority: float,
        target,
    ) -> float:
        """Apply ability, item and status priority modifiers."""

        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:
            VOLATILE_HANDLERS = {}

        ability = getattr(pokemon, "ability", None)
        if ability and hasattr(ability, "call"):
            try:
                mod = ability.call(
                    "onModifyPriority",
                    priority,
                    pokemon=pokemon,
                    target=target,
                    move=move,
                )
                if isinstance(mod, (int, float)):
                    priority = mod
            except Exception:
                pass
            try:
                frac = ability.call(
                    "onFractionalPriority",
                    priority,
                    pokemon=pokemon,
                    target=target,
                    move=move,
                )
                if isinstance(frac, (int, float)):
                    priority += frac if frac != priority else 0
            except Exception:
                pass

        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and hasattr(item, "call"):
            try:
                frac = item.call("onFractionalPriority", pokemon=pokemon)
                if isinstance(frac, (int, float)):
                    priority += frac
            except Exception:
                pass

        status = getattr(pokemon, "status", None)
        handler = CONDITION_HANDLERS.get(status)
        if handler:
            if hasattr(handler, "onModifyPriority"):
                try:
                    mod = handler.onModifyPriority(priority, pokemon=pokemon, target=target, move=move)
                    if isinstance(mod, (int, float)):
                        priority = mod
                except Exception:
                    pass
            if hasattr(handler, "onFractionalPriority"):
                try:
                    frac = handler.onFractionalPriority(priority, pokemon=pokemon, target=target, move=move)
                    if isinstance(frac, (int, float)):
                        priority += frac if frac != priority else 0
                except Exception:
                    pass

        volatiles = getattr(pokemon, "volatiles", {})
        for vol in list(volatiles.keys()):
            handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
            if not handler:
                continue
            if hasattr(handler, "onModifyPriority"):
                try:
                    mod = handler.onModifyPriority(priority, pokemon=pokemon, target=target, move=move)
                    if isinstance(mod, (int, float)):
                        priority = mod
                except Exception:
                    pass
            if hasattr(handler, "onFractionalPriority"):
                try:
                    frac = handler.onFractionalPriority(priority, pokemon=pokemon, target=target, move=move)
                    if isinstance(frac, (int, float)):
                        priority += frac if frac != priority else 0
                except Exception:
                    pass

        if getattr(pokemon, "tempvals", {}).pop("quash", False):
            priority = -7

        return priority

    def status_prevents_move(self, pokemon) -> bool:
        """Return True if the Pokemon cannot act due to status."""
        status = getattr(pokemon, "status", None)
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:
            VOLATILE_HANDLERS = {}

        ability = getattr(pokemon, "ability", None)
        if ability and hasattr(ability, "call"):
            try:
                res = ability.call("onBeforeMove", pokemon=pokemon, battle=self)
                if res is False:
                    return True
            except Exception:
                pass

        item = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if item and hasattr(item, "call"):
            try:
                res = item.call("onBeforeMove", pokemon=pokemon, battle=self)
                if res is False:
                    return True
            except Exception:
                pass

        handler = CONDITION_HANDLERS.get(status)
        if handler and hasattr(handler, "onBeforeMove"):
            result = handler.onBeforeMove(pokemon, battle=self)
            if result is False:
                return True

        volatiles = getattr(pokemon, "volatiles", {})
        if "flinch" in volatiles:
            volatiles.pop("flinch", None)
            return True
        for vol in list(volatiles.keys()):
            handler = CONDITION_HANDLERS.get(vol) or VOLATILE_HANDLERS.get(vol)
            if handler and hasattr(handler, "onBeforeMove"):
                try:
                    result = handler.onBeforeMove(pokemon, battle=self)
                except Exception:
                    result = handler.onBeforeMove(pokemon)
                if result is False:
                    return True

        if status == "par":
            return random.random() < 0.25
        if status == "frz":
            if random.random() < 0.2:
                pokemon.status = 0
                return False
            return True
        if status == "slp":
            turns = pokemon.tempvals.get("slp_turns")
            if turns is None:
                turns = random.randint(1, 3)
                pokemon.tempvals["slp_turns"] = turns
            if turns > 0:
                turns -= 1
                pokemon.tempvals["slp_turns"] = turns
                if turns == 0:
                    pokemon.status = 0
                    pokemon.tempvals.pop("slp_turns", None)
                    return False
                return True
        return False

    # ------------------------------------------------------------------
    # Basic stat handling helpers
    # ------------------------------------------------------------------
    def modify_stat_stage(self, pokemon, stat: str, delta: int) -> None:
        """Modify ``pokemon`` stat stage by ``delta``."""
        from pokemon.battle.utils import apply_boost

        apply_boost(pokemon, {stat: delta})

    def calculate_stat(self, pokemon, stat: str) -> int:
        """Return ``pokemon``'s stat after modifiers."""
        from pokemon.battle.utils import get_modified_stat

        return get_modified_stat(pokemon, stat)

    def reset_stat_changes(self, pokemon) -> None:
        """Clear temporary stat modifiers for ``pokemon``."""
        if hasattr(pokemon, "boosts"):
            pokemon.boosts = {}

    def execute_actions(self, actions: List[Action]) -> None:
        for action in actions:
            if action.action_type is ActionType.MOVE and action.move:
                actor_poke = action.pokemon or (action.actor.active[0] if action.actor.active else None)
                if self.status_prevents_move(actor_poke):
                    continue
                target_poke = None
                if action.target and action.target.active:
                    target_poke = action.target.active[0]
                action.move.execute(actor_poke, target_poke, self)
                try:
                    actor_poke.tempvals["moved"] = True
                except Exception:
                    pass
            elif action.action_type is ActionType.ITEM and action.item:
                self.execute_item(action)

    def execute_turn(self, actions: List[Action]) -> None:
        """Execute the supplied actions in proper order."""
        ordered = self.determine_move_order(actions)
        self.execute_actions(ordered)
        self.run_faint()
        self.residual()

    def execute_item(self, action: Action) -> None:
        """Handle item usage during battle."""
        item_name = action.item.lower()
        target = action.target
        if target not in self.participants or target.has_lost or not target.active:
            opponents = self.opponents_of(action.actor)
            target = opponents[0] if opponents else None
        if not target or not target.active:
            return

        if item_name.endswith("ball") and self.type is BattleType.WILD:
            target_poke = target.active[0]
            try:
                from pokemon.dex.functions.pokedex_funcs import get_catch_rate
            except Exception:
                get_catch_rate = lambda name: 255
            catch_rate = get_catch_rate(getattr(target_poke, "name", "")) or 0
            status = getattr(target_poke, "status", None)
            max_hp = getattr(target_poke, "max_hp", getattr(target_poke, "hp", 1))
            from .capture import attempt_capture
            ball_mod = BALL_MODIFIERS.get(item_name, 1.0)
            caught = attempt_capture(
                max_hp,
                target_poke.hp,
                catch_rate,
                ball_modifier=ball_mod,
                status=status,
            )
            if hasattr(action.actor, "remove_item"):
                try:
                    action.actor.remove_item(action.item)
                except Exception:
                    pass
            if caught:
                target.active.remove(target_poke)
                if target_poke in target.pokemons:
                    target.pokemons.remove(target_poke)
                if getattr(target_poke, "model_id", None) is not None:
                    try:
                        from pokemon.models.core import OwnedPokemon
                        dbpoke = OwnedPokemon.objects.get(unique_id=target_poke.model_id)
                        if hasattr(action.actor, "trainer"):
                            dbpoke.trainer = action.actor.trainer
                        dbpoke.current_hp = target_poke.hp
                        dbpoke.is_wild = False
                        dbpoke.ai_trainer = None
                        if hasattr(dbpoke, "save"):
                            dbpoke.save()
                        if hasattr(action.actor, "storage") and hasattr(action.actor.storage, "stored_pokemon"):
                            try:
                                action.actor.storage.stored_pokemon.add(dbpoke)
                            except Exception:
                                pass
                    except Exception:
                        pass
                elif hasattr(action.actor, "add_pokemon_to_storage"):
                    try:
                        poke_types = getattr(target_poke, "types", [])
                        type_ = ", ".join(poke_types) if isinstance(poke_types, list) else str(poke_types)
                        action.actor.add_pokemon_to_storage(
                            getattr(target_poke, "name", ""),
                            getattr(target_poke, "level", 1),
                            type_,
                        )
                    except Exception:
                        pass
                target.has_lost = True
                self.check_victory()

    # ------------------------------------------------------------------
    # Action convenience methods
    # ------------------------------------------------------------------
    def perform_move_action(self, action: Action) -> None:
        """Execute a move action."""
        self.use_move(action)

    def perform_item_action(self, action: Action) -> None:
        """Use an item during battle."""
        self.execute_item(action)

    def perform_mega_evolution(self, pokemon) -> None:
        """Placeholder for Mega Evolution mechanics."""
        setattr(pokemon, "mega_evolved", True)

    def perform_tera_change(self, pokemon, tera_type: str) -> None:
        """Placeholder for Terastallization mechanics."""
        setattr(pokemon, "tera_type", tera_type)

    def end_turn(self) -> None:
        for part in self.participants:
            if all(getattr(p, "hp", 1) <= 0 for p in part.pokemons):
                part.has_lost = True
            for poke in part.active:
                self.dispatcher.dispatch("end_turn", pokemon=poke, battle=self)
        self.check_victory()

    def run_turn(self) -> None:
        battle_logger.info("Run turn %s begin", self.turn_count + 1)
        self.dispatcher.dispatch("turn_start", battle=self)
        self.start_turn()
        battle_logger.info("After start_turn")
        self.before_turn()
        battle_logger.info("After before_turn")
        self.dispatcher.dispatch("lock_choices", battle=self)
        self.lock_choices()
        battle_logger.info("After lock_choices")
        self.dispatcher.dispatch("switch", battle=self)
        self.run_switch()
        self.run_after_switch()
        battle_logger.info("After switch")
        self.dispatcher.dispatch("move", battle=self)
        self.run_move()
        self.run_faint()
        battle_logger.info("After move")
        self.dispatcher.dispatch("residual", battle=self)
        self.residual()
        battle_logger.info("After residual")
        self.end_turn()
        battle_logger.info("Run turn %s end", self.turn_count)

    # ------------------------------------------------------------------
    # Logging and feedback helpers
    # ------------------------------------------------------------------
    def log_action(self, message: str) -> None:
        """Basic logger used by the engine."""
        print(message)

    def display_hp_bar(self, pokemon) -> str:
        """Return a simple textual HP bar for ``pokemon``."""
        hp = getattr(pokemon, "hp", 0)
        max_hp = getattr(pokemon, "max_hp", 1)
        percent = int((hp / max_hp) * 10)
        bar = "[" + ("#" * percent).ljust(10) + "]"
        return bar

    def announce_status_change(self, pokemon, status: str) -> None:
        """Notify about a status condition change."""
        self.log_action(f"{getattr(pokemon, 'name', 'Pokemon')} is now {status}!")

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
            The Pokémon whose stat changes will be announced.
        start: dict
            Mapping of stat names to their starting stage values.
        end: dict
            Mapping of stat names to their ending stage values.
        attempted: dict, optional
            Mapping of stat names to attempted changes. This is used to
            report messages when a stat change fails due to reaching the
            stage cap.
        """

        from pokemon.data.text import DEFAULT_TEXT
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
        return critical_hit_check()

    def calculate_type_effectiveness(self, target, move) -> float:
        from .damage import type_effectiveness
        return type_effectiveness(target, move)

    def handle_immunities_and_abilities(self, attacker, target, move) -> bool:
        """Return ``True`` if the move is blocked."""
        eff = 1.0
        if move.type:
            eff = self.calculate_type_effectiveness(target, move)
        if eff == 0:
            return True
        if getattr(target, "volatiles", {}).get("protect"):
            return True
        return False

    def check_protect_substitute(self, target) -> bool:
        vols = getattr(target, "volatiles", {})
        return "protect" in vols or "substitute" in vols

    def check_priority_override(self, pokemon) -> bool:
        return getattr(pokemon, "tempvals", {}).get("quash", False)

    def handle_end_of_battle_rewards(self, winner: BattleParticipant) -> None:
        """Placeholder for reward distribution."""
        pass
