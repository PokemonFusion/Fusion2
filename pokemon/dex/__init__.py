"""Simple object oriented loaders for Pokemon, moves and abilities."""
from pathlib import Path

from .entities import Ability, Move, Pokemon, load_abilitydex, load_movedex, load_pokedex

BASE_PATH = Path(__file__).resolve().parents[2]

# Raw data files
INPUT_PATH = BASE_PATH / "helpers" / "scripts" / "input"
POKEDEX_PATH = BASE_PATH / "pokemon" / "pokedex.py"
MOVEDEX_PATH = BASE_PATH / "pokemon" / "dex" / "combatdex.py"
ABILITYDEX_PATH = BASE_PATH / "pokemon" / "dex" / "abilities" / "abilitiesdex.py"

try:
    ABILITYDEX = load_abilitydex(ABILITYDEX_PATH)
except Exception:
    ABILITYDEX = {}

POKEDEX = load_pokedex(POKEDEX_PATH, ABILITYDEX)

try:
    MOVEDEX = load_movedex(MOVEDEX_PATH)
except Exception:
    MOVEDEX = {}

__all__ = [
    "Ability",
    "Move",
    "Pokemon",
    "POKEDEX",
    "MOVEDEX",
    "ABILITYDEX",
]
