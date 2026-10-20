"""Transient, checkpoint-safe Illusion appearance without owned identity writes."""


class BattleAppearance:
    """Keep the disguise in the holder's effect state and restore only runtime fields."""

    @staticmethod
    def illusion(pokemon):
        state = (getattr(pokemon, "ability_state", {}) or {}).get("illusion")
        return state if isinstance(state, dict) else None

    @classmethod
    def disguise(cls, pokemon, other):
        if other is None or other is pokemon or cls.illusion(pokemon):
            return False
        state = {"species": str(other.species), "name": other.name,
                 "gender": getattr(other, "gender", "N"), "original_name": pokemon.name,
                 "original_gender": getattr(pokemon, "gender", "N")}
        pokemon.ability_state["illusion"] = state
        pokemon.name, pokemon.gender = state["name"], state["gender"]
        return True

    @classmethod
    def restore(cls, pokemon):
        state = cls.illusion(pokemon)
        if state:
            pokemon.name = state["original_name"]
            pokemon.gender = state["original_gender"]
            pokemon.ability_state.pop("illusion", None)
            return True
        return False
