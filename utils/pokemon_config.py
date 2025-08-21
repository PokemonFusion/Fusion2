"""Configuration constants for Pokémon spawning."""

# Rarity weight mapping used for spawn rolls
RARITY_WEIGHTS = {
	"common": 50,
	"uncommon": 25,
	"rare": 10,
	"epic": 5,
	"legendary": 1,
}

# Level ranges mapped to tier names
TIERS = {
	"T1": (5, 15),
	"T2": (10, 25),
	"T3": (20, 35),
	"T4": (30, 50),
	"T5": (45, 65),
	"T6": (60, 80),
	"T7": (75, 90),
	"T8": (85, 100),
}
