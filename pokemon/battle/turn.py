"""Turn management mixin for battle sessions.

This module contains a :class:`TurnManager` mixin that encapsulates the common
turn-handling functionality used by :class:`~pokemon.battle.battleinstance.BattleSession`.
Private helper methods break the logic into smaller units which keeps the public
APIs :meth:`prompt_next_turn` and :meth:`run_turn` readable and easier to
maintain.
"""

from __future__ import annotations

import traceback

from .compat import log_err, log_info, log_warn
from .interface import format_turn_banner, render_interfaces
try:  # pragma: no cover - interface may be stubbed in tests
    from .interface import broadcast_interfaces
except Exception:  # pragma: no cover - fallback implementation
    def broadcast_interfaces(session, *, waiting_on=None):  # type: ignore[misc]
        iface_a, iface_b, iface_w = render_interfaces(
            session.captainA, session.captainB, session.state, waiting_on=waiting_on
        )
        for t in getattr(session, "teamA", []):
            session._msg_to(t, iface_a)
        for t in getattr(session, "teamB", []):
            session._msg_to(t, iface_b)
        for w in getattr(session, "observers", []):
            session._msg_to(w, iface_w)


class TurnManager:
    """Mixin providing turn flow helpers for battle sessions."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _notify_turn_banner(self) -> None:
        """Send the current turn banner to listeners if a battle is active."""

        if self.state and self.battle:
            self.notify(format_turn_banner(getattr(self.battle, "turn_count", 1)))

    def _render_interfaces(self) -> None:
        """Render and broadcast battle interfaces to participants and watchers."""

        if self.captainA and self.state and self.captainB is not None:
            try:
                broadcast_interfaces(self)
            except Exception:
                log_warn("Failed to display battle interface", exc_info=True)

    def _persist_turn_state(self) -> None:
        """Persist the current turn's data and state to backing storage."""

        if getattr(self, "storage", None):
            try:
                self.storage.set("data", self.logic.data.to_dict())
                self.storage.set(
                    "state",
                    self._compact_state_for_persist(self.logic.state.to_dict()),
                )
            except Exception:
                log_warn("Failed to persist battle state", exc_info=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def prompt_next_turn(self) -> None:
        """Prompt the player to issue a command for the next turn."""

        self._set_player_control(True)
        self._notify_turn_banner()
        self._render_interfaces()
        self.msg("The battle awaits your move.")
        if self.battle and getattr(self.battle, "turn_count", 0) == 1:
            log_info(f"Prompted first turn for battle {self.battle_id}")

    def run_turn(self) -> None:
        """Advance the battle by one turn."""

        if not self.battle:
            return

        self._notify_turn_banner()
        log_info(f"Running turn for battle {self.battle_id}")
        self._set_player_control(False)
        try:
            self.battle.run_turn()
        except Exception:
            err_txt = traceback.format_exc()
            self.turn_state["error"] = err_txt
            log_err(
                f"Error while running turn for battle {self.battle_id}:\n{err_txt}",
                exc_info=False,
            )
            self.notify(f"Battle error:\n{err_txt}")
        else:
            log_info(
                f"Finished turn {getattr(self.battle, 'turn_count', '?')} for battle {self.battle_id}"
            )
            self._notify_turn_banner()

        if self.state:
            self.state.declare.clear()
        if self.data:
            for pos in self.data.turndata.positions.values():
                pos.removeDeclare()

        self._persist_turn_state()
        self.prompt_next_turn()


__all__ = ["TurnManager"]

