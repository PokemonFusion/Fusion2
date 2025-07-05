import csv
import json
from pathlib import Path
import unicodedata
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

from pokemon.dex.pokedex import pokedex

# helper to convert species names to identifier style

def to_identifier(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.lower().replace(' ', '-')
    for ch in ("'", '.', ':', '_', '’'):
        name = name.replace(ch, '')
    name = name.replace('♀', '-f').replace('♂', '-m')
    return name


# load base experience values
base_exp = {}
with open(ROOT / 'pokemon' / 'data' / 'pokemon.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        base_exp[row['identifier']] = int(row['base_experience'])

# map stat ids to names
stat_names = {}
with open(ROOT / 'pokemon' / 'data' / 'stats.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sid = int(row['id'])
        if sid == 1:
            stat_names[sid] = 'hp'
        elif sid == 2:
            stat_names[sid] = 'atk'
        elif sid == 3:
            stat_names[sid] = 'def'
        elif sid == 4:
            stat_names[sid] = 'spa'
        elif sid == 5:
            stat_names[sid] = 'spd'
        elif sid == 6:
            stat_names[sid] = 'spe'

# build EV yields by identifier
id_to_name = {}
ev_yields = {}
with open(ROOT / 'pokemon' / 'data' / 'pokemon.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        id_to_name[int(row['id'])] = row['identifier']

with open(ROOT / 'pokemon' / 'data' / 'pokemon_stats.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = int(row['pokemon_id'])
        stat_id = int(row['stat_id'])
        effort = int(row['effort'])
        if effort:
            ident = id_to_name[pid]
            ev_yields.setdefault(ident, {})[stat_names[stat_id]] = effort

result = {}
for name in pokedex:
    ident = to_identifier(name)
    exp = base_exp.get(ident)
    evs = ev_yields.get(ident, {})
    if exp is not None:
        result[name] = {'exp': exp, 'evs': evs}

out_path = ROOT / 'pokemon' / 'dex' / 'exp_ev_yields.py'
with open(out_path, 'w') as f:
    f.write('GAIN_INFO = ')
    json.dump(result, f, indent=4, sort_keys=True)
    f.write('\n')

print(f'Wrote {len(result)} entries to {out_path}')
