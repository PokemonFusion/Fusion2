import re
import json
import json5
from collections import defaultdict
from pathlib import Path

INPUT_PATH = Path('helpers/scripts/input/items.ts')
OUTPUT_DEX = Path('pokemon/dex/items/itemsdex.py')
OUTPUT_FUNCS = Path('pokemon/dex/items/functions/itemfuncs.py')

TS_HEADER_RE = re.compile(r"export const Items: import\([^)]+\)\.ItemDataTable = {")
NAME_RE = re.compile(r"\s*(\w+):\s*{")
FUNC_RE = re.compile(r"(\w+)\s*\([^)]*\)\s*{")


def load_ts(path: Path) -> str:
    text = path.read_text()
    text = TS_HEADER_RE.sub('{', text)
    text = re.sub(r"//.*", '', text)
    return text


def extract_entries(text: str) -> dict[str, str]:
    text = text.strip()
    if text.endswith('};'):
        text = text[:-2]
    if text.startswith('{'):
        text = text[1:]
    entries = {}
    pos = 0
    while pos < len(text):
        m = NAME_RE.match(text, pos)
        if not m:
            break
        name = m.group(1)
        start = m.end() - 1  # position of '{'
        brace = 1
        i = start + 1
        while i < len(text) and brace:
            if text[i] == '{':
                brace += 1
            elif text[i] == '}':
                brace -= 1
            i += 1
        block = text[start:i]
        entries[name] = block
        if i < len(text) and text[i] == ',':
            i += 1
        pos = i
    return entries


def process_block(name: str, block: str, placeholders: defaultdict[str, set[str]]):
    class_name = name.capitalize()
    result = ''
    idx = 0
    while idx < len(block):
        m = FUNC_RE.search(block, idx)
        if not m:
            result += block[idx:]
            break
        fn = m.group(1)
        start_fn = m.start()
        open_brace = m.end() - 1
        result += block[idx:start_fn] + f"{fn}: '{class_name}.{fn}'"
        brace = 1
        j = open_brace + 1
        while j < len(block) and brace:
            if block[j] == '{':
                brace += 1
            elif block[j] == '}':
                brace -= 1
            j += 1
        if j < len(block) and block[j] == ',':
            result += ','
            j += 1
        placeholders[class_name].add(fn)
        idx = j
    data = json5.loads(result)
    return class_name, data


def main() -> None:
    ts = load_ts(INPUT_PATH)
    raw_entries = extract_entries(ts)
    placeholders: defaultdict[str, set[str]] = defaultdict(set)
    py_dict: dict[str, dict] = {}
    for name, block in raw_entries.items():
        cls, data = process_block(name, block, placeholders)
        py_dict[cls] = data
    OUTPUT_DEX.parent.mkdir(parents=True, exist_ok=True)
    import pprint
    with OUTPUT_DEX.open('w') as f:
        f.write('from .functions.itemfuncs import *\n\n')
        pretty = pprint.pformat(py_dict, indent=4, width=120, sort_dicts=False)
        f.write('py_dict = ' + pretty)
    OUTPUT_FUNCS.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FUNCS.open('w') as f:
        for cls in sorted(placeholders):
            f.write(f'class {cls}:\n')
            for func in sorted(placeholders[cls]):
                f.write(f'    def {func}(self, *args, **kwargs):\n        pass\n')
            f.write('\n')


if __name__ == '__main__':
    main()
