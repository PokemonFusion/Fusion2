from __future__ import annotations

import json
import pprint
import re
from pathlib import Path

import json5

BASE_DIR = Path(__file__).parent
TS_DIR = BASE_DIR / 'ts'
JSON_DIR = BASE_DIR / 'json'
POKEMON_LEARNSET_DIR = BASE_DIR.parents[2] / 'pokemon' / 'data' / 'learnsets'

HEADER_RE = re.compile(r'^export const Learnsets:[^=]+=\s*{', re.MULTILINE)


def convert_ts() -> None:
    ts_path = TS_DIR / 'learnsets.ts'
    if not ts_path.exists():
        print(f'Missing {ts_path}')
        return

    text = ts_path.read_text()
    # Strip TypeScript export wrapper
    text = HEADER_RE.sub('{', text, count=1).strip()
    if text.endswith('};'):
        text = text[:-1]  # keep closing brace, drop semicolon
    # Remove trailing comma from the final entry if present
    text = re.sub(r',\s*$', '', text)

    # Parse using json5 to allow comments and trailing commas
    data = json5.loads(text)

    # Write JSON
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    with (JSON_DIR / 'learnsets.json').open('w') as f:
        json.dump(data, f, indent=4)

    # Write Python dictionary into pokemon data folder
    POKEMON_LEARNSET_DIR.mkdir(parents=True, exist_ok=True)
    pretty = pprint.pformat(data, indent=4, width=120, sort_dicts=False)
    with (POKEMON_LEARNSET_DIR / 'learnsets.py').open('w') as f:
        f.write('LEARNSETS = ' + pretty + '\n')

    print('Processed learnsets')


def main() -> None:
    convert_ts()


if __name__ == '__main__':
    main()
