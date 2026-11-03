"""Read effective battle attributes without changing owned Pokemon data."""

import re


class EffectContext:
    """Resolve current effects at their consumer, retaining stored ownership."""

    @staticmethod
    def key(value):
        """Normalize a dex entity, display name or raw identifier."""
        value = getattr(value, "id", None) or getattr(value, "name", None) or value
        return re.sub(r"[^a-z0-9]", "", str(value or "").lower())

    @classmethod
    def ability(cls, pokemon):
        """Return an active ability without mutating its stored identity."""
        if pokemon is None or getattr(pokemon, "ability_suppressed", False):
            return None
        value = getattr(pokemon, "ability", None)
        if value and isinstance(value, str):
            try:
                from pokemon.dex import ABILITYDEX
            except ImportError:  # Standalone battle adapters may omit the dex.
                ABILITYDEX = {}
            value = ABILITYDEX.get(cls.key(value)) or ABILITYDEX.get(cls.key(value).capitalize()) or value
        flags = (getattr(value, "raw", {}) or {}).get("flags", {})
        held = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        battle = getattr(pokemon, "battle", None)
        if (value and not flags.get("cantsuppress") and cls.key(value) != "neutralizinggas"
                and cls.key(held) != "abilityshield" and battle is not None):
            if (getattr(pokemon, "volatiles", {}) or {}).get("gastroacid"):
                return None
            if any(mon is not pokemon and getattr(mon, "hp", 0) > 0
                   and cls.key(getattr(mon, "ability", None)) == "neutralizinggas"
                   for part in getattr(battle, "participants", []) for mon in getattr(part, "active", [])):
                return None
        return value

    @classmethod
    def item(cls, pokemon):
        """Return an effective item while keeping suppressed items owned."""
        field = getattr(getattr(pokemon, "battle", None), "field", None)
        if (getattr(pokemon, "item_suppressed", False)
                or cls.key(cls.ability(pokemon)) == "klutz"
                or (getattr(pokemon, "volatiles", {}) or {}).get("embargo")
                or "magicroom" in (getattr(field, "pseudo_weather", {}) or {})):
            return None
        value = getattr(pokemon, "item", None) or getattr(pokemon, "held_item", None)
        if isinstance(value, str):
            from pokemon.dex import ITEMDEX
            return ITEMDEX.get(cls.key(value)) or ITEMDEX.get(cls.key(value).capitalize()) or value
        return value

    @staticmethod
    def terrain(pokemon):
        """Read the field, with fallback for standalone callback tests."""
        field = getattr(getattr(pokemon, "battle", None), "field", None)
        return getattr(field, "terrain", "") if field is not None else getattr(pokemon, "terrain", "")

    @staticmethod
    def party(pokemon):
        """Read the holder's whole battle roster, including benched members."""
        battle = getattr(pokemon, "battle", None)
        participant_for = getattr(battle, "participant_for", None)
        participant = participant_for(pokemon) if callable(participant_for) else None
        return list(getattr(participant, "pokemons", None) or getattr(pokemon, "party", None) or [pokemon])

    @staticmethod
    def speed(pokemon):
        """Use the same stages and effect modifiers as action ordering."""
        from .utils import get_modified_stat

        speed = get_modified_stat(pokemon, "speed")
        battle = getattr(pokemon, "battle", None)
        if battle is not None and hasattr(battle, "runEvent"):
            modified = battle.runEvent("ModifySpe", pokemon, None, None, speed)
            if isinstance(modified, (int, float)) and not isinstance(modified, bool):
                speed = modified
        return max(1, int(speed))

    @classmethod
    def weight(cls, pokemon):
        """Apply the current weight hook at weight-based move consumers."""
        weight = getattr(pokemon, "weightkg", None)
        if weight is None:
            lookup = getattr(pokemon, "_lookup_species_entry", None)
            entry = lookup(str(getattr(pokemon, "species", None) or getattr(pokemon, "name", ""))) if callable(lookup) else None
            weight = (getattr(entry, "raw", {}) or {}).get("weightkg", .1)
        weight = max(.1, float(weight or .1))
        state = (getattr(pokemon, "volatiles", {}) or {}).get("autotomize", {})
        reductions = state.get("layers", 0) if isinstance(state, dict) else int(bool(state))
        if not reductions and (getattr(pokemon, "tempvals", {}) or {}).get("autotomize"):
            reductions = 1  # Legacy battle checkpoints tracked only one use.
        weight = max(.1, weight - 100 * max(0, int(reductions)))
        ability = cls.ability(pokemon)
        if hasattr(ability, "call"):
            modified = ability.call("onModifyWeight", weight, pokemon=pokemon)
            if isinstance(modified, (int, float)) and not isinstance(modified, bool):
                weight = modified
        item = cls.item(pokemon)
        if hasattr(item, "call"):
            modified = item.call("onModifyWeight", weight, pokemon=pokemon)
            if isinstance(modified, (int, float)) and not isinstance(modified, bool):
                weight = modified
        return max(.1, float(weight))
