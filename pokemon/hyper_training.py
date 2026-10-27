"""Persistent stat-only Hyper Training overlays, separate from genetic IVs."""

from collections.abc import Mapping

from pokemon.names import normalize_name
from pokemon.utils.boosts import STAT_KEY_MAP


class HyperTraining:
    """Share canonical training flags across owned stats and battle snapshots."""

    prefix = "hypertrained:"
    stats = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")
    labels = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")
    minimum_level = 50

    @classmethod
    def stat(cls, query):
        """Resolve a complete stat label/alias without guessing a prefix or index."""
        aliases = {normalize_name(name): stat for stat, label in zip(cls.stats, cls.labels)
                   for name in (stat, label)}
        aliases.update({"spatk": "special_attack", "spdef": "special_defense",
                        "defence": "defense", "specialdefence": "special_defense"})
        return aliases.get(normalize_name(query))

    @classmethod
    def canonical(cls, values):
        """Accept only known canonical snapshot keys, in stable stat order."""
        if not isinstance(values, (list, tuple, set, frozenset)):
            return []
        return [stat for stat in cls.stats if stat in values]

    @classmethod
    def trained(cls, pokemon):
        """Prefer persisted owned flags; battle objects carry only this overlay."""
        flags = getattr(pokemon, "flags", None)
        if flags is not None:
            return [stat for stat in cls.stats if cls.prefix + stat in flags]
        return cls.canonical(getattr(pokemon, "hyper_training", ()))

    @classmethod
    def effective(cls, ivs, pokemon):
        """Return a stat-calculation copy; never overwrite genetic IV storage."""
        trained = cls.trained(pokemon)
        if isinstance(ivs, Mapping):
            return {key: 31 if STAT_KEY_MAP.get(key, key) in trained else value
                    for key, value in ivs.items()}
        values = list(ivs)
        return [31 if index < len(cls.stats) and cls.stats[index] in trained else value
                for index, value in enumerate(values)]
