"""Explicit, bounded PF2 equivalents for reviewed item evolution rules."""

from pokemon.names import normalize_name


class GimmighoulEvolution:
    """Admit the reviewed manual Chest-form, 999-bag-coin equivalent only."""

    item = "Gimmighoul Coin"
    quantity = 999
    condition = "Level up with 999 Coins in the bag"

    @classmethod
    def eligible(cls, source, target, item, level, ability):
        """Require exact native metadata and legal saved level/ability, never prose flags."""
        return bool(
            normalize_name(source.name) == "gimmighoul"
            and source.raw.get("baseForme") == "Chest"
            and not source.raw.get("forme") and not source.raw.get("baseSpecies")
            and normalize_name(target.name) == "gholdengo"
            and not target.raw.get("forme") and not target.raw.get("baseSpecies")
            and target.raw.get("evoType") == "other"
            and target.raw.get("evoCondition") == cls.condition
            and target.raw.get("evoItem") is None
            and normalize_name(item) == normalize_name(cls.item)
            and type(level) is int and 2 <= level <= 100
            and normalize_name(ability) == "rattled"
        )


class KubfuEvolution:
    """Select exactly one reviewed Urshifu branch with a real bag Scroll."""

    transitions = {
        "urshifu": ("Scroll of Darkness", "Defeat the Single Strike Tower",
                    {"baseForme": "Single-Strike", "baseSpecies": None, "forme": None}),
        "urshifurapidstrike": ("Scroll of Waters", "Defeat the Rapid Strike Tower",
                               {"baseForme": None, "baseSpecies": "Urshifu", "forme": "Rapid-Strike"}),
    }

    @classmethod
    def required_item(cls, target):
        """Expose a complete bag requirement without rewriting generated data."""
        rule = cls.transitions.get(normalize_name(target.name))
        return rule[0] if rule else None

    @classmethod
    def eligible(cls, source, target, item):
        """Reject mismatched items and any unreviewed source/form/condition."""
        rule = cls.transitions.get(normalize_name(target.name))
        return bool(
            rule and normalize_name(source.name) == "kubfu"
            and not source.raw.get("forme") and not source.raw.get("baseSpecies")
            and not source.raw.get("baseForme")
            and normalize_name(item) == normalize_name(rule[0])
            and target.raw.get("evoType") == "other"
            and target.raw.get("evoCondition") == rule[1]
            and target.raw.get("evoItem") is None
            and not target.raw.get("battleOnly") and not target.raw.get("changesFrom")
            and all(target.raw.get(field) == expected for field, expected in rule[2].items())
        )


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
