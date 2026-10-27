"""Temporary defensive typing for a useful ordinary Roost heal."""


class RoostTyping:
    """Keep the one-turn Flying removal reversible without overwriting later typing."""

    @staticmethod
    def start(pokemon):
        """Apply only after useful healing; Terastallized typing stays fixed."""
        if getattr(pokemon, "terastallized", False):
            return
        original = list(pokemon.types)
        if "Flying" not in original or "roost" in pokemon.volatiles:
            return
        temporary = [kind for kind in original if kind != "Flying"] or ["Normal"]
        pokemon.volatiles["roost"] = {
            "version": 1,
            "original_types": original,
            "temporary_types": temporary,
        }
        pokemon.types = list(temporary)

    @staticmethod
    def end(pokemon):
        """Restore only this effect's own unchanged projection, then discard its proof."""
        state = pokemon.volatiles.pop("roost", None)
        if not isinstance(state, dict) or state.get("version") != 1:
            return
        original, temporary = state.get("original_types"), state.get("temporary_types")
        if (
            isinstance(original, list)
            and original
            and all(isinstance(t, str) for t in original)
            and isinstance(temporary, list)
            and list(pokemon.types) == temporary
        ):
            pokemon.types = list(original)
