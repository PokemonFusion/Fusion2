"""Helpers for queuing battle actions.

This module defines :class:`ActionQueue`, a mixin providing a generic method
for queuing battle actions.  The helper centralises common steps like looking
up the active position for a trainer, checking for already queued actions,
persisting state and triggering turn advancement.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from .compat import log_info, _battle_norm_key


class ActionQueue:
    """Mixin implementing generic action queuing for battles."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_position_for_trainer(self, trainer) -> Tuple[str | None, Any]:
        """Return the active position for ``trainer``."""

        if not self.data:
            return None, None
        team = None
        if trainer in getattr(self, "teamA", []):
            team = "A"
        elif trainer in getattr(self, "teamB", []):
            team = "B"
        else:
            for idx, part in enumerate(getattr(self.battle, "participants", [])):
                if getattr(part, "player", None) is trainer:
                    team = "A" if idx == 0 else "B"
                    break
        if not team:
            return None, None
        pos_name = f"{team}1"
        return pos_name, self.data.turndata.positions.get(pos_name)

    def _already_queued(self, pos_name, pos, caller, action_desc: str) -> bool:
        """Return ``True`` if ``pos`` already has an action queued."""

        pokemon_name = getattr(getattr(pos, "pokemon", None), "name", "Unknown")
        if pos.getAction() or (self.state and pos_name in self.state.declare):
            self._msg_to(
                caller or self.captainA,
                f"{pokemon_name} already has an action queued this turn.",
            )
            log_info(
                f"Ignored {action_desc} for {pokemon_name} at {pos_name}: action already queued"
            )
            self.maybe_run_turn()
            return True
        return False

    # ------------------------------------------------------------------
    # Generic queuing implementation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Public queueing API
    # ------------------------------------------------------------------

    def queue_move(self, move_key: str, target: str = "B1", caller=None) -> None:
        """Queue a move by its dex key and run the turn if ready."""

        norm_key = _battle_norm_key(move_key)
        self._queue_action(
            caller,
            f"move {norm_key}",
            lambda pos: pos.declareAttack(target, norm_key),
            {"move": norm_key, "target": target},
            "Queued move {move} targeting {target} from {pokemon} at {pos}",
            {"move": norm_key, "target": target},
            "queued move",
        )

    def queue_switch(self, slot: int, caller=None) -> None:
        """Queue a Pokémon switch and run the turn if ready."""

        self._queue_action(
            caller,
            "switch",
            lambda pos: pos.declareSwitch(slot),
            {"switch": slot},
            "Queued switch to slot {slot} for {pokemon} at {pos}",
            {"slot": slot},
            "queued switch",
        )

    def queue_item(self, item_name: str, target: str = "B1", caller=None) -> None:
        """Queue an item use and run the turn if ready."""

        self._queue_action(
            caller,
            f"item {item_name}",
            lambda pos: pos.declareItem(item_name),
            {"item": item_name, "target": target},
            "Queued item {item} targeting {target} from {pokemon} at {pos}",
            {"item": item_name, "target": target},
            "queued item",
        )

    def queue_run(self, caller=None) -> None:
        """Queue a flee attempt and run the turn if ready."""

        self._queue_action(
            caller,
            "flee attempt",
            lambda pos: pos.declareRun(),
            {"run": "1"},
            "Queued attempt to flee by {pokemon} at {pos}",
            {},
            "flee attempt",
        )
