"""Canonical native identity for species-restricted held-item callbacks."""

from collections.abc import Mapping

from pokemon.names import normalize_name, resolve_dex_entry


class HeldItemIdentity:
    """Read real dex species/base species without consulting display names."""

    @classmethod
    def can_take_mega_stone(cls, item, pokemon):
        """Protect a compatible native holder, independent of the taking source.

        The reference Mega Stone hook's second argument is its holder. PF2
        names that argument ``pokemon`` and passes the thief separately. A
        compatible thief cannot protect a stone held by another species.
        """
        native = getattr(item, "mega_evolves", None)
        return not (native and cls.matches(pokemon, native, family=True))

    @staticmethod
    def species_key(value, *, family=False):
        """Resolve an exact known species, optionally to its canonical family."""
        from pokemon.dex import POKEDEX

        entry = resolve_dex_entry(POKEDEX, value)
        raw = entry if isinstance(entry, Mapping) else getattr(entry, "raw", {}) or {}
        name = raw.get("name")
        return normalize_name((raw.get("baseSpecies") or name) if family else name)

    @classmethod
    def matches(cls, pokemon, *species, family=False, untransformed=False):
        """Match native identity, with an optional current/untransformed guard.

        Most native bonuses survive Transform, whose runtime changes preserve
        ``base_species``. Ditto powders additionally require its current native
        form and an untransformed holder. Standalone adapters may supply a real
        ``species`` when no base exists, but a copied adapter cannot infer one.
        Unknown or empty native identities fail closed; nicknames never count.
        """
        if pokemon is None:
            return False
        transformed = bool(getattr(pokemon, "transformed", False))
        if untransformed and transformed:
            return False
        native = getattr(pokemon, "base_species", None)
        if native is None:
            if transformed:
                return False
            native = getattr(pokemon, "species", None)
        allowed = {normalize_name(name) for name in species}
        if cls.species_key(native, family=family) not in allowed:
            return False
        return (
            not untransformed
            or cls.species_key(getattr(pokemon, "species", None), family=family) in allowed
        )
