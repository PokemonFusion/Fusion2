"""Separate temporary copied slots from canonical learned moves and PP."""

import copy

from .effect_context import EffectContext


class BattleCopyState:
    """Use serializable slot backups and independent temporary move objects."""

    @staticmethod
    def _state(pokemon):
        return pokemon.tempvals.setdefault("copy_state", {"original_slots": {}})

    @staticmethod
    def _payload(move):
        return {"name": move.name, "pp": getattr(move, "pp", None), "priority": getattr(move, "priority", 0)}

    @staticmethod
    def _move(name, pp):
        from .battledata import Move
        move = Move(name)
        move.pp = pp
        return move

    @classmethod
    def _replace(cls, pokemon, index, name, pp):
        state = cls._state(pokemon)
        if index < len(pokemon.moves):
            state["original_slots"].setdefault(str(index), cls._payload(pokemon.moves[index]))
        else:
            state["original_slots"].setdefault(str(index), None)
        replacement = cls._move(name, pp)
        if index < len(pokemon.moves):
            pokemon.moves[index] = replacement
        else:
            pokemon.moves.append(replacement)

    @classmethod
    def temporary_index(cls, pokemon, move):
        """Identify the selected virtual slot before considering owned rows."""
        state = getattr(pokemon, "tempvals", {}).get("copy_state", {})
        originals = state.get("original_slots", {})
        selected = getattr(move, "_runtime_slot_index", None)
        if selected is None:
            selected = next((index for index, candidate in enumerate(getattr(pokemon, "moves", []))
                             if EffectContext.key(candidate) == EffectContext.key(move)), None)
        return selected if str(selected) in originals else None

    @classmethod
    def spend_pp(cls, pokemon, move, amount):
        """Return None for ordinary moves; virtual PP never updates owned slots."""
        index = cls.temporary_index(pokemon, move)
        if index is None:
            return None
        cached = pokemon.moves[index]
        current = getattr(cached, "pp", 0) or 0
        cached.pp = max(0, current - amount)
        move.pp = cached.pp
        return current - cached.pp

    @classmethod
    def mimic(cls, user, target):
        """Copy full base PP, independent of the target's remaining PP."""
        from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name

        copied = getattr(target, "last_move", None)
        if copied is None or getattr(user, "transformed", False):
            return False
        entry = _battle_move_from_name(copied.name)
        if entry is None or entry.raw.get("flags", {}).get("failmimic") or entry.raw.get("isZ") or entry.raw.get("isMax"):
            return False
        if any(EffectContext.key(move) == EffectContext.key(entry) for move in user.moves):
            return False
        index = next((index for index, move in enumerate(user.moves) if EffectContext.key(move) == "mimic"), None)
        if index is None:
            return False
        cls._replace(user, index, entry.name, entry.raw.get("pp", entry.pp))
        return True

    @classmethod
    def transform(cls, user, target, battle=None):
        """Copy non-HP combat attributes and virtual PP while preserving identity."""
        try:
            from .utils import get_modified_stat
        except ImportError:  # Reduced battle adapters may expose only base stats.
            def get_modified_stat(pokemon, stat, **kwargs):
                return getattr(pokemon.base_stats, stat)
        from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name

        if (user is target or getattr(user, "transformed", False) or getattr(target, "transformed", False)
                or getattr(target, "hp", 0) <= 0 or "substitute" in getattr(target, "volatiles", {})
                or getattr(user, "illusion", None) or getattr(target, "illusion", None)
                or getattr(user, "terastallized", None) == "Stellar"):
            return False
        state = cls._state(user)
        state["transform"] = {"species": str(user.species), "name": user.name, "types": list(user.types),
                              "ability": getattr(getattr(user, "ability", None), "name", getattr(user, "ability", None)),
                              "boosts": copy.deepcopy(user.boosts), "stat_overrides": copy.deepcopy(user.tempvals.get("stat_overrides", {})),
                              "weightkg": getattr(user, "weightkg", None), "move_count": len(user.moves),
                              "base_stats": {stat: getattr(user.base_stats, stat) for stat in
                                             ("hp", "attack", "defense", "special_attack", "special_defense", "speed")}}
        # Remember every original slot before changing the list length.
        for index, move in enumerate(user.moves):
            state["original_slots"].setdefault(str(index), cls._payload(move))
        copied = []
        for index, move in enumerate(target.moves):
            entry = _battle_move_from_name(move.name)
            base_pp = entry.raw.get("pp", entry.pp) if entry else 5
            state["original_slots"].setdefault(str(index), None)
            copied.append(cls._move(move.name, 1 if base_pp == 1 else 5))
        user.moves = copied
        user.tempvals["stat_overrides"] = {stat: get_modified_stat(target, stat, ignore_boosts=True)
                                           for stat in ("attack", "defense", "special_attack", "special_defense", "speed")}
        user.base_stats = copy.deepcopy(target.base_stats)
        user.base_stats.hp = state["transform"]["base_stats"]["hp"]
        user.boosts = copy.deepcopy(target.boosts)
        user.species, user.name, user.types = target.species, target.name, list(target.types)
        if hasattr(target, "weightkg"):
            user.weightkg = target.weightkg
        user.transformed = True
        target_ability = EffectContext.ability(target)
        if not (getattr(target_ability, "raw", {}) or {}).get("flags", {}).get("notransform"):
            if battle is not None:
                battle.set_ability(user, target.ability, source=target, is_from_forme_change=True, is_transform=True)
            else:
                user.ability = target.ability
        return True

    @classmethod
    def cleanup(cls, pokemon):
        """Restore only virtual slots and transformed attributes on leaving."""
        state = getattr(pokemon, "tempvals", {}).pop("copy_state", None)
        if not isinstance(state, dict):
            return
        from .battledata import Move
        original = state.get("original_slots", {})
        transform = state.get("transform")
        if transform:
            pokemon.moves = [Move.from_dict(original[str(index)]) for index in range(transform["move_count"])]
            pokemon.species, pokemon.name = transform["species"], transform["name"]
            pokemon.types, pokemon.boosts = list(transform["types"]), dict(transform["boosts"])
            if transform.get("base_stats"):
                pokemon.base_stats = copy.deepcopy(pokemon.base_stats)
                for stat, value in transform["base_stats"].items():
                    setattr(pokemon.base_stats, stat, value)
            pokemon.ability = transform["ability"]
            pokemon.ability_state = {"id": EffectContext.key(pokemon.ability)}
            if transform.get("weightkg") is not None:
                pokemon.weightkg = transform["weightkg"]
            if transform["stat_overrides"]:
                pokemon.tempvals["stat_overrides"] = transform["stat_overrides"]
            else:
                pokemon.tempvals.pop("stat_overrides", None)
            pokemon.transformed = False
        else:
            for index, payload in original.items():
                if payload is not None:
                    pokemon.moves[int(index)] = Move.from_dict(payload)

    @classmethod
    def sketch(cls, user, target):
        """Replace the actual Sketch slot permanently through its owned writer."""
        from pokemon.dex.functions.moves.damage_moves import _battle_move_from_name
        from pokemon.services.pokemon_refs import parse_pokemon_ref

        copied = getattr(target, "last_move", None)
        if copied is None or getattr(user, "transformed", False):
            return False
        entry = _battle_move_from_name(copied.name)
        if entry is None or entry.raw.get("flags", {}).get("nosketch") or entry.raw.get("isZ") or entry.raw.get("isMax"):
            return False
        if any(EffectContext.key(move) == EffectContext.key(entry) for move in user.moves):
            return False
        index = next((index for index, move in enumerate(user.moves) if EffectContext.key(move) == "sketch"), None)
        if index is None or cls.temporary_index(user, user.moves[index]) is not None:
            return False
        kind, identifier = parse_pokemon_ref(getattr(user, "model_id", None))
        if kind == "owned" and identifier:
            from pokemon.services.sketch import SketchWriter
            if not SketchWriter().replace(identifier, index + 1, entry.name):
                return False
        user.moves[index] = cls._move(entry.name, entry.raw.get("pp", entry.pp))
        return True
