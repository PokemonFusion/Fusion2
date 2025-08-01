"""Utilities for generating Pokémon instances from dex data."""

from dataclasses import dataclass
import re
import random
from typing import Dict, List, Optional

from .dex import POKEDEX, MOVEDEX
from .data.learnsets.learnsets import LEARNSETS
from .dex.entities import Stats, Pokemon as SpeciesPokemon


# Mapping for numeric dex-number lookups
POKEDEX_BY_NUM = {mon.num: mon for mon in POKEDEX.values()}


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


def get_gender(
    ratio: Optional[Dict[str, float]] = None, single: Optional[str] = None
) -> str:
    """Return a gender based on ratio or a single-gender value."""
    if single:
        if single in {"M", "F", "N"}:
            return single

    if ratio is None:
        # default 50/50 when no ratio and no single gender
        ratio = {"M": 0.5, "F": 0.5}

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


def choose_wild_moves(species_name: str, level: int, *, allow_special: bool = False) -> List[str]:
    """Return up to four moves for a wild Pokémon.

    The moves are chosen from level-up moves learned at or before the given
    level.  STAB and higher-level moves are preferred.  If ``allow_special`` is
    True, there is a small chance an egg or machine move is included.
    """

    key = species_name.lower()
    species = POKEDEX.get(key)
    if not species:
        try:
            num = int(species_name)
        except (TypeError, ValueError):
            return []
        species = POKEDEX_BY_NUM.get(num)
        if species:
            key = species.name.lower()
        else:
            return []

    types = [t.lower() for t in species.types]

    data = LEARNSETS.get(key)
    if not data:
        return ["Struggle"]

    learnset = data.get("learnset", {})
    level_moves: List[tuple[int, str]] = []
    for move, codes in learnset.items():
        learned_at: Optional[int] = None
        for code in codes:
            m = _LEVEL_CODE.match(code)
            if not m:
                continue
            lvl = int(m.group("level"))
            if lvl <= level and (learned_at is None or lvl > learned_at):
                learned_at = lvl
        if learned_at is not None:
            level_moves.append((learned_at, move))

    if not level_moves:
        return ["Struggle"]

    # Sort by level descending for recency
    level_moves.sort(key=lambda x: x[0], reverse=True)

    def is_stab(mv: str) -> bool:
        md = MOVEDEX.get(mv.lower())
        return bool(md and md.type and md.type.lower() in types)

    def is_damaging(mv: str) -> bool:
        md = MOVEDEX.get(mv.lower())
        if not md:
            return False
        if md.category == "Status":
            return False
        try:
            return int(md.power) > 0
        except (TypeError, ValueError):
            return False

    stab_moves = [mv for _, mv in level_moves if is_stab(mv)]
    other_moves = [mv for _, mv in level_moves if not is_stab(mv)]

    moves: List[str] = []
    for mv in stab_moves:
        if mv not in moves:
            moves.append(mv)
        if len(moves) >= 4:
            break
    if len(moves) < 4:
        for mv in other_moves:
            if mv not in moves:
                moves.append(mv)
            if len(moves) >= 4:
                break

    if allow_special and random.random() < 0.05:
        special_pool: List[str] = []
        for move, codes in learnset.items():
            for code in codes:
                if code.endswith("M") or code.endswith("E"):
                    special_pool.append(move)
                    break
        if special_pool:
            special_move = random.choice(special_pool)
            if special_move not in moves:
                if len(moves) >= 4:
                    moves[-1] = special_move
                else:
                    moves.append(special_move)

    def has_damaging(ms: List[str]) -> bool:
        return any(is_damaging(m) for m in ms)

    if not has_damaging(moves):
        fallback = "Tackle" if "tackle" in MOVEDEX else "Struggle"
        if moves:
            moves[0] = fallback
        else:
            moves = [fallback]

    return moves[:4]


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
    species = POKEDEX.get(species_name.lower())
    if not species:
        try:
            species = POKEDEX_BY_NUM.get(int(species_name))
        except (TypeError, ValueError):
            species = None
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
    ratio_dict = None
    if species.gender_ratio:
        ratio_dict = {"M": species.gender_ratio.M, "F": species.gender_ratio.F}
    gender = get_gender(ratio_dict, getattr(species, "gender", None))

    moves = get_valid_moves(species.name, level)
    if not moves:
        moves = ["Flail"]
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

