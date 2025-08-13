"""Battle participant models.

This module defines :class:`BattleParticipant`, representing one side in a
battle. It was extracted from ``engine.py`` to improve modularity.
"""

from __future__ import annotations

import random
from typing import List, Optional, TYPE_CHECKING
from .battledata import Move

if TYPE_CHECKING:  # pragma: no cover - circular imports for typing only
    from pokemon.battle.actions import Action, ActionType
    from pokemon.battle.engine import Battle, BattleMove


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
        Optional team identifier. Participants with the same team are treated
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
        from importlib import import_module

        battle_side_cls = getattr(import_module("pokemon.battle.engine"), "BattleSide")
        self.side = battle_side_cls()
        self.player = player
        self.max_active = max_active
        # Team is optional; if ``None`` participants are assumed to be enemies
        # of everyone else. When provided, participants sharing the same team
        # value are considered allies.
        self.team = team
        for poke in self.pokemons:
            if poke is not None:
                setattr(poke, "side", self.side)

    def choose_action(self, battle: "Battle") -> Optional[Action]:
        """Return an :class:`Action` object for this turn."""

        from pokemon.battle.actions import Action, ActionType

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

        if not self.is_ai or not self.active:
            return None

        active_poke = self.active[0]
        moves = getattr(active_poke, "moves", [])
        move_data = moves[0] if moves else Move(name="Flail")

        mv_key = getattr(move_data, "key", getattr(move_data, "name", ""))
        move_pp = getattr(move_data, "pp", None)
        from .engine import BattleMove, _normalize_key  # runtime import
        from pokemon.dex import MOVEDEX

        move = BattleMove(getattr(move_data, "name", mv_key), pp=move_pp)
        dex_entry = MOVEDEX.get(_normalize_key(getattr(move, "key", mv_key)))
        priority = dex_entry.raw.get("priority", 0) if dex_entry else 0
        move.priority = priority
        opponents = battle.opponents_of(self)
        if not opponents:
            return None
        opponent = random.choice(opponents)
        if not opponent.active:
            return None
        from pokemon.battle.engine import battle_logger as eng_logger
        eng_logger.info("%s chooses %s", self.name, move.name)
        return Action(self, ActionType.MOVE, opponent, move, priority, pokemon=active_poke)

    def choose_actions(self, battle: "Battle") -> List[Action]:
        """Return a list of actions for all active Pokémon."""
        from pokemon.battle.actions import Action, ActionType

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
        from .engine import BattleMove, _normalize_key  # runtime import
        from pokemon.dex import MOVEDEX

        for active_poke in self.active:
            moves = getattr(active_poke, "moves", [])
            move_data = moves[0] if moves else Move(name="Flail")
            mv_key = getattr(move_data, "key", getattr(move_data, "name", ""))
            move_pp = getattr(move_data, "pp", None)
            move = BattleMove(getattr(move_data, "name", mv_key), pp=move_pp)
            dex_entry = MOVEDEX.get(_normalize_key(getattr(move, "key", mv_key)))
            priority = dex_entry.raw.get("priority", 0) if dex_entry else 0
            move.priority = priority
            opponents = battle.opponents_of(self)
            if not opponents:
                continue
            opponent = random.choice(opponents)
            if not opponent.active:
                continue
            from pokemon.battle.engine import battle_logger as eng_logger
            eng_logger.info("%s chooses %s", self.name, move.name)
            actions.append(
                Action(self, ActionType.MOVE, opponent, move, priority, pokemon=active_poke)
            )
        return actions


__all__ = ["BattleParticipant"]
