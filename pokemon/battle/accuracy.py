"""Shared owned-effect accuracy rules for damaging and status moves."""

from types import SimpleNamespace

from .effect_context import EffectContext


class MoveAccuracy:
    """Resolve current ability/item owners before the normal private battle roll."""

    @staticmethod
    def modified(user, target, move, battle=None, *, base=None):
        """Apply source, target, field, item and guaranteed-hit event modifiers."""
        accuracy = getattr(move, "accuracy", True) if base is None else base
        if MoveAccuracy.locked_on(user, target):
            return True
        if accuracy is True:
            return True

        def apply(holder, hook, owner, state_name):
            nonlocal accuracy
            if holder is None or not hasattr(holder, "call"):
                return
            state = getattr(owner, state_name, {})
            state["target"] = owner
            result = holder.call(hook, accuracy, source=user, user=user, attacker=user,
                                 target=target, defender=target, move=move, effect_state=state)
            if result is not None:
                accuracy = result

        ignored = getattr(battle, "_move_ignores_target_ability", None)
        target_ignored = callable(ignored) and ignored(user, target, move)
        apply(EffectContext.ability(user), "onSourceModifyAccuracy", user, "ability_state")
        if not target_ignored:
            apply(EffectContext.ability(target), "onModifyAccuracy", target, "ability_state")
        owners = []
        for owner in [user, target] + [mon for part in getattr(battle, "participants", [])
                                      for mon in getattr(part, "active", []) if getattr(mon, "hp", 0) > 0]:
            if all(owner is not previous for previous in owners):
                owners.append(owner)
        for owner in owners:
            if owner is target and target_ignored:
                continue
            apply(EffectContext.ability(owner), "onAnyModifyAccuracy", owner, "ability_state")
        apply(EffectContext.item(user), "onSourceModifyAccuracy", user, "item_state")
        apply(EffectContext.item(target), "onModifyAccuracy", target, "item_state")
        if accuracy is not True and isinstance(accuracy, (int, float)):
            raw = getattr(move, "raw", {}) or {}
            own = (getattr(user, "boosts", {}) or {}).get("accuracy", 0)
            evasion = (getattr(target, "boosts", {}) or {}).get("evasion", 0)
            # Read only the participating owners. An uninvolved Unaware ally
            # cannot erase a stage, and an ignored target ability cannot act.
            if (raw.get("ignoreAccuracy") or getattr(move, "ignoreAccuracy", False)
                    or not target_ignored and EffectContext.key(EffectContext.ability(target)) == "unaware"):
                own = 0
            if (raw.get("ignoreEvasion") or getattr(move, "ignoreEvasion", False)
                    or EffectContext.key(EffectContext.ability(user)) == "unaware"):
                evasion = 0
            own, evasion = max(-6, min(6, own)), max(-6, min(6, evasion))
            stage = max(-6, min(6, own - evasion))
            accuracy = int(accuracy * (3 + stage) / 3 if stage >= 0 else accuracy * 3 / (3 - stage))
        if battle is not None and hasattr(battle, "runEvent"):
            result = battle.runEvent("Accuracy", target, user, move, accuracy)
            if result is not None:
                accuracy = 0 if result is False else result
        return accuracy

    @classmethod
    def check_status(cls, user, target, move, battle=None):
        """Use the same modifiers before a targeted status handler changes state."""
        from .damage import accuracy_check

        accuracy = cls.modified(user, target, move, battle)
        if accuracy is True or isinstance(accuracy, (int, float)) and accuracy >= 100:
            return True
        hit = accuracy_check(SimpleNamespace(accuracy=accuracy), rng=getattr(battle, "rng", None))
        item = EffectContext.item(user)
        if not hit and hasattr(item, "call"):
            item.call("onAccuracyMiss", pokemon=user, target=target, move=move)
        return hit
    @staticmethod
    def reference(pokemon):
        """Use the stable combatant identity rather than an ephemeral object."""
        return str(getattr(pokemon, "model_id", None) or getattr(pokemon, "name", ""))

    @classmethod
    def locked_on(cls, user, target):
        """A lock only grants accuracy against its recorded target."""
        state = (getattr(user, "volatiles", {}) or {}).get("lockon")
        return (isinstance(state, dict) and state.get("duration", 0) > 0
                and state.get("target_ref") == cls.reference(target))

