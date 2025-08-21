import csv
import json
import unicodedata
from pathlib import Path
import sys

# Add repository root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from pokemon.dex.pokedex import pokedex

def to_identifier(name: str) -> str:
    """Convert a Pok\xe9mon name to the identifier style used by the CSV."""
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.lower().replace(' ', '-')
    for ch in ("'", '.', ':', '_', '’'):
        name = name.replace(ch, '')
    name = name.replace('♀', '-f').replace('♂', '-m')
    return name

# Load catch data from CSV
catch_data = {}
with open(Path(__file__).resolve().parents[3] / 'pokemon' / 'data' / 'pokemon_species.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        catch_data[row['identifier']] = {
            'catchRate': int(row['capture_rate']),
            'baseHappiness': int(row['base_happiness']),
        }

# Build mapping for all pokedex entries
result = {}
for name, data in pokedex.items():
    base = data.get('baseSpecies', name)
    identifier = to_identifier(base)
    if identifier in catch_data:
        result[name] = catch_data[identifier]

output_path = Path(__file__).resolve().parents[3] / 'pokemon' / 'dex' / 'catch_rates.py'
with open(output_path, 'w') as f:
    f.write('CATCH_INFO = ')
    json.dump(result, f, indent=4, sort_keys=True)
    f.write('\n')

print(f"Wrote {len(result)} entries to {output_path}")
