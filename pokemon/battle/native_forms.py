"""Calculated, reversible native battle forms without owned-species writes."""

from types import SimpleNamespace


class NativeBattleForm:
    """Retain ordinary identity and damage through native Terapagos forms."""

    @staticmethod
    def tera_shift(pokemon):
        """Change only native Terapagos, preserving damage rather than HP ratio."""
        if str(getattr(pokemon, "base_species", "")).split("-")[0] != "Terapagos":
            return False
        if str(pokemon.species) != "Terapagos" or getattr(pokemon, "transformed", False):
            return False
        return NativeBattleForm._change(pokemon, "Terapagos-Terastal", "Tera Shell")

    @staticmethod
    def can_tera_stellar(pokemon):
        """Only a native, untransformed Terastal Terapagos can enter Stellar."""
        native = str(getattr(pokemon, "base_species", "")).split("-")[0]
        return (native == "Terapagos" and str(pokemon.species) == "Terapagos-Terastal"
                and not getattr(pokemon, "transformed", False))

    @staticmethod
    def tera_stellar(pokemon):
        """Commit the native Stellar form without changing its owned identity."""
        if not NativeBattleForm.can_tera_stellar(pokemon):
            return False
        return NativeBattleForm._change(pokemon, "Terapagos-Stellar", "Teraform Zero")

    @staticmethod
    def _change(pokemon, species, ability, *, types=None):
        """Calculate a reversible form, preserving damage and the first backup."""
        from pokemon.dex.entities import Stats
        from pokemon.helpers.pokemon_helpers import get_max_hp, get_stats
        from pokemon.hyper_training import HyperTraining

        previous = {"species": str(pokemon.species), "name": pokemon.name,
                    "types": list(pokemon.types), "ability": str(getattr(pokemon.ability, "name", pokemon.ability)),
                    "max_hp": pokemon.max_hp}
        data = SimpleNamespace(species=species, level=pokemon.level,
                               ivs=pokemon.ivs, evs=pokemon.evs, nature=pokemon.nature,
                               hyper_training=HyperTraining.trained(pokemon))
        stats = get_stats(data)
        maximum = get_max_hp(data)
        if not stats or not maximum:
            return False
        pokemon.tempvals.setdefault("native_form", previous)
        damage = pokemon.max_hp - pokemon.hp
        pokemon.species = species
        if pokemon.name == previous["species"]:
            pokemon.name = pokemon.species
        pokemon.types = list(types) if types is not None else ["Normal"]
        pokemon.base_stats = Stats(**stats)
        pokemon.max_hp = maximum
        pokemon.hp = max(0, maximum - damage) if pokemon.hp > 0 else 0
        pokemon.setAbility(ability, is_from_forme_change=True)
        return True

    @staticmethod
    def restore(pokemon):
        """Revert only the runtime form and preserve the damage it received."""
        state = getattr(pokemon, "tempvals", {}).pop("native_form", None)
        if not state:
            return False
        from pokemon.dex.entities import Stats
        from pokemon.helpers.pokemon_helpers import get_stats

        damage = pokemon.max_hp - pokemon.hp
        conscious = pokemon.hp > 0
        for name in ("species", "name", "types", "ability", "max_hp"):
            setattr(pokemon, name, state[name])
        if getattr(pokemon, "terastallized", None):
            pokemon.tera_original_types = list(state["types"])
        pokemon.base_stats = Stats(**get_stats(pokemon))
        pokemon.hp = max(1, pokemon.max_hp - damage) if conscious else 0
        return True


class OgerponForm:
    """Native mask eligibility and reversible Ogerpon Tera transformations."""

    forms = {
        "Ogerpon": ("Grass", "Teal", "Defiant", "", "spe"),
        "Ogerpon-Wellspring": ("Water", "Wellspring", "Water Absorb", "wellspringmask", "spd"),
        "Ogerpon-Hearthflame": ("Fire", "Hearthflame", "Mold Breaker", "hearthflamemask", "atk"),
        "Ogerpon-Cornerstone": ("Rock", "Cornerstone", "Sturdy", "cornerstonemask", "def"),
    }

    @staticmethod
    def key(value):
        """Normalize actual named items without using a Pokemon's nickname."""
        return "".join(char for char in str(value).lower() if char.isalnum())

    @classmethod
    def native(cls, pokemon):
        """A copied species cannot unlock Ogerpon's native transformation."""
        return (str(getattr(pokemon, "base_species", "")).split("-")[0] == "Ogerpon"
                and not getattr(pokemon, "transformed", False))

    @classmethod
    def item_key(cls, pokemon):
        """Read the authoritative mask name from an item object or saved name."""
        item = getattr(pokemon, "item", None)
        raw = getattr(item, "raw", {}) or {}
        return cls.key(raw.get("name") or getattr(item, "name", item) or "")

    @classmethod
    def profile(cls, pokemon):
        """Return only a conscious native ordinary form with its required mask."""
        profile = cls.forms.get(str(getattr(pokemon, "species", "")))
        if not cls.native(pokemon) or not profile or getattr(pokemon, "hp", 0) <= 0:
            return None
        mask = cls.item_key(pokemon)
        masks = {row[3] for row in cls.forms.values() if row[3]}
        if profile[3] and mask != profile[3] or not profile[3] and mask in masks:
            return None
        return profile

    @classmethod
    def apply_mask(cls, pokemon):
        """Select a native ordinary mask form at entry, retaining its backup."""
        if (not cls.native(pokemon) or str(pokemon.species) not in cls.forms
                or getattr(pokemon, "terastallized", None) or getattr(pokemon, "hp", 0) <= 0):
            return False
        mask = cls.item_key(pokemon)
        for species, row in cls.forms.items():
            if row[3] and mask == row[3]:
                if str(pokemon.species) == species:
                    return False
                return NativeBattleForm._change(pokemon, species, row[2], types=["Grass", row[0]])
        return False

    @classmethod
    def terastallize(cls, pokemon, tera_type):
        """Install the matching Embody Aspect only on a committed native form."""
        profile = cls.profile(pokemon)
        if not profile or tera_type != profile[0]:
            return False
        typ, aspect = profile[:2]
        return NativeBattleForm._change(pokemon, f"Ogerpon-{aspect}-Tera",
                                        f"Embody Aspect ({aspect})", types=[typ])

    @classmethod
    def mask_matches(cls, pokemon, aspect):
        """Mask effects belong to their native form, including its Tera form."""
        return (cls.native(pokemon)
                and str(getattr(pokemon, "species", "")) in
                {f"Ogerpon-{aspect}", f"Ogerpon-{aspect}-Tera"})
