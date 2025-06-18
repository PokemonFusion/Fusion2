"""Utilities for generating Pokémon instances from dex data."""

from dataclasses import dataclass
import re
import random
from typing import Dict, List, Optional

from .dex import POKEDEX
from .data.learnsets.learnsets import LEARNSETS
from .dex.entities import Stats, Pokemon as SpeciesPokemon


@dataclass
class PokemonInstance:
    """A generated Pokémon with stats, moves and other metadata."""

    species: SpeciesPokemon
    level: int
    ivs: Stats
    stats: Stats
    moves: List[str]
    ability: str
    gender: str
    nature: str


# --- Helper functions -----------------------------------------------------

def roll_ivs() -> Stats:
    """Return random IVs between 0 and 31 for each stat."""
    return Stats(
        hp=random.randint(0, 31),
        atk=random.randint(0, 31),
        def_=random.randint(0, 31),
        spa=random.randint(0, 31),
        spd=random.randint(0, 31),
        spe=random.randint(0, 31),
    )


def calculate_stat(base: int, iv: int, level: int, *, is_hp: bool = False, modifier: float = 1.0) -> int:
    """Calculate a Pokémon stat from base value, IV and level."""
    if is_hp:
        return int(((2 * base + iv) * level) / 100) + level + 10
    stat = int(((2 * base + iv) * level) / 100) + 5
    stat = int(stat * modifier)
    return stat


def get_gender(ratio: Optional[Dict[str, float]]) -> str:
    """Return a gender based on the species gender ratio."""
    if ratio is None:
        return "N"
    if ratio.get("M") == 0 and ratio.get("F") == 0:
        return "N"
    if ratio.get("M") == 1:
        return "M"
    if ratio.get("F") == 1:
        return "F"
    r = random.random()
    female_ratio = ratio.get("F", 0.5)
    return "F" if r < female_ratio else "M"


_LEVEL_CODE = re.compile(r"(?P<gen>\d+)L(?P<level>\d+)")

def get_valid_moves(species_name: str, level: int) -> List[str]:
    """Return a list of moves learnable at or below the given level."""
    key = species_name.lower()
    data = LEARNSETS.get(key)
    if not data:
        return []

    learned: List[tuple[int, int, str]] = []
    learnset = data.get("learnset", {})
    for move, codes in learnset.items():
        for code in codes:
            m = _LEVEL_CODE.match(code)
            if not m:
                continue
            lvl = int(m.group("level"))
            if lvl <= level:
                gen = int(m.group("gen"))
                learned.append((gen, lvl, move))
                break
    learned.sort(key=lambda x: (-x[0], -x[1]))
    moves = []
    for _, _, mv in learned:
        if mv not in moves:
            moves.append(mv)
    return moves


def get_random_ability(abilities: Dict[str, str]) -> str:
    """Choose a random ability from the abilities dict."""
    if not abilities:
        return ""
    return random.choice(list(abilities.values()))


NATURES: Dict[str, tuple[Optional[str], Optional[str]]] = {
    "Hardy": (None, None),
    "Lonely": ("atk", "def"),
    "Brave": ("atk", "spe"),
    "Adamant": ("atk", "spa"),
    "Naughty": ("atk", "spd"),
    "Bold": ("def", "atk"),
    "Docile": (None, None),
    "Relaxed": ("def", "spe"),
    "Impish": ("def", "spa"),
    "Lax": ("def", "spd"),
    "Timid": ("spe", "atk"),
    "Hasty": ("spe", "def"),
    "Serious": (None, None),
    "Jolly": ("spe", "spa"),
    "Naive": ("spe", "spd"),
    "Modest": ("spa", "atk"),
    "Mild": ("spa", "def"),
    "Quiet": ("spa", "spe"),
    "Bashful": (None, None),
    "Rash": ("spa", "spd"),
    "Calm": ("spd", "atk"),
    "Gentle": ("spd", "def"),
    "Sassy": ("spd", "spe"),
    "Careful": ("spd", "spa"),
    "Quirky": (None, None),
}


# --- Main generation function --------------------------------------------

def generate_pokemon(species_name: str, level: int = 5) -> PokemonInstance:
    """Create a Pokémon instance from dex data."""
    species: Optional[SpeciesPokemon] = None
    for name, data in POKEDEX.items():
        if name.lower() == species_name.lower():
            species = data
            break
    if not species:
        raise ValueError(f"Species '{species_name}' not found in Pokedex")

    ivs = roll_ivs()

    nature = random.choice(list(NATURES.keys()))
    inc, dec = NATURES[nature]

    def mod(stat: str) -> float:
        if stat == inc:
            return 1.1
        if stat == dec:
            return 0.9
        return 1.0

    stats = Stats(
        hp=calculate_stat(species.base_stats.hp, ivs.hp, level, is_hp=True),
        atk=calculate_stat(species.base_stats.atk, ivs.atk, level, modifier=mod("atk")),
        def_=calculate_stat(species.base_stats.def_, ivs.def_, level, modifier=mod("def")),
        spa=calculate_stat(species.base_stats.spa, ivs.spa, level, modifier=mod("spa")),
        spd=calculate_stat(species.base_stats.spd, ivs.spd, level, modifier=mod("spd")),
        spe=calculate_stat(species.base_stats.spe, ivs.spe, level, modifier=mod("spe")),
    )

    ability = get_random_ability({k: v.name if hasattr(v, "name") else v for k, v in species.abilities.items()})
    gender = get_gender( {"M": species.gender_ratio.M, "F": species.gender_ratio.F} if species.gender_ratio else None)

    moves = get_valid_moves(species.name, level)
    if len(moves) > 4:
        moves = random.sample(moves, 4)

    return PokemonInstance(
        species=species,
        level=level,
        ivs=ivs,
        stats=stats,
        moves=moves,
        ability=ability,
        gender=gender,
        nature=nature,
    )

