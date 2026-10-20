"""Persist weather/terrain highest-stat activation across battle checkpoints."""

from .effect_context import EffectContext


class HighestStatActivation:
    """Keep selected stat and Booster Energy lifetime in bounded ability state."""

    stats = (("atk", "attack"), ("def", "defense"), ("spa", "special_attack"),
             ("spd", "special_defense"), ("spe", "speed"))

    def __init__(self, name):
        self.name = name

    def state(self, pokemon):
        """Return a serializable per-holder activation mapping."""
        state = getattr(pokemon, "abilityState", None)
        if not isinstance(state, dict):
            state = {}
            pokemon.abilityState = state
        return state.setdefault(self.name, {})

    def choose_stat(self, pokemon):
        """Choose actual stage-adjusted stats with the canonical tie order."""
        from .utils import get_modified_stat

        return max(self.stats, key=lambda pair: get_modified_stat(pokemon, pair[1]))[0]

    def activate(self, pokemon):
        """Start, retain or end a field boost; consume Booster Energy once."""
        if pokemon is None:
            return
        state = self.state(pokemon)
        if state.get("from_booster"):
            return
        weather = getattr(pokemon, "effective_weather", lambda: "")()
        active = (weather in {"sunnyday", "desolateland"} if self.name == "protosynthesis"
                  else EffectContext.terrain(pokemon) == "electricterrain")
        if active:
            if not state.get("active"):
                state.update(active=True, stat=self.choose_stat(pokemon), from_booster=False)
            return
        state.clear()
        item = EffectContext.item(pokemon)
        if EffectContext.key(item) != "boosterenergy":
            return
        battle = getattr(pokemon, "battle", None)
        if battle is not None:
            if not battle.use_item(pokemon, item, source=pokemon, effect="ability:" + self.name):
                return
            if not battle.remove_item(pokemon, source=pokemon, effect="ability:" + self.name, used=True):
                return
        else:
            pokemon.item = None
            if hasattr(pokemon, "held_item"):
                pokemon.held_item = ""
        state.update(active=True, stat=self.choose_stat(pokemon), from_booster=True)

    def modify(self, value, pokemon, stat):
        """Apply only the selected stat modifier and preserve inactive values."""
        if pokemon is None or getattr(pokemon, "ability_suppressed", False):
            return value
        state = self.state(pokemon)
        if state.get("active") and state.get("stat") == stat:
            return int(value * (1.5 if stat == "spe" else 1.3))
        return value

    def end(self, pokemon):
        """Discard activation when the holder's ability ends or it leaves."""
        if pokemon is not None:
            self.state(pokemon).clear()
