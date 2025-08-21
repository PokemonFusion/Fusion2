import csv
import json
import sys
import unicodedata
from pathlib import Path

# Add repository root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from pokemon.dex.pokedex import pokedex


def to_identifier(name: str) -> str:
	"""Convert a Pokémon name to the identifier style used by the CSV."""
	name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
	name = name.lower().replace(" ", "-")
	for ch in ("'", ".", ":", "_", "’"):
		name = name.replace(ch, "")
	name = name.replace("♀", "-f").replace("♂", "-m")
	return name


# Load baby form info from CSV
babies = set()
with open(Path(__file__).resolve().parents[3] / "pokemon" / "data" / "pokemon_species.csv") as f:
	reader = csv.DictReader(f)
	for row in reader:
		if row.get("is_baby") == "1":
			babies.add(row["identifier"])

# Map to pokedex keys
result = []
for name, data in pokedex.items():
	base = data.get("baseSpecies", name)
	ident = to_identifier(base)
	if ident in babies:
		result.append(name)

output_path = Path(__file__).resolve().parents[3] / "pokemon" / "dex" / "baby_species.py"
with open(output_path, "w") as f:
	f.write("BABY_SPECIES = ")
	json.dump(sorted(result), f, indent=4)
	f.write("\n")

print(f"Wrote {len(result)} entries to {output_path}")
