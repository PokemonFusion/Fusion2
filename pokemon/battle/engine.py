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
        # Optional action to be used for the next turn when this participant is
        # controlled externally (e.g. by a player).
        self.pending_action: Optional[Action] = None

    def choose_action(self, battle: "Battle") -> Optional[Action]:
        """Return an Action object for this turn.

        For AI-controlled participants the action is chosen automatically.  For
        non-AI participants this method returns the ``pending_action`` that was
        queued externally.
        """

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

        # Apply very light residual damage for demonstration
        for part in self.participants:
            if part.has_lost:
                continue
            for poke in list(part.active):
                status = getattr(poke, "status", None)
                if status in {"brn", "psn"}:
                    poke.hp = max(0, poke.hp - 1)

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
        self.run_action()
        self.end_turn()
