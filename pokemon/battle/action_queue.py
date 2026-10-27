"""Mutable remaining actions for effects that inspect or reorder current choices."""


class ActionQueue:
    """Own only unexecuted actions; popped actions can never be selected again."""

    def __init__(self, actions):
        self.actions = list(actions)

    def __bool__(self):
        return bool(self.actions)

    def pop_next(self):
        """Remove the next choice before its move callbacks run."""
        return self.actions.pop(0)

    def will_move(self, pokemon):
        """Return the current unexecuted attack selected by this Pokemon."""
        for action in self.actions:
            kind = getattr(getattr(action, "action_type", None), "name", "")
            actor = getattr(action, "pokemon", None)
            if actor is None:
                active = getattr(getattr(action, "actor", None), "active", [])
                actor = active[0] if active else None
            if actor is pokemon and kind == "MOVE" and getattr(actor, "hp", 0) > 0:
                return action
        return None

    def _remove(self, action):
        for index, candidate in enumerate(self.actions):
            if candidate is action:
                return self.actions.pop(index)
        return None

    def cancel_action(self, pokemon):
        """Cancel only that battler's still-pending actions, preserving other actors."""
        previous = len(self.actions)
        self.actions[:] = [action for action in self.actions if (
            getattr(action, "pokemon", None) or next(iter(getattr(action.actor, "active", [])), None)) is not pokemon]
        return len(self.actions) != previous

    def prioritize_action(self, action):
        """Place a still-pending move immediately after the executing action."""
        selected = self._remove(action)
        if selected is None:
            return False
        self.actions.insert(0, selected)
        return True

    def defer_action(self, action):
        """Place a still-pending move after the remaining actions."""
        selected = self._remove(action)
        if selected is None:
            return False
        self.actions.append(selected)
        return True
