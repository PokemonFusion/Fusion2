"""Simple object oriented loaders for Pokemon, moves and abilities."""
from pathlib import Path

from .baby_species import BABY_SPECIES
from .entities import (
    Ability,
    Condition,
    Item,
    Move,
    Pokemon,
    load_abilitydex,
    load_conditiondex,
    load_itemdex,
    load_movedex,
    load_pokedex,
)

BASE_PATH = Path(__file__).resolve().parents[2]

# Raw data files
INPUT_PATH = BASE_PATH / "helpers" / "scripts" / "input"
POKEDEX_PATH = BASE_PATH / "pokemon" / "dex" / "pokedex" / "__init__.py"
MOVEDEX_PATH = BASE_PATH / "pokemon" / "dex" / "movedex.py"
ABILITYDEX_PATH = BASE_PATH / "pokemon" / "dex" / "abilities" / "abilitiesdex.py"
ITEMDEX_PATH = BASE_PATH / "pokemon" / "dex" / "items" / "itemsdex.py"
CONDITIONDEX_PATH = BASE_PATH / "pokemon" / "dex" / "conditions.py"

try:
    ABILITYDEX = load_abilitydex(ABILITYDEX_PATH)
except Exception:
    ABILITYDEX = {}

POKEDEX = load_pokedex(POKEDEX_PATH, ABILITYDEX)

try:
    MOVEDEX = load_movedex(MOVEDEX_PATH)
except Exception:
    MOVEDEX = {}

try:
    ITEMDEX = load_itemdex(ITEMDEX_PATH)
except Exception:
    ITEMDEX = {}

try:
    CONDITIONDEX = load_conditiondex(CONDITIONDEX_PATH)
except Exception:
    CONDITIONDEX = {}

__all__ = [
    "Ability",
    "Move",
    "Pokemon",
    "Item",
    "POKEDEX",
    "MOVEDEX",
    "ABILITYDEX",
    "ITEMDEX",
    "CONDITIONDEX",
    "BABY_SPECIES",
]
