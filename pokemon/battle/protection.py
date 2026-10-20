"""Resolve named protection and contact retaliation on the blocked attack."""

from .effect_context import EffectContext
from .indirect_damage import IndirectEffect, apply_indirect_damage


class MoveProtection:
    """Keep the protecting holder separate from the incoming contact attacker."""

    named = ("banefulbunker", "burningbulwark", "kingsshield", "obstruct", "silktrap", "spikyshield")
    damage_only = {"burningbulwark", "kingsshield", "obstruct", "silktrap"}

    @classmethod
    def blocks(cls, holder, source, move, battle):
        """Apply one eligible shield counter, retaining ordinary bypass rules."""
        if holder is source or getattr(move, "breaksProtect", False):
            return False
        state = getattr(holder, "volatiles", {}) or {}
        guard = next((name for name in cls.named if state.get(name)), None)
        if not guard and not state.get("protect"):
            return False
        raw = getattr(move, "raw", {}) or {}
        category = getattr(move, "category", None) or raw.get("category")
        if guard in cls.damage_only and category == "Status":
            return False
        flags = getattr(move, "flags", None) or raw.get("flags", {})
        if flags.get("protect", True) is False or flags.get("protect") == 0:
            return False
        contact = bool(flags.get("contact"))
        contact = contact and EffectContext.key(EffectContext.ability(source)) != "longreach"
        contact = contact and EffectContext.key(EffectContext.item(source)) != "protectivepads"
        if guard and contact:
            cause = IndirectEffect(guard, "Condition")
            status = {"banefulbunker": "psn", "burningbulwark": "brn"}.get(guard)
            if status and hasattr(source, "setStatus"):
                source.setStatus(status, source=holder, battle=battle, effect=cause)
            boosts = {"kingsshield": {"atk": -1}, "obstruct": {"def": -2}, "silktrap": {"spe": -1}}.get(guard)
            if boosts:
                from pokemon.utils.boosts import apply_boost
                apply_boost(source, boosts, source=holder, effect=cause)
            if guard == "spikyshield":
                apply_indirect_damage(source, max(1, source.max_hp // 8), battle=battle, source=holder, effect=cause)
        return True
