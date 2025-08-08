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

try:
    from .events import EventDispatcher
except Exception:  # pragma: no cover - fallback for tests with stubs
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

battle_logger = logging.getLogger("battle")
try:
    from pokemon.dex.items.ball_modifiers import BALL_MODIFIERS
except Exception:
    BALL_MODIFIERS = {}

try:
    from pokemon.dex.functions import moves_funcs, conditions_funcs
except Exception:
    moves_funcs = None
    conditions_funcs = None


def _normalize_key(name: str) -> str:
    """Normalize move names for lookup in ``MOVEDEX``."""

    return name.replace(" ", "").replace("-", "").replace("'", "").lower()


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


class ActionType(Enum):
    """Possible actions a participant may take in a turn."""

    MOVE = auto()
    SWITCH = auto()
    ITEM = auto()
    RUN = auto()


@dataclass
class BattleMove:
    """Representation of a move used in battle."""

    name: str
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

    def execute(self, user, target, battle: "Battle") -> None:
        """Execute this move's effect."""
        if self.onTry:
            self.onTry(user, target, self, battle)
        if self.onHit:
            self.onHit(user, target, battle)
            return

        # Default behaviour for moves without custom handlers
        from .damage import apply_damage
        from pokemon.dex.entities import Move

        raw = dict(self.raw)
        if self.basePowerCallback:
            raw["basePowerCallback"] = self.basePowerCallback
        move = Move(
            name=self.name,
            num=0,
            type=self.type,
            category="Physical",
            power=self.power,
            accuracy=self.accuracy,
            pp=None,
            raw=raw,
        )

        if self.basePowerCallback:
            try:
                move.basePowerCallback = self.basePowerCallback
                # allow callback to setup move data before damage calculation
                self.basePowerCallback(user, target, move)
            except Exception:
                move.basePowerCallback = None

        apply_damage(user, target, move, battle=battle)

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

        # Apply volatile status effects set by this move
        volatile = self.raw.get("volatileStatus") if self.raw else None
        if volatile:
            effect = self.raw.get("condition", {})
            cb = effect.get("onStart")
            if isinstance(cb, str) and moves_funcs:
                try:
                    cls_name, func_name = cb.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        cb = getattr(cls(), func_name, None)
                except Exception:
                    cb = None
            if callable(cb):
                try:
                    cb(user, target)
                except Exception:
                    cb(target)
            affected = user if self.raw.get("target") == "self" else target
            if affected and hasattr(affected, "volatiles"):
                affected.volatiles.setdefault(volatile, True)



@dataclass
class Action:
    """Container describing a chosen action for the turn."""

    actor: "BattleParticipant"
    action_type: ActionType
    target: Optional["BattleParticipant"] = None
    move: Optional[BattleMove] = None
    item: Optional[str] = None
    priority: int = 0
    priority_mod: float = 0.0
    speed: int = 0
    pokemon: Optional[Any] = None


class BattleParticipant:
    """Represents one side of a battle.

    Parameters
    ----------
    name:
        Display name for this participant.
    pokemons:
        List of Pokémon available to this participant.
    is_ai:
        If ``True`` this participant is controlled by the AI.
    player:
        Optional Evennia object representing the controlling player.
    max_active:
        Maximum number of simultaneously active Pokémon.
    team:
        Optional team identifier.  Participants with the same team are treated
        as allies and should not be targeted by automatic opponent selection.
    """

    def __init__(
        self,
        name: str,
        pokemons: List,
        is_ai: bool = False,
        player=None,
        max_active: int = 1,
        team: str | None = None,
    ):
        self.name = name
        self.pokemons = pokemons
        self.active: List = []
        self.is_ai = is_ai
        self.has_lost = False
        self.pending_action: Optional[Action] = None
        self.side = BattleSide()
        self.player = player
        self.max_active = max_active
        # Team is optional; if ``None`` participants are assumed to be enemies
        # of everyone else.  When provided, participants sharing the same team
        # value are considered allies.
        self.team = team
        for poke in self.pokemons:
            if poke is not None:
                setattr(poke, "side", self.side)

    def choose_action(self, battle: "Battle") -> Optional[Action]:
        """Return an Action object for this turn.

        For AI-controlled participants the action is chosen automatically.  For
        non-AI participants this method returns the ``pending_action`` that was
        queued externally.
        """
        if self.pending_action:
            action = self.pending_action
            self.pending_action = None
            # Validate the target against remaining opponents
            if action.target and action.target not in battle.participants:
                action.target = None
            if not action.target:
                opponents = battle.opponents_of(self)
                if opponents:
                    action.target = opponents[0]
            return action

        if not self.is_ai:
            return None

        if not self.active:
            return None
        active_poke = self.active[0]
        moves = getattr(active_poke, "moves", [])
        if not moves:
            move_data = Move(name="Flail")
        else:
            move_data = moves[0]

        move_entry = MOVEDEX.get(_normalize_key(move_data.name))
        on_hit_func = None
        on_try_func = None
        on_before_move_func = None
        on_after_move_func = None
        base_power_cb = None
        if move_entry:
            on_hit = move_entry.raw.get("onHit")
            if isinstance(on_hit, str):
                try:
                    cls_name, func_name = on_hit.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        inst = cls()
                        candidate = getattr(inst, func_name, None)
                        if callable(candidate):
                            on_hit_func = candidate
                except Exception:
                    on_hit_func = None

            on_try = move_entry.raw.get("onTry")
            if isinstance(on_try, str):
                try:
                    cls_name, func_name = on_try.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        inst = cls()
                        cand = getattr(inst, func_name, None)
                        if callable(cand):
                            on_try_func = cand
                except Exception:
                    on_try_func = None
            before_cb = move_entry.raw.get("onBeforeMove")
            if isinstance(before_cb, str):
                try:
                    cls_name, func_name = before_cb.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        inst = cls()
                        cand = getattr(inst, func_name, None)
                        if callable(cand):
                            on_before_move_func = cand
                except Exception:
                    on_before_move_func = None
            after_cb = move_entry.raw.get("onAfterMove")
            if isinstance(after_cb, str):
                try:
                    cls_name, func_name = after_cb.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        inst = cls()
                        cand = getattr(inst, func_name, None)
                        if callable(cand):
                            on_after_move_func = cand
                except Exception:
                    on_after_move_func = None
            base_cb = move_entry.raw.get("basePowerCallback")
            if isinstance(base_cb, str):
                try:
                    cls_name, func_name = base_cb.split(".", 1)
                    cls = getattr(moves_funcs, cls_name, None)
                    if cls:
                        inst = cls()
                        cand = getattr(inst, func_name, None)
                        if callable(cand):
                            base_power_cb = cand
                except Exception:
                    base_power_cb = None
                    
            move = BattleMove(
                name=move_entry.name,
                power=getattr(move_entry, "power", 0),
                accuracy=getattr(move_entry, "accuracy", 100),
                priority=move_entry.raw.get("priority", 0),
                onHit=on_hit_func,
                onTry=on_try_func,
                onBeforeMove=on_before_move_func,
                onAfterMove=on_after_move_func,
                basePowerCallback=base_power_cb,
                type=getattr(move_entry, "type", None),
                raw=move_entry.raw,
            )
        else:
            move = BattleMove(name=move_data.name, priority=getattr(move_data, "priority", 0))
        opponents = battle.opponents_of(self)
        if not opponents:
            return None
        opponent = random.choice(opponents)
        if not opponent.active:
            return None
        target = opponent
        priority = getattr(move, "priority", 0)
        battle_logger.info("%s chooses %s", self.name, move.name)
        return Action(self, ActionType.MOVE, target, move, priority, pokemon=active_poke)

    def choose_actions(self, battle: "Battle") -> List[Action]:
        """Return a list of actions for all active Pokémon."""
        if self.pending_action:
            action = self.pending_action
            self.pending_action = None
            if isinstance(action, list):
                for act in action:
                    if act.target and act.target not in battle.participants:
                        act.target = None
                    if not act.target:
                        opps = battle.opponents_of(self)
                        if opps:
                            act.target = opps[0]
                return action
            if action.target and action.target not in battle.participants:
                action.target = None
            if not action.target:
                opps = battle.opponents_of(self)
                if opps:
                    action.target = opps[0]
            return [action]

        if not self.is_ai:
            return []

        actions: List[Action] = []
        for active_poke in self.active:
            moves = getattr(active_poke, "moves", [])
            move_data = moves[0] if moves else Move(name="Flail")
            move_entry = MOVEDEX.get(_normalize_key(move_data.name))
            on_hit_func = None
            on_try_func = None
            on_before_move_func = None
            on_after_move_func = None
            base_power_cb = None
            if move_entry:
                on_hit = move_entry.raw.get("onHit")
                if isinstance(on_hit, str):
                    try:
                        cls_name, func_name = on_hit.split(".", 1)
                        cls = getattr(moves_funcs, cls_name, None)
                        if cls:
                            inst = cls()
                            candidate = getattr(inst, func_name, None)
                            if callable(candidate):
                                on_hit_func = candidate
                    except Exception:
                        on_hit_func = None

                on_try = move_entry.raw.get("onTry")
                if isinstance(on_try, str):
                    try:
                        cls_name, func_name = on_try.split(".", 1)
                        cls = getattr(moves_funcs, cls_name, None)
                        if cls:
                            inst = cls()
                            cand = getattr(inst, func_name, None)
                        if callable(cand):
                            on_try_func = cand
                    except Exception:
                        on_try_func = None
                before_cb = move_entry.raw.get("onBeforeMove")
                if isinstance(before_cb, str):
                    try:
                        cls_name, func_name = before_cb.split(".", 1)
                        cls = getattr(moves_funcs, cls_name, None)
                        if cls:
                            inst = cls()
                            cand = getattr(inst, func_name, None)
                            if callable(cand):
                                on_before_move_func = cand
                    except Exception:
                        on_before_move_func = None
                after_cb = move_entry.raw.get("onAfterMove")
                if isinstance(after_cb, str):
                    try:
                        cls_name, func_name = after_cb.split(".", 1)
                        cls = getattr(moves_funcs, cls_name, None)
                        if cls:
                            inst = cls()
                            cand = getattr(inst, func_name, None)
                            if callable(cand):
                                on_after_move_func = cand
                    except Exception:
                        on_after_move_func = None
                base_cb = move_entry.raw.get("basePowerCallback")
                if isinstance(base_cb, str):
                    try:
                        cls_name, func_name = base_cb.split(".", 1)
                        cls = getattr(moves_funcs, cls_name, None)
                        if cls:
                            inst = cls()
                            cand = getattr(inst, func_name, None)
                            if callable(cand):
                                base_power_cb = cand
                    except Exception:
                        base_power_cb = None

                move = BattleMove(
                    name=move_entry.name,
                    power=getattr(move_entry, "power", 0),
                    accuracy=getattr(move_entry, "accuracy", 100),
                    priority=move_entry.raw.get("priority", 0),
                    onHit=on_hit_func,
                    onTry=on_try_func,
                    onBeforeMove=on_before_move_func,
                    onAfterMove=on_after_move_func,
                    basePowerCallback=base_power_cb,
                    type=getattr(move_entry, "type", None),
                    raw=move_entry.raw,
                )
            else:
                move = BattleMove(name=move_data.name, priority=getattr(move_data, "priority", 0))
            opponents = battle.opponents_of(self)
            if not opponents:
                continue
            opponent = random.choice(opponents)
            if not opponent.active:
                continue
            target = opponent
            priority = getattr(move, "priority", 0)
            battle_logger.info("%s chooses %s", self.name, move.name)
            actions.append(Action(self, ActionType.MOVE, target, move, priority, pokemon=active_poke))
        return actions


class Battle:
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

    def add_side_condition(
        self,
        participant: BattleParticipant,
        name: str,
        effect: Dict,
        source=None,
        *,
        moves_funcs=None,
    ) -> None:
        """Apply a side condition to ``participant``."""

        moves_funcs = moves_funcs or {}
        side = participant.side
        current = side.conditions.get(name)
        if current is None:
            side.conditions[name] = effect.copy()
            cb = effect.get("onSideStart")
        else:
            cb = effect.get("onSideRestart")
        if isinstance(cb, str) and moves_funcs:
            try:
                cls_name, func_name = cb.split(".", 1)
                cls = getattr(moves_funcs, cls_name, None)
                if cls:
                    cb = getattr(cls(), func_name, None)
            except Exception:
                cb = None
        if callable(cb):
            try:
                cb(side, source)
            except Exception:
                try:
                    cb(side)
                except Exception:
                    cb()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
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

    def check_victory(self) -> Optional[BattleParticipant]:
        remaining = [p for p in self.participants if not p.has_lost]
        if len(remaining) <= 1:
            self.battle_over = True
            self.restore_transforms()
            return remaining[0] if remaining else None
        return None

    # ------------------------------
    # Field condition helpers
    # ------------------------------
    def _lookup_effect(self, name: str):
        if not moves_funcs and not conditions_funcs:
            return None

        key = name.replace(" ", "").replace("-", "").lower()
        cls_name = key.capitalize()
        handler = getattr(conditions_funcs, cls_name, None)
        if handler is None:
            handler = getattr(moves_funcs, cls_name, None)
        if handler:
            try:
                return handler()
            except Exception:
                return handler
        return None

    def setWeather(self, name: str, source=None) -> bool:
        """Start a weather effect on the field."""
        handler = self._lookup_effect(name)
        if not handler:
            return False
        effect = {}
        dur_cb = getattr(handler, "durationCallback", None)
        if callable(dur_cb):
            try:
                effect["duration"] = dur_cb(source=source)
            except Exception:
                try:
                    effect["duration"] = dur_cb(source)
                except Exception:
                    effect["duration"] = dur_cb()
        self.field.add_pseudo_weather(name, effect)
        if hasattr(handler, "onFieldStart"):
            try:
                handler.onFieldStart(self.field, source=source)
            except Exception:
                handler.onFieldStart(self.field)
        self.field.weather = name
        self.field.weather_handler = handler
        return True

    def clearWeather(self) -> None:
        name = getattr(self.field, "weather", None)
        handler = getattr(self.field, "weather_handler", None)
        if name and handler and hasattr(handler, "onFieldEnd"):
            try:
                handler.onFieldEnd(self.field)
            except Exception:
                pass
        if name:
            self.field.pseudo_weather.pop(name, None)
        self.field.weather = None
        self.field.weather_state = {}
        self.field.weather_handler = None

    def setTerrain(self, name: str, source=None) -> bool:
        """Start a terrain effect on the field."""
        handler = self._lookup_effect(name)
        if not handler:
            return False
        effect = {}
        dur_cb = getattr(handler, "durationCallback", None)
        if callable(dur_cb):
            try:
                effect["duration"] = dur_cb(source=source)
            except Exception:
                try:
                    effect["duration"] = dur_cb(source)
                except Exception:
                    effect["duration"] = dur_cb()
        self.field.add_pseudo_weather(name, effect)
        if hasattr(handler, "onFieldStart"):
            try:
                handler.onFieldStart(self.field, source=source)
            except Exception:
                handler.onFieldStart(self.field)
        self.field.terrain = name
        self.field.terrain_handler = handler
        return True

    def clearTerrain(self) -> None:
        name = getattr(self.field, "terrain", None)
        handler = getattr(self.field, "terrain_handler", None)
        if name and handler and hasattr(handler, "onFieldEnd"):
            try:
                handler.onFieldEnd(self.field)
            except Exception:
                pass
        if name:
            self.field.pseudo_weather.pop(name, None)
        self.field.terrain = None
        self.field.terrain_state = {}
        self.field.terrain_handler = None

    def apply_entry_hazards(self, pokemon) -> None:
        """Apply entry hazard effects to ``pokemon`` if present."""
        side = getattr(pokemon, "side", None)
        if not side:
            return

        name_map = {
            "rocks": "stealthrock",
            "spikes": "spikes",
            "toxicspikes": "toxicspikes",
            "stickyweb": "stickyweb",
            "steelsurge": "gmaxsteelsurge",
        }

        for name, active in list(side.hazards.items()):
            if not active:
                continue
            effect = name_map.get(name, name)
            handler = None
            if moves_funcs:
                handler = getattr(moves_funcs, effect.capitalize(), None)
                if handler:
                    try:
                        handler = handler()
                    except Exception:
                        pass
            if not handler:
                continue
            cb = getattr(handler, "onEntryHazard", None)
            if callable(cb):
                try:
                    cb(pokemon=pokemon)
                except Exception:
                    try:
                        cb(pokemon)
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Generic battle condition helpers
    # ------------------------------------------------------------------
    def apply_status_condition(self, pokemon, condition: str) -> None:
        """Inflict a major status condition on ``pokemon``."""
        pokemon.status = condition
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        handler = CONDITION_HANDLERS.get(condition)
        if handler and hasattr(handler, "onStart"):
            try:
                handler.onStart(pokemon, battle=self)
            except Exception:
                handler.onStart(pokemon)

    def apply_volatile_status(self, pokemon, condition: str) -> None:
        """Apply a volatile status to ``pokemon``."""
        if not hasattr(pokemon, "volatiles"):
            pokemon.volatiles = {}
        pokemon.volatiles[condition] = True
        try:
            from pokemon.dex.functions.moves_funcs import VOLATILE_HANDLERS
        except Exception:
            VOLATILE_HANDLERS = {}
        handler = VOLATILE_HANDLERS.get(condition)
        if handler and hasattr(handler, "onStart"):
            try:
                handler.onStart(pokemon, battle=self)
            except Exception:
                handler.onStart(pokemon)

    def handle_weather(self) -> None:
        """Apply residual effects of the current weather."""
        weather_handler = getattr(self.field, "weather_handler", None)
        if weather_handler and hasattr(weather_handler, "onFieldResidual"):
            try:
                weather_handler.onFieldResidual(self.field)
            except Exception:
                pass

    def handle_terrain(self) -> None:
        """Apply residual effects of the active terrain."""
        terrain_handler = getattr(self.field, "terrain_handler", None)
        if terrain_handler and hasattr(terrain_handler, "onFieldResidual"):
            try:
                terrain_handler.onFieldResidual(self.field)
            except Exception:
                pass

    def update_hazards(self) -> None:
        """Update hazard effects on the field."""
        for part in self.participants:
            for poke in part.active:
                self.apply_entry_hazards(poke)

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
                    module = __import__(
                        f"pokemon.dex.functions.{mod_name.lower()}", fromlist=[mod_name]
                    )
                    cls = getattr(module, mod_name, None)
                    cb = getattr(cls(), func_name) if cls else None
                except Exception:
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

            self.dispatcher.register(event, handler())

            self.dispatcher.register(event, handler)

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
                        if act and act.action_type is ActionType.MOVE and act.move and act.move.name.lower() == "pursuit":
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
                        from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
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
        if move.pp is not None:
            if move.pp > 0:
                move.pp -= 1
            return

        slots = getattr(pokemon, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:  # pragma: no cover - fallback for stubs
                slot_iter = slots
            for slot in slot_iter:
                if getattr(getattr(slot, "move", None), "name", None) == move.name:
                    if getattr(slot, "current_pp", None) and slot.current_pp > 0:
                        slot.current_pp -= 1
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
                break

    def _deal_damage(self, user, target, move: BattleMove, *, spread: bool = False) -> int:
        """Apply simplified damage calculation to ``target``."""
        from .damage import apply_damage
        from pokemon.dex.entities import Move

        raw = dict(move.raw)
        if move.basePowerCallback:
            raw["basePowerCallback"] = move.basePowerCallback
        temp_move = Move(
            name=move.name,
            num=0,
            type=move.type,
            category="Physical",
            power=move.power,
            accuracy=move.accuracy,
            pp=None,
            raw=raw,
        )
        if move.basePowerCallback:
            try:
                temp_move.basePowerCallback = move.basePowerCallback
                move.basePowerCallback(user, target, temp_move)
            except Exception:
                temp_move.basePowerCallback = None

        result = apply_damage(user, target, temp_move, battle=self, spread=spread)
        return sum(result.debug.get("damage", []))

    def _do_move(self, user, target, move: BattleMove) -> bool:
        """Execute ``move`` handling two-turn charge phases."""

        cb_name = move.raw.get("onTryMove") if move.raw else None
        if cb_name:
            if isinstance(cb_name, str) and moves_funcs:
                cls_name, func_name = cb_name.split(".", 1)
                cls = getattr(moves_funcs, cls_name, None)
                cb = getattr(cls(), func_name, None) if cls else None
            else:
                cb = cb_name
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
        dex_move = MOVEDEX.get(_normalize_key(action.move.name))
        if dex_move:
            if not action.move.raw:
                action.move.raw = dict(dex_move.raw)
            if action.move.power in (None, 0) and dex_move.power not in (None, 0):
                action.move.power = dex_move.power
            if action.move.accuracy is None:
                action.move.accuracy = dex_move.accuracy
            if action.move.type is None:
                action.move.type = dex_move.type
            if action.move.priority == 0:
                action.move.priority = dex_move.raw.get("priority", 0)

        slots = getattr(user, "activemoveslot_set", None)
        if slots is not None:
            try:
                slot_iter = slots.all()
            except Exception:  # pragma: no cover - fallback for stubs
                slot_iter = slots
            for slot in slot_iter:
                if getattr(getattr(slot, "move", None), "name", "").lower() == action.move.name.lower():
                    current = getattr(slot, "current_pp", None)
                    if current is not None:
                        if current <= 0:
                            return
                        if action.move.pp is None:
                            action.move.pp = current
                    break
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

        eff = 1.0
        if action.move.type:
            try:
                from pokemon.data import TYPE_CHART
                chart = TYPE_CHART.get(action.move.type.capitalize())
                if chart:
                    for typ in getattr(target, "types", []):
                        val = chart.get(typ.capitalize(), 0)
                        if val == 3:
                            eff = 0
                            break
                        elif val == 1:
                            eff *= 2
                        elif val == 2:
                            eff *= 0.5
            except Exception:
                pass

        if eff == 0:
            try:
                user.tempvals["moved"] = True
            except Exception:
                pass
            if action.move.raw.get("selfdestruct") == "always":
                user.hp = 0
            return

        start_hp = getattr(target, "hp", 0)
        if action.move.onBeforeMove:
            try:
                action.move.onBeforeMove(user, target, self)
            except Exception:
                action.move.onBeforeMove(user, target)
        executed = self._do_move(user, target, action.move)
        end_hp = getattr(target, "hp", 0)
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
        if dmg > 0:
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')} used {action.move.name} on {getattr(target, 'name', 'Pokemon')} and dealt {dmg} damage!"
            )
        else:
            self.log_action(
                f"{getattr(user, 'name', 'Pokemon')} used {action.move.name} on {getattr(target, 'name', 'Pokemon')} but it had no effect!"
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
                        poke.is_fainted = True
                else:
                    for poke in fainted:
                        poke.is_fainted = True

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
                            if oa and oa.action_type is ActionType.MOVE and oa.move and oa.move.name.lower() == "pursuit":
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

    def perform_switch_action(self, participant: BattleParticipant, new_pokemon) -> None:
        """Switch ``participant``'s active Pokémon."""
        self.switch_pokemon(participant, new_pokemon)

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

    def check_fainted(self, pokemon) -> bool:
        """Return ``True`` if ``pokemon`` has fainted."""
        return getattr(pokemon, "hp", 0) <= 0

    def check_win_conditions(self) -> Optional[BattleParticipant]:
        """Return the winning participant if the battle has ended."""
        return self.check_victory()

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
