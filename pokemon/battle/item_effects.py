"""Shared rules for native held-item eligibility and one-shot effects."""

from .effect_context import EffectContext


class HeldItemRules:
    """Apply existing items through authoritative battle state and services."""

    @staticmethod
    def field_duration(source, item_key, ordinary=5, extended=8):
        """Extend a field effect only while its native held item is effective."""
        return extended if EffectContext.key(EffectContext.item(source)) == item_key else ordinary

    @staticmethod
    def eject(holder, recipient, *, source=None, effect=None, forced=False):
        """Consume only when the native replacement protocol can switch."""
        if holder is None or recipient is None or holder.hp <= 0 or recipient.hp <= 0:
            return False
        battle = getattr(holder, "battle", None)
        if battle is None:
            return False
        from .active_slots import slot_for
        from .legal_actions import LegalActions

        participant = battle.participant_for(recipient)
        if participant is None or recipient not in participant.active:
            return False
        slot = slot_for(participant, recipient)
        if not LegalActions(battle, participant, recipient).reserves(slot=slot):
            return False
        if forced and not battle._can_drag_out(recipient, source=source, effect=effect):
            return False
        if not forced and battle._is_trapped(recipient):
            return False
        if not battle.use_item(holder) or not battle.remove_item(holder, used=True):
            return False
        recipient.tempvals["switch_out"] = True
        if forced:
            recipient.tempvals["dragged_out"] = True
        return True

    @staticmethod
    def apply_gem_power(move):
        """Apply the armed Gem multiplier once, including Substitute hits."""
        multiplier = getattr(move, "_gem_power_multiplier", 1)
        if multiplier != 1 and not getattr(move, "_gem_power_applied", False):
            move._gem_original_power = move.power
            move.power = int(move.power * multiplier)
            move._gem_power_applied = True

    @staticmethod
    def can_evolve(pokemon):
        """Read real evolution data, retaining legacy standalone adapters."""
        if pokemon is None:
            return False
        lookup = getattr(pokemon, "_lookup_species_entry", None)
        name = str(getattr(pokemon, "species", None) or getattr(pokemon, "name", ""))
        entry = lookup(name) if callable(lookup) else None
        if entry is None:
            from pokemon.dex import POKEDEX
            from pokemon.names import resolve_dex_entry

            entry = resolve_dex_entry(POKEDEX, name)
        if entry is not None:
            return bool(getattr(entry, "raw", {}).get("evos"))
        return not getattr(pokemon, "fully_evolved", True)

    @staticmethod
    def consume_gem(source, target, move, move_type):
        """Arm one matching attack without changing persistent stat stages."""
        if (
            source is None
            or target is source
            or move is None
            or getattr(move, "category", "Status") == "Status"
            or getattr(move, "type", None) != move_type
            or (getattr(move, "flags", {}) or {}).get("pledgecombo")
            or getattr(move, "_gem_boosted", False)
        ):
            return
        if not EffectContext.item(source):
            return
        move._gem_boosted = True
        move._gem_power_multiplier = 1.3

    @staticmethod
    def commit_gem(source, move):
        """Debit an armed Gem only after actual HP or Substitute damage."""
        if not getattr(move, "_gem_boosted", False) or getattr(move, "_gem_consumed", False):
            return
        battle = getattr(source, "battle", None)
        if battle is not None:
            if not battle.use_item(source) or not battle.remove_item(
                source, source=source, effect=move, used=True
            ):
                return
        else:
            source.item = None
        move._gem_consumed = True

    @staticmethod
    def recoil_life_orb(source, move):
        """Require dealt damage and honor the existing recoil exceptions."""
        if source is None or move is None or not getattr(move, "total_damage", 0):
            return
        ability = EffectContext.key(EffectContext.ability(source))
        raw = getattr(move, "raw", {}) or {}
        if ability == "magicguard" or (
            ability == "sheerforce"
            and (
                getattr(move, "sheer_force_boosted", False)
                or raw.get("secondary")
                or raw.get("secondaries")
            )
        ):
            return
        from .indirect_damage import IndirectEffect, apply_indirect_damage

        apply_indirect_damage(
            source,
            max(1, source.max_hp // 10),
            battle=getattr(source, "battle", None),
            source=source,
            effect=IndirectEffect("lifeorb", "Item"),
        )

    @staticmethod
    def berry_pp(pokemon, *, restore=False, amount=10):
        """Read depleted owned slots and retain their actual boosted caps."""
        battle = getattr(pokemon, "battle", None)
        if battle is not None and callable(getattr(battle, "_move_pp_states", None)):
            states = battle._move_pp_states(pokemon)
        else:
            from pokemon.dex import MOVEDEX
            from pokemon.names import resolve_dex_entry

            states = []
            for move in getattr(pokemon, "moves", []):
                entry = resolve_dex_entry(MOVEDEX, getattr(move, "name", ""))
                maximum = getattr(move, "max_pp", None)
                if maximum is None:
                    maximum = (getattr(entry, "raw", {}) or {}).get("pp")
                states.append(
                    (move, getattr(move, "name", ""), getattr(move, "pp", None), maximum, False)
                )
        depleted = [state for state in states if state[2] == 0 and state[3]]
        if restore and not depleted:
            usable = [state for state in states if isinstance(state[2], int) and state[3]]
            depleted = sorted(usable, key=lambda state: state[2])[:1]
        for slot, name, current, capacity, stored in depleted:
            if not restore:
                return True
            updated = min(int(capacity), current + amount)
            setattr(slot, "current_pp" if stored else "pp", updated)
            if stored and callable(getattr(slot, "save", None)):
                slot.save(update_fields=["current_pp"])
            for move in getattr(pokemon, "moves", []):
                if EffectContext.key(getattr(move, "name", "")) == EffectContext.key(name):
                    move.pp = updated
            return updated
        return 0 if restore else False

    @staticmethod
    def flavor_berry(pokemon, lowered_natures):
        """Heal and apply nature-dependent confusion through normal guards."""
        if pokemon is None:
            return
        amount = max(1, pokemon.max_hp // 3)
        battle = getattr(pokemon, "battle", None)
        if battle is not None and callable(getattr(battle, "heal", None)):
            battle.heal(pokemon, amount, source=pokemon, effect="item:flavorberry")
        else:
            pokemon.hp = min(pokemon.max_hp, pokemon.hp + amount)
        if str(getattr(pokemon, "nature", "Hardy")) not in lowered_natures:
            return
        if battle is not None and callable(getattr(battle, "apply_volatile_status", None)):
            battle.apply_volatile_status(
                pokemon, "confusion", source=pokemon, effect="item:flavorberry"
            )
        else:
            pokemon.volatiles = getattr(pokemon, "volatiles", {})
            pokemon.volatiles["confusion"] = {"duration": 3}
