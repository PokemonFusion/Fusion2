"""Allowlisted Alcremie decoration policy, separate from battle species/forms."""

from pokemon.names import normalize_name, resolve_dex_entry


class AlcremieEvolution:
    """Use the seven existing Sweets and only cosmetic names in the local dex."""

    sweets = (
        "Berry Sweet", "Clover Sweet", "Flower Sweet", "Love Sweet",
        "Ribbon Sweet", "Star Sweet", "Strawberry Sweet",
    )
    form_prefix = "alcremie:form:"
    sweet_prefix = "alcremie:sweet:"

    @classmethod
    def sweet(cls, value):
        """Return one complete Sweet display name, rejecting partial/foreign items."""
        return next((name for name in cls.sweets if normalize_name(name) == normalize_name(value)), None)

    @staticmethod
    def forms():
        """Expose the base and declared cosmetics without introducing dex entries."""
        from pokemon.dex import POKEDEX

        base = resolve_dex_entry(POKEDEX, "Alcremie")
        if not base:
            return ()
        return (base.name, *base.raw.get("cosmeticFormes", ()))

    @classmethod
    def select(cls, target=None):
        """Resolve a complete allowed target; no target means Vanilla Cream."""
        target = target or "Alcremie"
        return next((name for name in cls.forms() if normalize_name(name) == normalize_name(target)), None)

    @classmethod
    def eligible(cls, source, target, held_item):
        """Recognize only the exact dex Sweet transition, never arbitrary 'other'."""
        return bool(
            normalize_name(source.name) == "milcery"
            and normalize_name(target.name) == "alcremie"
            and target.raw.get("evoType") == "other"
            and target.raw.get("evoCondition") == "spin while holding a Sweet"
            and cls.sweet(held_item)
        )

    @classmethod
    def decorate(cls, pokemon, form, sweet):
        """Write result metadata; these tags are never evolution eligibility."""
        if form not in cls.forms() or sweet not in cls.sweets:
            raise ValueError("Choose a supported Alcremie cream and Sweet.")
        flags = getattr(pokemon, "flags", [])
        pokemon.flags = [tag for tag in flags if not tag.startswith((cls.form_prefix, cls.sweet_prefix))] + [
            cls.form_prefix + form, cls.sweet_prefix + sweet,
        ]

    @classmethod
    def appearance(cls, pokemon):
        """Read one unambiguous pair of allowlisted persisted cosmetic values."""
        if normalize_name(getattr(pokemon, "species", "")) != "alcremie":
            return None
        flags = getattr(pokemon, "flags", [])
        if not isinstance(flags, (list, tuple)):
            return None
        forms = [tag.removeprefix(cls.form_prefix) for tag in flags if isinstance(tag, str) and tag.startswith(cls.form_prefix)]
        sweets = [tag.removeprefix(cls.sweet_prefix) for tag in flags if isinstance(tag, str) and tag.startswith(cls.sweet_prefix)]
        if len(forms) != 1 or len(sweets) != 1 or forms[0] not in cls.forms() or sweets[0] not in cls.sweets:
            return None
        return {"form": forms[0], "sweet": sweets[0]}

    @classmethod
    def describe(cls, pokemon):
        """Display only validated decorations on canonical Alcremie after reload."""
        appearance = cls.appearance(pokemon)
        if appearance is None:
            return None
        form, sweet = appearance.get("form"), appearance.get("sweet")
        cream = "Vanilla Cream" if form == "Alcremie" else form.removeprefix("Alcremie-").replace("-", " ")
        return f"{cream}; {sweet}"
