"""Utilities for battle-prefixed messaging."""

class MessagingMixin:
    """Mixin providing battle-prefixed messaging helpers.

    Classes inheriting this mixin are expected to define ``captainA`` and
    optionally ``captainB`` attributes referencing the battling trainers.  They
    may also provide ``trainers`` and ``observers`` collections.  Messages sent
    through these helpers are automatically prefixed with the battle header so
    that recipients can easily identify the source.
    """

    def msg(self, text: str) -> None:
        """Send ``text`` to all trainers and observers with a battle prefix."""
        trainers = getattr(self, "trainers", None)
        if not trainers:
            trainers = [t for t in (getattr(self, "captainA", None), getattr(self, "captainB", None)) if t]
        names = [getattr(t, "key", str(t)) for t in trainers]
        prefix = f"[Battle: {' vs. '.join(names)}]"
        message = f"{prefix} {text}"
        for obj in trainers + list(getattr(self, "observers", set())):
            if hasattr(obj, "msg"):
                obj.msg(message)

    def _msg_to(self, obj, text: str) -> None:
        """Send ``text`` to ``obj`` with a battle prefix."""
        names = [
            getattr(getattr(self, "captainA", None), "key", str(getattr(self, "captainA", None))),
            (
                getattr(getattr(self, "captainB", None), "key", str(getattr(self, "captainB", None)))
                if getattr(self, "captainB", None)
                else None
            ),
        ]
        names = [n for n in names if n]
        prefix = f"[Battle: {' vs. '.join(names)}]"
        if hasattr(obj, "msg"):
            obj.msg(f"{prefix} {text}")
