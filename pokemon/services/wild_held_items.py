"""A single opt-in authored wild held-item source, independent of species metadata."""

from pokemon.names import normalize_name


class WildHeldItems:
    """Accept only native Rattata / Oran Berry with an explicit integer chance."""

    @staticmethod
    def select(species, entry, rng):
        """Return a real held item only for the reviewed complete authoring tuple."""
        chance = entry.get("held_item_chance", 0)
        if (normalize_name(species) != "rattata"
                or normalize_name(entry.get("held_item")) != "oranberry"
                or type(chance) is not int or not 0 <= chance <= 100):
            return ""
        return "Oran Berry" if chance and rng.randint(1, 100) <= chance else ""
