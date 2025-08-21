"""Implementations for status-oriented move callbacks."""

from random import choice, random

from pokemon.utils.boosts import apply_boost


class Acupressure:
    def onHit(self, user, target, battle):
        """Randomly raise one of the target's stats by 2 stages."""
        stats = ["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"]
        viable = [s for s in stats if getattr(target, "boosts", {}).get(s, 0) < 6]
        if not viable:
            return False
        stat = choice(viable)
        apply_boost(target, {stat: 2})
        return True


class Afteryou:
    def onHit(self, user, target, battle):
        """Make the target act immediately after the user when possible."""
        if not battle:
            return True
        # Fail in singles battles (only one active Pokémon per side)
        if all(len(getattr(p, "active", [])) <= 1 for p in getattr(battle, "participants", [])):
            return False
        queue = getattr(battle, "queue", None)
        if queue:
            action = getattr(queue, "will_move", lambda t: None)(target)
            if not action:
                return False
            getattr(queue, "prioritize_action", lambda a: None)(action)
        return True


class Alluringvoice:
    def onHit(self, user, target, battle):
        """Lower the target's Attack by one stage."""
        apply_boost(target, {"atk": -1})
        return True


class Allyswitch:
    def onHit(self, user, target, battle):
        """Swap positions with the ally if possible."""
        side = getattr(user, "side", None)
        if not side or len(getattr(side, "active", [])) <= 1:
            return False
        active = side.active
        if user not in active:
            return False
        idx = active.index(user)
        other_idx = 1 - idx if len(active) > 1 else idx
        active[idx], active[other_idx] = active[other_idx], active[idx]
        return True

    def onPrepareHit(self, *args, **kwargs):
        return True

    def onRestart(self, *args, **kwargs):
        return True

    def onStart(self, *args, **kwargs):
        return True


class Aquaring:
    """Runtime handler for the Aqua Ring volatile status."""

    def onResidual(self, *args, **kwargs):
        """Heal the user for 1/16 of its maximum HP each turn."""
        user = args[0] if args else None
        if not user:
            return False
        max_hp = getattr(user, "max_hp", 0)
        heal = max_hp // 16
        user.hp = min(getattr(user, "hp", 0) + heal, max_hp)
        return True

    def onStart(self, *args, **kwargs):
        """Activate Aqua Ring on the user so residual can process it."""
        user = args[0] if args else None
        if user and hasattr(user, "volatiles"):
            user.volatiles["aquaring"] = True
        return True


class Aromatherapy:
    def onHit(self, user, target, battle):
        """Cure status conditions of the user's party."""
        for mon in getattr(user, "party", [user]):
            if hasattr(mon, "setStatus"):
                mon.setStatus(0)
        return True


class Assist:
    def onHit(self, user, target, battle):
        """Use a random move known by an ally."""
        allies = [ally for ally in getattr(user, "party", []) if ally is not user]
        moves = []
        for ally in allies:
            moves.extend(getattr(ally, "moves", []))
        moves = [m for m in moves if getattr(m, "name", "").lower() != "assist"]
        if not moves:
            return False
        move = choice(moves)
        if hasattr(move, "onHit"):
            move.onHit(user, target, battle)
        return True


class Attract:
    """Runtime handler for the Attract volatile status."""

    def onBeforeMove(self, *args, **kwargs):
        """50% chance the infatuated Pokémon can't move."""
        user = args[0] if args else kwargs.get("user")
        if user and random() < 0.5:
            if hasattr(user, "tempvals"):
                user.tempvals["cant_move"] = "attract"
            return False
        return True

    def onEnd(self, *args, **kwargs):
        """Remove the Attract effect from the target."""
        target = args[0] if args else kwargs.get("target")
        if target and hasattr(target, "volatiles"):
            target.volatiles.pop("attract", None)
        return True

    def onStart(self, *args, **kwargs):
        """Begin infatuation, marking the target as attracted to the user."""
        user = args[0] if args else None
        target = args[1] if len(args) > 1 else None
        if target and hasattr(target, "volatiles"):
            target.volatiles["attract"] = user
        return True

    def onTryImmunity(self, *args, **kwargs):
        """Fail if genders are same or unknown."""
        target = args[0] if args else kwargs.get("target")
        source = args[1] if len(args) > 1 else kwargs.get("source")
        tg = getattr(target, "gender", "N") if target else "N"
        sg = getattr(source, "gender", "N") if source else "N"
        if tg == "N" or sg == "N" or tg == sg:
            return False
        return True

    def onUpdate(self, *args, **kwargs):
        """Clear the effect if the source Pokémon has fainted."""
        target = args[0] if args else kwargs.get("target")
        if not target or not hasattr(target, "volatiles"):
            return False
        src = target.volatiles.get("attract")
        if not src or getattr(src, "hp", 0) <= 0:
            target.volatiles.pop("attract", None)
        return True


__all__ = [
    "Acupressure",
    "Afteryou",
    "Alluringvoice",
    "Allyswitch",
    "Aquaring",
    "Aromatherapy",
    "Assist",
    "Attract",
]

