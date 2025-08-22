"""Utilities for generating Pokémon instances from dex data."""

from dataclasses import dataclass
import random
from typing import Dict, List, Optional

from ..dex import POKEDEX, MOVEDEX
from .learnsets.learnsets import LEARNSETS
from ..dex.entities import Stats, Pokemon as SpeciesPokemon


# Mapping for numeric dex-number lookups
POKEDEX_BY_NUM = {mon.num: mon for mon in POKEDEX.values()}


# Preprocess learnset level-up data at import time to avoid repeated parsing.
# The resulting structure maps ``species -> level -> {move: generation}``.
LEVEL_UP_LEARNSETS: Dict[str, Dict[int, Dict[str, int]]] = {}

for _name, _data in LEARNSETS.items():
    _learnset = _data.get("learnset", {})
    level_map: Dict[int, Dict[str, int]] = {}
    for _move, _codes in _learnset.items():
        for _code in _codes:
            if "L" not in _code:
                continue
            gen_part, level_part = _code.split("L", 1)
            if not gen_part.isdigit() or not level_part.isdigit():
                continue
            gen = int(gen_part)
            lvl = int(level_part)
            moves_at_level = level_map.setdefault(lvl, {})
            # Keep the highest generation for a given move/level pair
            existing_gen = moves_at_level.get(_move)
            if existing_gen is None or gen > existing_gen:
                moves_at_level[_move] = gen
    if level_map:
        LEVEL_UP_LEARNSETS[_name] = level_map


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


# Public exports from this module
__all__ = [
    "PokemonInstance",
    "generate_pokemon",
    "get_valid_moves",
    "choose_wild_moves",
    "NATURES",
]

# --- Helper functions -----------------------------------------------------

def roll_ivs(*, rng: Optional[random.Random] = None) -> Stats:
    """Return random IVs between 0 and 31 for each stat."""

    rng = rng or random
    return Stats(
        hp=rng.randint(0, 31),
        attack=rng.randint(0, 31),
        defense=rng.randint(0, 31),
        special_attack=rng.randint(0, 31),
        special_defense=rng.randint(0, 31),
        speed=rng.randint(0, 31),
    )


def calculate_stat(base: int, iv: int, level: int, *, is_hp: bool = False, modifier: float = 1.0) -> int:
    """Calculate a Pokémon stat from base value, IV and level."""
    if is_hp:
        return int(((2 * base + iv) * level) / 100) + level + 10
    stat = int(((2 * base + iv) * level) / 100) + 5
    stat = int(stat * modifier)
    return stat


def get_gender(
    ratio: Optional[Dict[str, float]] = None,
    single: Optional[str] = None,
    *,
    rng: Optional[random.Random] = None,
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
    rng = rng or random
    r = rng.random()
    female_ratio = ratio.get("F", 0.5)
    return "F" if r < female_ratio else "M"


def get_valid_moves(species_name: str, level: int) -> List[str]:
    """Return a list of moves learnable at or below the given level."""
    key = species_name.lower()
    level_map = LEVEL_UP_LEARNSETS.get(key)
    if not level_map:
        return []

    entries: List[tuple[int, int, str]] = []
    for lvl, moves in level_map.items():
        if lvl > level:
            continue
        for move, gen in moves.items():
            entries.append((gen, lvl, move))

    entries.sort(key=lambda x: (-x[0], -x[1]))
    moves: List[str] = []
    for _, _, mv in entries:
        if mv not in moves:
            moves.append(mv)
    return moves


def choose_wild_moves(
    species_name: str,
    level: int,
    *,
    allow_special: bool = False,
    seed: int | None = None,
) -> List[str]:
    """Return up to four moves for a wild Pokémon.

    The moves are chosen from level-up moves learned at or before the given
    level.  STAB and higher-level moves are preferred.  If ``allow_special`` is
    True, there is a small chance an egg or machine move is included.
    """

    rng = random.Random(seed)

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

    level_map = LEVEL_UP_LEARNSETS.get(key, {})
    if not level_map:
        return ["Struggle"]

    move_to_level: Dict[str, int] = {}
    for lvl in sorted(level_map):
        if lvl > level:
            break
        for move in level_map[lvl]:
            move_to_level[move] = lvl

    if not move_to_level:
        return ["Struggle"]

    level_moves: List[tuple[int, str]] = sorted(
        ((lvl, mv) for mv, lvl in move_to_level.items()), key=lambda x: x[0], reverse=True
    )

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

    if allow_special and rng.random() < 0.05:
        special_pool: List[str] = []
        learnset = LEARNSETS.get(key, {}).get("learnset", {})
        for move, codes in learnset.items():
            for code in codes:
                if code.endswith("M") or code.endswith("E"):
                    special_pool.append(move)
                    break
        if special_pool:
            special_move = rng.choice(special_pool)
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


def get_random_ability(abilities: Dict[str, str], *, rng: Optional[random.Random] = None) -> str:
    """Choose a random ability from the abilities dict."""

    if not abilities:
        return ""
    rng = rng or random
    return rng.choice(list(abilities.values()))


NATURES: Dict[str, tuple[Optional[str], Optional[str]]] = {
    "Hardy": (None, None),
    "Lonely": ("attack", "defense"),
    "Brave": ("attack", "speed"),
    "Adamant": ("attack", "special_attack"),
    "Naughty": ("attack", "special_defense"),
    "Bold": ("defense", "attack"),
    "Docile": (None, None),
    "Relaxed": ("defense", "speed"),
    "Impish": ("defense", "special_attack"),
    "Lax": ("defense", "special_defense"),
    "Timid": ("speed", "attack"),
    "Hasty": ("speed", "defense"),
    "Serious": (None, None),
    "Jolly": ("speed", "special_attack"),
    "Naive": ("speed", "special_defense"),
    "Modest": ("special_attack", "attack"),
    "Mild": ("special_attack", "defense"),
    "Quiet": ("special_attack", "speed"),
    "Bashful": (None, None),
    "Rash": ("special_attack", "special_defense"),
    "Calm": ("special_defense", "attack"),
    "Gentle": ("special_defense", "defense"),
    "Sassy": ("special_defense", "speed"),
    "Careful": ("special_defense", "special_attack"),
    "Quirky": (None, None),
}


# --- Main generation function --------------------------------------------

def generate_pokemon(
    species_name: str,
    level: int = 5,
    *,
    seed: int | None = None,
) -> PokemonInstance:
    """Create a Pokémon instance from dex data."""

    rng = random.Random(seed)

    species = POKEDEX.get(species_name.lower())
    if not species:
        try:
            species = POKEDEX_BY_NUM.get(int(species_name))
        except (TypeError, ValueError):
            species = None
    if not species:
        raise ValueError(f"Species '{species_name}' not found in Pokedex")

    ivs = roll_ivs(rng=rng)

    nature = rng.choice(list(NATURES.keys()))
    inc, dec = NATURES[nature]

    def mod(stat: str) -> float:
        if stat == inc:
            return 1.1
        if stat == dec:
            return 0.9
        return 1.0

    stats = Stats(
        hp=calculate_stat(species.base_stats.hp, ivs.hp, level, is_hp=True),
        attack=calculate_stat(
            species.base_stats.attack, ivs.attack, level, modifier=mod("attack")
        ),
        defense=calculate_stat(
            species.base_stats.defense, ivs.defense, level, modifier=mod("defense")
        ),
        special_attack=calculate_stat(
            species.base_stats.special_attack,
            ivs.special_attack,
            level,
            modifier=mod("special_attack"),
        ),
        special_defense=calculate_stat(
            species.base_stats.special_defense,
            ivs.special_defense,
            level,
            modifier=mod("special_defense"),
        ),
        speed=calculate_stat(
            species.base_stats.speed, ivs.speed, level, modifier=mod("speed")
        ),
    )

    ability = get_random_ability(
        {k: v.name if hasattr(v, "name") else v for k, v in species.abilities.items()},
        rng=rng,
    )
    ratio_dict = None
    if species.gender_ratio:
        ratio_dict = {"M": species.gender_ratio.M, "F": species.gender_ratio.F}
    gender = get_gender(ratio_dict, getattr(species, "gender", None), rng=rng)

    moves = choose_wild_moves(species.name, level, seed=seed)
    if not moves:
        moves = ["Flail"]
    if len(moves) > 4:
        moves = rng.sample(moves, 4)

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

