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

from pokemon.dex import MOVEDEX


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
    basePowerCallback: Optional[Callable] = None
    type: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def execute(self, user, target, battle: "Battle") -> None:
        """Execute this move's effect."""
        if self.onTry:
            self.onTry(user, target, self, battle)
        if self.onHit:
            self.onHit(user, target, battle)
            return

        # Default behaviour for moves without custom handlers
        from .damage import damage_calc
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

        result = damage_calc(user, target, move, battle=battle)
        dmg = sum(result.debug.get("damage", []))
        if hasattr(target, "hp"):
            target.hp = max(0, target.hp - dmg)
            if dmg > 0:
                try:
                    target.tempvals["took_damage"] = True
                except Exception:
                    pass

        # Handle side conditions set by this move
        side_cond = self.raw.get("sideCondition") if self.raw else None
        if side_cond:
            condition = self.raw.get("condition", {})
            try:
                from pokemon.dex.functions import moves_funcs
            except Exception:
                moves_funcs = None
            target_side = user
            if self.raw.get("target") != "allySide":
                target_side = target
            part = battle.participant_for(target_side)
            if part:
                battle.add_side_condition(part, side_cond, condition, source=user, moves_funcs=moves_funcs)



@dataclass
class Action:
    """Container describing a chosen action for the turn."""

    actor: "BattleParticipant"
    action_type: ActionType
    target: Optional["BattleParticipant"] = None
    move: Optional[BattleMove] = None
    item: Optional[str] = None
    priority: int = 0


class BattleParticipant:
    """Represents one side of a battle."""

    def __init__(self, name: str, pokemons: List, is_ai: bool = False):
        self.name = name
        self.pokemons = pokemons
        self.active: List = []
        self.is_ai = is_ai
        self.has_lost = False
        self.pending_action: Optional[Action] = None
        self.side = BattleSide()
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
            return action

        if not self.is_ai:
            return None

        if not self.is_ai:
            action = self.pending_action
            self.pending_action = None
            return action

        if not self.active:
            return None
        active_poke = self.active[0]
        if not hasattr(active_poke, "moves") or not active_poke.moves:
            return None
        move_data = active_poke.moves[0]

        def _norm(name: str) -> str:
            return name.replace(" ", "").replace("-", "").replace("'", "").lower()

        move_entry = MOVEDEX.get(_norm(move_data.name))
        on_hit_func = None
        on_try_func = None
        base_power_cb = None
        if move_entry:
            from pokemon.dex.functions import moves_funcs
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
                basePowerCallback=base_power_cb,
                type=getattr(move_entry, "type", None),
                raw=move_entry.raw,
            )
        else:
            move = BattleMove(name=move_data.name, priority=getattr(move_data, "priority", 0))
        opponent = battle.opponent_of(self)
        if not opponent or not opponent.active:
            return None
        target = opponent.active[0]
        priority = getattr(move, "priority", 0)
        return Action(self, ActionType.MOVE, target, move, priority)


class Battle:
    """Main battle controller."""

    def __init__(self, battle_type: BattleType, participants: List[BattleParticipant]):
        self.type = battle_type
        self.participants = participants
        self.turn_count = 0
        self.battle_over = False
        from .battledata import Field
        self.field = Field()

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
        for part in self.participants:
            if part is not participant:
                return part
        return None

    def check_victory(self) -> Optional[BattleParticipant]:
        remaining = [p for p in self.participants if not p.has_lost]
        if len(remaining) <= 1:
            self.battle_over = True
            return remaining[0] if remaining else None
        return None

    # ------------------------------------------------------------------
    # Pseudocode mapping
    # ------------------------------------------------------------------
    def run_switch(self) -> None:
        """Handle Pokémon switches before moves are executed."""

        for part in self.participants:
            if part.has_lost:
                continue

            # If no active Pokémon, bring out the first healthy one
            if not part.active:
                for poke in part.pokemons:
                    if getattr(poke, "hp", 0) > 0:
                        part.active = [poke]
                        setattr(poke, "side", part.side)
                        ability = getattr(poke, "ability", None)
                        if ability and hasattr(ability, "call"):
                            ability.call("onStart", poke, self)
                            ability.call("onSwitchIn", poke, self)
                        break
                continue

            # Replace fainted active Pokémon if possible
            active = part.active[0]
            if getattr(active, "hp", 0) <= 0:
                for poke in part.pokemons:
                    if poke is active:
                        continue
                    if getattr(poke, "hp", 0) > 0:
                        part.active = [poke]
                        setattr(poke, "side", part.side)
                        ability = getattr(poke, "ability", None)
                        if ability and hasattr(ability, "call"):
                            ability.call("onStart", poke, self)
                            ability.call("onSwitchIn", poke, self)
                        break

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

    def run_move(self) -> None:
        """Execute ordered actions for this turn."""

        # TODO: incorporate full move failure and targeting rules
        actions = self.select_actions()
        actions = self.order_actions(actions)
        self.execute_actions(actions)

    def run_faint(self) -> None:
        """Handle fainted Pokémon and mark participants as losing if needed."""

        for part in self.participants:
            if part.has_lost:
                continue

            # Remove fainted Pokémon from the active list
            part.active = [p for p in part.active if getattr(p, "hp", 0) > 0]

            # Check if the participant has any Pokémon left
            if not any(getattr(p, "hp", 0) > 0 for p in part.pokemons):
                part.has_lost = True

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

        # Remove Pokémon that fainted from residual damage
        self.run_faint()

        # Auto-switch in replacements for any empty sides
        self.run_switch()
        self.run_after_switch()

    def run_action(self) -> None:
        """Main action runner modeled on Showdown's `runAction`."""

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
                    ability = getattr(poke, "ability", None)
                    if ability and hasattr(ability, "call"):
                        ability.call("onStart", poke, self)
                        ability.call("onSwitchIn", poke, self)

    def select_actions(self) -> List[Action]:
        actions: List[Action] = []
        for part in self.participants:
            if part.has_lost:
                continue
            action = part.choose_action(self)
            if action:
                actions.append(action)
        return actions

    def order_actions(self, actions: List[Action]) -> List[Action]:
        return sorted(actions, key=lambda a: a.priority, reverse=True)

    def status_prevents_move(self, pokemon) -> bool:
        """Return True if the Pokemon cannot act due to status."""
        status = getattr(pokemon, "status", None)
        try:
            from pokemon.dex.functions.conditions_funcs import CONDITION_HANDLERS
        except Exception:
            CONDITION_HANDLERS = {}
        handler = CONDITION_HANDLERS.get(status)
        if handler and hasattr(handler, "onBeforeMove"):
            result = handler.onBeforeMove(pokemon, battle=self)
            return result is False
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

    def execute_actions(self, actions: List[Action]) -> None:
        for action in actions:
            if action.action_type is ActionType.MOVE and action.move:
                actor_poke = action.actor.active[0]
                if self.status_prevents_move(actor_poke):
                    continue
                action.move.execute(actor_poke, action.target.active[0], self)
                try:
                    actor_poke.tempvals["moved"] = True
                except Exception:
                    pass
            elif action.action_type is ActionType.ITEM and action.item:
                self.execute_item(action)

    def execute_item(self, action: Action) -> None:
        """Handle item usage during battle."""
        item_name = action.item.lower()
        target = action.target or self.opponent_of(action.actor)
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
            caught = attempt_capture(max_hp, target_poke.hp, catch_rate, status=status)
            if caught:
                target.active.remove(target_poke)
                if target_poke in target.pokemons:
                    target.pokemons.remove(target_poke)
                target.has_lost = True
                self.check_victory()

    def end_turn(self) -> None:
        for part in self.participants:
            if all(getattr(p, "hp", 1) <= 0 for p in part.pokemons):
                part.has_lost = True
            for poke in part.active:
                ability = getattr(poke, "ability", None)
                if ability and hasattr(ability, "call"):
                    ability.call("onEnd", poke, self)
        self.check_victory()

    def run_turn(self) -> None:
        self.start_turn()
        self.run_action()
        self.end_turn()
