"""Separate genetic Nature from a reviewed mint's effective stat preference."""


class NatureTrainingError(ValueError):
    """Malformed genetics/training needs review, never random replacement stats."""


class NatureTraining:
    """One strict trained-state policy; breeding/evolution/flavors keep genetics."""

    natures = (
        "Hardy",
        "Lonely",
        "Brave",
        "Adamant",
        "Naughty",
        "Bold",
        "Docile",
        "Relaxed",
        "Impish",
        "Lax",
        "Timid",
        "Hasty",
        "Serious",
        "Jolly",
        "Naive",
        "Modest",
        "Mild",
        "Quiet",
        "Bashful",
        "Rash",
        "Calm",
        "Gentle",
        "Sassy",
        "Careful",
        "Quirky",
    )
    mint_names = tuple(
        name for name in natures if name not in {"Hardy", "Docile", "Bashful", "Quirky"}
    )

    @classmethod
    def validate_training(cls, value):
        """Accept only an absent preference or one of the21 exact trained values."""
        if value is None or value == "":
            return None
        if not isinstance(value, str) or value not in cls.mint_names:
            raise NatureTrainingError("Invalid saved mint training; ask staff to review it.")
        return str(value)

    @classmethod
    def genetic(cls, value, *, legacy_blank=False):
        """Validate saved genetics; old untrained blank stat callers retain neutral behavior.

        This compatibility fallback never writes/invents a saved genetic value.
        A mint request and any nonblank training require actual canonical genetics.
        """
        if legacy_blank and (value is None or value == ""):
            return "Hardy"
        if not isinstance(value, str) or value not in cls.natures:
            raise NatureTrainingError("Invalid saved genetic Nature; ask staff to review it.")
        return str(value)

    @classmethod
    def effective(cls, pokemon):
        """Resolve the stat modifier only, preserving the object's genetic field."""
        trained = cls.validate_training(getattr(pokemon, "trained_stat_nature", None))
        genetic = cls.genetic(getattr(pokemon, "nature", "Hardy"), legacy_blank=trained is None)
        return trained or genetic

    @classmethod
    def signature(cls, nature):
        """Use the project's existing modifiers, including neutral equivalence."""
        from pokemon.data.generation import NATURES

        return NATURES[cls.genetic(nature)]

    @classmethod
    def useful(cls, pokemon, requested):
        """A mint cannot hide invalid genetics or spend on an equivalent modifier."""
        cls.genetic(getattr(pokemon, "nature", None))
        target = cls.validate_training(requested)
        if target is None:
            raise NatureTrainingError("A mint must select its explicit trained stat Nature.")
        return cls.signature(cls.effective(pokemon)) != cls.signature(target)
