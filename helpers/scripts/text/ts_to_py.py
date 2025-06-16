from __future__ import annotations
import re
import json
import json5
from pathlib import Path
import pprint

BASE_DIR = Path(__file__).parent
TS_DIR = BASE_DIR / 'ts'
JSON_DIR = BASE_DIR / 'json'
POKEMON_TEXT_DIR = BASE_DIR.parents[2] / 'pokemon' / 'data' / 'text'

HEADER_RE = re.compile(r'^export const \w+Text:[^=]+=\s*{', re.MULTILINE)


def convert_ts(filename: str) -> None:
    ts_path = TS_DIR / f'{filename}.ts'
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
    with (JSON_DIR / f'{filename}.json').open('w') as f:
        json.dump(data, f, indent=4)

    # Write Python dictionary into pokemon data folder
    POKEMON_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    const_name = f'{filename.upper()}_TEXT'
    pretty = pprint.pformat(data, indent=4, width=120, sort_dicts=False)
    with (POKEMON_TEXT_DIR / f'{filename}.py').open('w') as f:
        f.write(f'{const_name} = ' + pretty + '\n')

    print(f'Processed {filename}')


def main() -> None:
    for name in ['abilities', 'default', 'items', 'moves', 'pokedex']:
        convert_ts(name)


if __name__ == '__main__':
    main()
