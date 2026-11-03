"""One authoritative positive-only field friendship modifier for EV berry feeding."""

from pokemon.names import normalize_name


class FieldFriendship:
    """Apply a reusable physical Bell only to the reviewed positive berry event."""

    @staticmethod
    def ev_berry_gain(pokemon, friendship):
        """Use the pre-feed tier, floor the Bell multiplier, then let the caller cap."""
        gain = 10 if friendship < 100 else 5 if friendship < 200 else 2
        return gain * 3 // 2 if normalize_name(pokemon.held_item) == "soothebell" else gain
