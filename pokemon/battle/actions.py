"""Helpers for queuing battle actions.

This module defines :class:`ActionQueue`, a mixin providing a generic method
for queuing battle actions.  The helper centralises common steps like looking
up the active position for a trainer, checking for already queued actions,
persisting state and triggering turn advancement.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

try:  # pragma: no cover - Evennia may not be installed during tests
    from evennia.utils.logger import log_info
except Exception:  # pragma: no cover - fallback logger
    import logging

    _log = logging.getLogger(__name__)

    def log_info(*args, **kwargs):  # type: ignore[misc]
        _log.info(*args, **kwargs)


class ActionQueue:
    """Mixin implementing generic action queuing for battles."""

    def _queue_action(
        self,
        caller: Any,
        action_desc: str,
        declare: Callable[[Any], None],
        state_data: Dict[str, Any],
        log_template: str,
        log_params: Dict[str, Any],
        save_desc: str,
    ) -> None:
        """Handle shared logic for queuing an action.

        Parameters
        ----------
        caller : object | None
            Trainer requesting the action.
        action_desc : str
            Description used for duplicate checking and logging.
        declare : Callable[[Any], None]
            Callback applying the action to a position.
        state_data : dict
            Action specific fields to store in ``state.declare``.
        log_template : str
            Template for the action log message. ``pokemon`` and ``pos``
            placeholders will be supplied automatically.
        log_params : dict
            Additional parameters for ``log_template``.
        save_desc : str
            Description used when logging state persistence.
        """

        if not self.data or not self.battle:
            return
        pos_name, pos = self._get_position_for_trainer(caller or self.captainA)
        if not pos:
            return
        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if self._already_queued(pos_name, pos, caller, action_desc):
            return

        declare(pos)

        params = dict(log_params)
        params.update({"pokemon": pokemon_name, "pos": pos_name})
        log_info(log_template.format(**params))

        if self.state:
            actor_id = str(getattr(caller or self.captainA, "id", ""))
            poke_id = str(getattr(getattr(pos, "pokemon", None), "model_id", ""))
            state = dict(state_data)
            state.update({"trainer": actor_id, "pokemon": poke_id})
            self.state.declare[pos_name] = state

        # Persist only the (compacted) state on input to avoid duplicating
        # turndata snapshots.
        self.storage.set(
            "state", self._compact_state_for_persist(self.logic.state.to_dict())
        )
        log_info(f"Saved {save_desc} for {pokemon_name} at {pos_name} to room state")
        self.maybe_run_turn()
