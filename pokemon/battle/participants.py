"""Battle participant models.

This module defines :class:`BattleParticipant`, representing one side in a
battle. It was extracted from ``engine.py`` to improve modularity.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from .battledata import Move
from utils.safe_import import safe_import

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

        battle_side_cls = getattr(safe_import("pokemon.battle.engine"), "BattleSide")
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
        _select_ai_action = safe_import("pokemon.battle.engine")._select_ai_action  # type: ignore[attr-defined]

        return _select_ai_action(self, active_poke, battle)

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
        _select_ai_action = safe_import("pokemon.battle.engine")._select_ai_action  # type: ignore[attr-defined]

        for active_poke in self.active:
            action = _select_ai_action(self, active_poke, battle)
            if action:
                actions.append(action)
        return actions


__all__ = ["BattleParticipant"]
