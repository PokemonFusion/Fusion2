"""Held-item residual and retaliation effects through normal battle guards."""

from .effect_context import EffectContext
from .indirect_damage import IndirectEffect, apply_indirect_damage
from .item_consumption import ReactiveItemConsumption


class HeldItemEffects:
    """Retain the item's identity while applying guarded HP changes."""

    @staticmethod
    def damage(recipient, holder, divisor, *, item=None):
        """Apply rounded indirect damage, returning only actual HP loss."""
        item = item or EffectContext.item(holder)
        return apply_indirect_damage(recipient, max(1, recipient.max_hp // divisor),
                                     source=holder,
                                     effect=IndirectEffect(EffectContext.key(item), "Item"))

    @staticmethod
    def heal(pokemon, divisor):
        """Reusable residual healing respects TryHeal and never revives."""
        if pokemon is None or pokemon.hp <= 0:
            return 0
        battle = getattr(pokemon, "battle", None)
        if battle is None:
            return 0
        return battle.heal(pokemon, max(1, pokemon.max_hp // divisor), source=pokemon,
                           effect=EffectContext.item(pokemon))

    @staticmethod
    def contact(source, target, move):
        """Use current contact flags, including Glove/Long Reach modification."""
        return bool(source and target and source is not target and move
                    and move.flags.get("contact")
                    and EffectContext.key(EffectContext.item(source)) != "protectivepads")

    @classmethod
    def retaliate(cls, damage, target, source, move, category):
        """Magic Guard retains the berry; permitted eating owns its history."""
        if not (source and target and move and move.category == category
                and damage > 0 and source.hp > 0):
            return
        battle = getattr(target, "battle", None)
        participant = battle.participant_for(source) if battle else None
        if not participant or source not in participant.active:
            return
        if EffectContext.key(EffectContext.ability(source)) == "magicguard":
            return
        item = EffectContext.item(target)
        divisor = 4 if EffectContext.key(EffectContext.ability(target)) == "ripen" else 8
        if ReactiveItemConsumption.eat(target, source=source, effect=move, allow_fainted=True):
            cls.damage(source, target, divisor, item=item)
