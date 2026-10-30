"""Guard reactive uses and checkpoint item histories without live object graphs."""

from collections.abc import Mapping, MutableSequence

from .effect_context import EffectContext


class ReactiveItemConsumption:
    """Reuse eating/UseItem gates and the engine's single removal notification."""

    @staticmethod
    def battle_for(pokemon, *, allow_fainted=False):
        """Require an active, effective holder; retaliation berries allow a KO."""
        battle = getattr(pokemon, "battle", None)
        if (battle is None or EffectContext.item(pokemon) is None
                or (not allow_fainted and getattr(pokemon, "hp", 0) <= 0)):
            return None
        participant = battle.participant_for(pokemon)
        return battle if participant and pokemon in participant.active else None

    @classmethod
    def eat(cls, pokemon, *, source=None, effect=None, allow_fainted=False):
        """Run the real berry gate and normal eating history exactly once."""
        battle = cls.battle_for(pokemon, allow_fainted=allow_fainted)
        return bool(battle and battle.eat_item(pokemon, source=source, effect=effect))

    @classmethod
    def use(cls, pokemon, *, source=None, effect=None):
        """Use a non-berry through UseItem then the existing used-removal path."""
        battle = cls.battle_for(pokemon)
        if not battle or not battle.use_item(pokemon, source=source, effect=effect):
            return False
        if not battle.remove_item(pokemon, source=source, effect=effect, used=True):
            return False
        ItemUseHistory.supersede_berry(pokemon)
        return True


class ItemUseHistory:
    """Persist named recovery references and prevent restoring one use twice."""

    REFERENCES = ("last_used_item", "last_consumed_item_obj", "consumed_item",
                  "consumed_berry", "berry_consumed")
    NAMES = ("last_item", "last_consumed_item", "last_removed_item")

    @staticmethod
    def item_name(value):
        """Keep only an item's textual identity, never a callback/ORM graph."""
        return str(getattr(value, "name", value)) if value else None

    @staticmethod
    def item(value):
        """Resolve explicit checkpoint references; unknown identities refuse."""
        if value is None:
            return None
        from pokemon.dex import ITEMDEX
        from pokemon.names import resolve_dex_entry

        if not isinstance(value, str) or not value:
            raise ValueError("Invalid item-use history requires battle recovery.")
        item = resolve_dex_entry(ITEMDEX, value)
        if item is None:
            raise ValueError("Unknown item-use history requires battle recovery.")
        return item

    @classmethod
    def freeze(cls, pokemon):
        """Store independent recovery slots plus the lifetime berry marker."""
        return {"version": 1, "ate_berry": bool(getattr(pokemon, "ate_berry", False)
                                               or getattr(pokemon, "consumed_berry", False)),
                **{key: cls.item_name(getattr(pokemon, key, None))
                   for key in cls.REFERENCES + cls.NAMES}}

    @classmethod
    def restore(cls, pokemon, payload):
        """Legacy absent histories stay empty; explicit malformed data refuses."""
        if payload is None:
            return
        if (not isinstance(payload, Mapping) or type(payload.get("version")) is not int
                or payload.get("version") != 1 or type(payload.get("ate_berry")) is not bool
                or set(payload) != {"version", "ate_berry", *cls.REFERENCES, *cls.NAMES}):
            raise ValueError("Invalid item-use history requires battle recovery.")
        values = {key: cls.item(payload[key]) for key in cls.REFERENCES}
        for key in cls.NAMES:
            value = payload[key]
            if value is not None and not isinstance(value, str):
                raise ValueError("Invalid item-use history requires battle recovery.")
            values[key] = value
        for key, value in values.items():
            setattr(pokemon, key, value)
        pokemon.ate_berry = payload["ate_berry"]

    @classmethod
    def recovered(cls, pokemon, *, retire_side=True):
        """Retire every recovery alias after receiving the one consumed copy."""
        item = (getattr(pokemon, "last_used_item", None) or getattr(pokemon, "berry_consumed", None)
                or getattr(pokemon, "consumed_berry", None))
        used = getattr(getattr(pokemon, "side", None), "used_items", [])
        if retire_side and item:
            for index in range(len(used) - 1, -1, -1):
                if EffectContext.key(used[index]) == EffectContext.key(item):
                    used.pop(index)
                    break
        pokemon.last_used_item = None
        cls.supersede_berry(pokemon)

    @staticmethod
    def supersede_berry(pokemon):
        """Retire the old berry recovery slot while retaining lifetime eating."""
        pokemon.ate_berry = bool(getattr(pokemon, "ate_berry", False)
                                 or getattr(pokemon, "consumed_berry", False))
        pokemon.consumed_berry = None
        pokemon.berry_consumed = None

    @staticmethod
    def recovery_owners(side, item):
        """Find explicit current recovery owners; ambiguous ledgers cannot grant."""
        owners = []
        for mon in getattr(side, "pokemons", None) or getattr(side, "active", []):
            history = getattr(mon, "last_used_item", None) or getattr(mon, "berry_consumed", None)
            if history and EffectContext.key(history) == EffectContext.key(item) and mon not in owners:
                owners.append(mon)
        return owners

    @classmethod
    def freeze_sides(cls, battle):
        """Save the ordinary side ledger as item identities, once per side."""
        return {getattr(part, "team", None) or ("A" if i == 0 else "B"):
                [cls.item_name(item) for item in getattr(getattr(part, "side", None), "used_items", [])]
                for i, part in enumerate(battle.participants)}

    @classmethod
    def restore_sides(cls, battle, payload):
        """Rebuild the side ledger without replaying consumption callbacks."""
        if not isinstance(payload, Mapping) or any(key not in {"A", "B"} for key in payload):
            raise ValueError("Invalid used-item side history requires recovery.")
        restored = {}
        for key, values in payload.items():
            if (not isinstance(values, (list, tuple, MutableSequence))
                    or any(not isinstance(value, str) or not value for value in values)):
                raise ValueError("Invalid used-item side history requires recovery.")
            restored[key] = [cls.item(value) for value in values]
        for i, part in enumerate(battle.participants):
            key = getattr(part, "team", None) or ("A" if i == 0 else "B")
            if key in restored:
                part.side.used_items = list(restored[key])
