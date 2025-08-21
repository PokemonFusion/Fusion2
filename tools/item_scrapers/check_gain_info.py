import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from pokemon.dex.pokedex import pokedex
from pokemon.dex.exp_ev_yields import GAIN_INFO

missing = [name for name in pokedex if name not in GAIN_INFO]

if missing:
    print("Missing gain data for", len(missing), "pokemon:")
    for m in missing:
        print(m)
else:
    print("All pokemon have gain data.")
