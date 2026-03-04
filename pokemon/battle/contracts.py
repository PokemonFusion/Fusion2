"""Protocol contracts and adapters for battle-facing collaborators.

The battle engine interacts with participants, Pokémon objects and contextual
battle state that may come from full Evennia models or lightweight test
doubles.  This module centralizes the required interfaces and small adapters so
call-sites can rely on stable method signatures instead of ad-hoc probing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from .actions import Action
else:  # pragma: no cover - runtime alias avoids circular imports
    Action = Any


@runtime_checkable
class CombatPokemonProtocol(Protocol):
    """State required from a Pokémon while resolving battle turns."""

    hp: int
    max_hp: int
    status: Any
    tempvals: dict[str, Any]
    volatiles: dict[str, Any]
    boosts: dict[str, Any]


@runtime_checkable
class ParticipantProtocol(Protocol):
    """Behavior required from battle participants during action selection."""

    active: Sequence[CombatPokemonProtocol]
    pending_action: Action | list[Action] | None
    has_lost: bool
    team: str | None

    def choose_action(self, battle: "BattleContextProtocol") -> Action | None:
        """Return a single action for the current turn."""

    def choose_actions(self, battle: "BattleContextProtocol") -> list[Action]:
        """Return one or more actions for the current turn."""


@runtime_checkable
class BattleContextProtocol(Protocol):
    """Battle context operations used by turn and condition helpers."""

    rng: Any
    field: Any
    participants: Sequence[ParticipantProtocol]

    def announce_status_change(self, pokemon: CombatPokemonProtocol, status: str, event: str = "") -> None:
        """Announce a status-change message to battle logs/output."""

    def log_action(self, message: str) -> None:
        """Record a battle action message."""


@dataclass
class ParticipantAdapter:
    """Adapter exposing :class:`ParticipantProtocol` for lightweight doubles."""

    raw: Any

    @property
    def active(self):
        return getattr(self.raw, "active", [])

    @property
    def pending_action(self):
        return getattr(self.raw, "pending_action", None)

    @pending_action.setter
    def pending_action(self, value):
        setattr(self.raw, "pending_action", value)

    @property
    def has_lost(self) -> bool:
        return bool(getattr(self.raw, "has_lost", False))

    @property
    def team(self) -> str | None:
        return getattr(self.raw, "team", None)

    def choose_action(self, battle: "BattleContextProtocol") -> Action | None:
        chooser = getattr(self.raw, "choose_action", None)
        if callable(chooser):
            return chooser(battle)
        return None

    def choose_actions(self, battle: "BattleContextProtocol") -> list[Action]:
        chooser_many = getattr(self.raw, "choose_actions", None)
        if callable(chooser_many):
            actions = chooser_many(battle)
            if isinstance(actions, list):
                return [act for act in actions if act is not None]
            return [actions] if actions is not None else []

        action = self.choose_action(battle)
        if action is not None:
            return [action]

        pending = self.pending_action
        if pending is None:
            return []
        if isinstance(pending, list):
            self.pending_action = None
            return [act for act in pending if act is not None]
        self.pending_action = None
        return [pending]


@dataclass
class BattleContextAdapter:
    """Adapter implementing :class:`BattleContextProtocol` for test doubles."""

    raw: Any

    @property
    def rng(self):
        return getattr(self.raw, "rng", None)

    @property
    def field(self):
        return getattr(self.raw, "field", None)

    @property
    def participants(self):
        return getattr(self.raw, "participants", [])

    def announce_status_change(self, pokemon: CombatPokemonProtocol, status: str, event: str = "") -> None:
        callback = getattr(self.raw, "announce_status_change", None)
        if callable(callback):
            callback(pokemon, status, event=event)

    def log_action(self, message: str) -> None:
        callback = getattr(self.raw, "log_action", None)
        if callable(callback):
            callback(message)


def adapt_participants(participants: Iterable[Any]) -> list[ParticipantAdapter]:
    """Return participant adapters for a participant iterable."""

    return [ParticipantAdapter(part) for part in participants]
