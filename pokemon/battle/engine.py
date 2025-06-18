"""Basic battle engine implementing turn-based combat.

This module provides a simplified framework for battles using the design
specification found in the repository documentation.  The focus is on
turn ordering and state tracking rather than full battle logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional


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
    effect_function: Optional[Callable] = None

    def execute(self, user, target, battle: "Battle") -> None:
        """Execute this move's effect."""
        if self.effect_function:
            self.effect_function(user, target, battle)


@dataclass
class Action:
    """Container describing a chosen action for the turn."""

    actor: "BattleParticipant"
    action_type: ActionType
    target: Optional["BattleParticipant"] = None
    move: Optional[BattleMove] = None
    priority: int = 0


class BattleParticipant:
    """Represents one side of a battle."""

    def __init__(self, name: str, pokemons: List, is_ai: bool = False):
        self.name = name
        self.pokemons = pokemons
        self.active: List = []
        self.is_ai = is_ai
        self.has_lost = False

    def choose_action(self, battle: "Battle") -> Optional[Action]:
        """Return an Action object for this turn.

        This default AI simply uses the first move of the first active
        Pokémon against the opposing participant's first active Pokémon.
        """

        if not self.active:
            return None
        active_poke = self.active[0]
        if not hasattr(active_poke, "moves") or not active_poke.moves:
            return None
        move = active_poke.moves[0]
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
    # Turn logic
    # ------------------------------------------------------------------
    def start_turn(self) -> None:
        """Reset temporary flags or display status."""
        self.turn_count += 1

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

    def execute_actions(self, actions: List[Action]) -> None:
        for action in actions:
            if action.action_type is ActionType.MOVE and action.move:
                action.move.execute(action.actor.active[0], action.target.active[0], self)

    def end_turn(self) -> None:
        for part in self.participants:
            if all(getattr(p, "hp", 1) <= 0 for p in part.pokemons):
                part.has_lost = True
        self.check_victory()

    def run_turn(self) -> None:
        self.start_turn()
        actions = self.select_actions()
        actions = self.order_actions(actions)
        self.execute_actions(actions)
        self.end_turn()
