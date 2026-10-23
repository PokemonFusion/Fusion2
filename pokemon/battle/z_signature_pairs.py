"""Explicit signature mappings reviewed before release; no metadata expansion."""

from .z_profiles import ZProfile


CAPS = tuple(
    "Pikachu-" + form
    for form in ("Original", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola", "Partner")
)
FIVE_STATS = ("atk", "def", "spa", "spd", "spe")


def signature(crystal, source, name, power, move_type, category, native, **effects):
    """Keep the immutable holder/source/effect contract explicit in each row."""
    return ZProfile(
        crystal + " Z",
        source,
        name,
        power,
        move_type,
        category,
        kind="signature",
        native=tuple(native),
        **effects,
    )


SIGNATURE_PAIRS = (
    signature(
        "Aloraichium",
        "Thunderbolt",
        "Stoked Sparksurfer",
        175,
        "Electric",
        "Special",
        ("Raichu-Alola",),
        intrinsic="paralysis",
    ),
    signature(
        "Decidium",
        "Spirit Shackle",
        "Sinister Arrow Raid",
        180,
        "Ghost",
        "Physical",
        ("Decidueye",),
    ),
    signature(
        "Incinium",
        "Darkest Lariat",
        "Malicious Moonsault",
        180,
        "Dark",
        "Physical",
        ("Incineroar",),
        contact=True,
    ),
    signature(
        "Primarium", "Sparkling Aria", "Oceanic Operetta", 195, "Water", "Special", ("Primarina",)
    ),
    signature(
        "Pikanium",
        "Volt Tackle",
        "Catastropika",
        210,
        "Electric",
        "Physical",
        ("Pikachu",),
        contact=True,
    ),
    signature(
        "Pikashunium",
        "Thunderbolt",
        "10,000,000 Volt Thunderbolt",
        195,
        "Electric",
        "Special",
        CAPS,
        critical_stage=2,
    ),
    signature(
        "Snorlium",
        "Giga Impact",
        "Pulverizing Pancake",
        210,
        "Normal",
        "Physical",
        ("Snorlax",),
        contact=True,
    ),
    signature(
        "Mimikium",
        "Play Rough",
        "Let's Snuggle Forever",
        190,
        "Fairy",
        "Physical",
        ("Mimikyu", "Mimikyu-Totem"),
        contact=True,
    ),
    signature(
        "Eevium",
        "Last Resort",
        "Extreme Evoboost",
        0,
        "Normal",
        "Status",
        ("Eevee",),
        target="self",
        bonus=tuple((key, 2) for key in FIVE_STATS),
    ),
    signature(
        "Kommonium",
        "Clanging Scales",
        "Clangorous Soulblaze",
        185,
        "Dragon",
        "Special",
        ("Kommo-o", "Kommo-o-Totem"),
        target="allAdjacentFoes",
        sound=True,
        bypass_substitute=True,
        intrinsic="soulblaze",
        bonus=tuple((key, 1) for key in FIVE_STATS),
    ),
    signature(
        "Lycanium",
        "Stone Edge",
        "Splintered Stormshards",
        190,
        "Rock",
        "Physical",
        ("Lycanroc", "Lycanroc-Midnight", "Lycanroc-Dusk"),
        intrinsic="clearterrain",
    ),
    signature(
        "Mewnium",
        "Psychic",
        "Genesis Supernova",
        185,
        "Psychic",
        "Special",
        ("Mew",),
        intrinsic="psychicterrain",
    ),
    signature(
        "Lunalium",
        "Moongeist Beam",
        "Menacing Moonraze Maelstrom",
        200,
        "Ghost",
        "Special",
        ("Lunala",),
        ignore_ability=True,
    ),
    signature(
        "Solganium",
        "Sunsteel Strike",
        "Searing Sunraze Smash",
        200,
        "Steel",
        "Physical",
        ("Solgaleo",),
        contact=True,
        ignore_ability=True,
    ),
    signature(
        "Marshadium",
        "Spectral Thief",
        "Soul-Stealing 7-Star Strike",
        195,
        "Ghost",
        "Physical",
        ("Marshadow",),
        contact=True,
    ),
    signature(
        "Tapunium",
        "Nature's Madness",
        "Guardian of Alola",
        0,
        "Fairy",
        "Special",
        ("Tapu Koko", "Tapu Lele", "Tapu Bulu", "Tapu Fini"),
        intrinsic="guardian",
    ),
)
