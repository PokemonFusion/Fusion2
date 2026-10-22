"""Explicit, bounded PF2 equivalents for reviewed item evolution rules."""

from pokemon.names import normalize_name


class KingambitEvolution:
    """Admit only the reviewed native transition with private server evidence."""

    condition = "Defeat 3 Bisharp leading Pawniard and level-up"

    @classmethod
    def eligible(cls, source, target, ready):
        """Leave all other conditions/forms fail-closed and consume no item."""
        return bool(
            ready is True and normalize_name(source.name) == "bisharp"
            and normalize_name(target.name) == "kingambit"
            and not source.raw.get("forme") and not source.raw.get("baseSpecies")
            and not target.raw.get("forme") and not target.raw.get("baseSpecies")
            and target.raw.get("evoType") == "other"
            and target.raw.get("evoCondition") == cls.condition
            and target.raw.get("evoItem") is None
        )


class PeatBlockEvolution:
    """Replace only ordinary Ursaluna's lunar condition with explicit bag use."""

    item = "Peat Block"
    condition = "Peat Block when there's a full moon"

    @classmethod
    def eligible(cls, source, target, item):
        """Reject other forms, item identities and unreviewed dex metadata."""
        return bool(
            normalize_name(source.name) == "ursaring"
            and normalize_name(target.name) == "ursaluna"
            and normalize_name(item) == normalize_name(cls.item)
            and not source.raw.get("forme")
            and not target.raw.get("forme")
            and not source.raw.get("baseSpecies")
            and not target.raw.get("baseSpecies")
            and target.raw.get("evoType") == "other"
            and target.raw.get("evoCondition") == cls.condition
            and target.raw.get("evoItem") is None
        )


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
