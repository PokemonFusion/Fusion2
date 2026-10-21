"""Explicit PF2 non-transfer equivalents for existing trade-held item rules."""

from pokemon.names import normalize_name


class TradeHeldEvolution:
    """Allow only reviewed source/target/item triples, never general trading."""

    transitions = (
        ("Clamperl", "Gorebyss", "Deep Sea Scale"),
        ("Clamperl", "Huntail", "Deep Sea Tooth"),
        ("Seadra", "Kingdra", "Dragon Scale"),
        ("Porygon2", "Porygon-Z", "Dubious Disc"),
        ("Electabuzz", "Electivire", "Electirizer"),
        ("Poliwhirl", "Politoed", "King's Rock"),
        ("Slowpoke", "Slowking", "King's Rock"),
        ("Magmar", "Magmortar", "Magmarizer"),
        ("Onix", "Steelix", "Metal Coat"),
        ("Scyther", "Scizor", "Metal Coat"),
        ("Nohface", "Kitsunoh", "Metal Coat"),
        ("Feebas", "Milotic", "Prism Scale"),
        ("Rhydon", "Rhyperior", "Protector"),
        ("Dusclops", "Dusknoir", "Reaper Cloth"),
        ("Spritzee", "Aromatisse", "Sachet"),
        ("Porygon", "Porygon2", "Up-Grade"),
        ("Swirlix", "Slurpuff", "Whipped Dream"),
    )

    @classmethod
    def eligible(cls, source, target, held_item):
        """Match actual held state and dex metadata; other predicates stay shared."""
        if target.raw.get("evoType") != "trade":
            return False
        identity = tuple(normalize_name(value) for value in (source.name, target.name, held_item))
        return (
            identity in {tuple(normalize_name(value) for value in row) for row in cls.transitions}
            and normalize_name(target.raw.get("evoItem") or "") == identity[2]
        )
