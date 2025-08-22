from __future__ import annotations

import json
import pprint
import re
from collections import defaultdict
from pathlib import Path

import json5

# Directories
BASE_DIR = Path(__file__).parent
TS_DIR = BASE_DIR / "ts"
JSON_DIR = BASE_DIR / "json"
PY_DIR = BASE_DIR / "py"

# Mapping of dictionary types to output python file names used by the main
# project.  These names differ from the raw dict_type names for some data
# files.
PY_NAMES = {
	"pokedex": "pokedex",
	"items": "itemsdex",
	"abilities": "abilitiesdex",
	# move data was previously stored in combatdex.py
	"moves": "moves",
}
FUNC_DIR = PY_DIR / "functions"

# Patterns to remove TypeScript headers
HEADER_PATTERNS = {
	"pokedex": re.compile(r"export const Pokedex: import\([^)]+\)\.SpeciesDataTable = {"),
	"items": re.compile(r"export const Items: import\([^)]+\)\.ItemDataTable = {"),
	"abilities": re.compile(r"/\*.*?\*/\s*export const Abilities: import\([^)]+\)\.AbilityDataTable = {", re.DOTALL),
	"moves": re.compile(r"// List of flags[\s\S]*?export const Moves: import\([^)]+\)\.MoveDataTable = {", re.DOTALL),
}

NAME_RE = re.compile(r"\s*(\"[^\"]+\"|\w+)\s*:\s*{")
FUNC_RE = re.compile(r"(\w+)\s*(?::\s*function)?\s*\([^)]*\)\s*{")
ARROW_SIMPLE_RE = re.compile(r"(\w+)\s*:\s*\([^)]*\)\s*=>\s*[^,{]+")
ARROW_BLOCK_RE = re.compile(r"(\w+)\s*:\s*\([^)]*\)\s*=>\s*{")


def load_ts(path: Path, dict_type: str) -> str:
	"""Load a TypeScript file and strip its header."""
	text = path.read_text()
	pattern = HEADER_PATTERNS.get(dict_type)
	if pattern:
		text = pattern.sub("{", text)
	text = re.sub(r"//.*", "", text)
	return text.strip()


def extract_entries(text: str) -> dict[str, str]:
	"""Split a TypeScript dictionary into individual entry blocks."""
	if text.endswith("};"):
		text = text[:-2]
	if text.startswith("{"):
		text = text[1:]
	entries: dict[str, str] = {}
	pos = 0
	while pos < len(text):
		m = NAME_RE.match(text, pos)
		if not m:
			break
		key = m.group(1)
		name = key.split(":")[0].strip().strip('"')
		start = m.end() - 1
		brace = 1
		i = start + 1
		while i < len(text) and brace:
			if text[i] == "{":
				brace += 1
			elif text[i] == "}":
				brace -= 1
			i += 1
		block = text[start:i]
		entries[name] = block
		if i < len(text) and text[i] == ",":
			i += 1
		pos = i
	return entries


def process_block(name: str, block: str, placeholders: defaultdict[str, set[str]]) -> tuple[str, dict]:
	"""Replace functions in a block with class method references."""
	class_name = name.capitalize() if name.isidentifier() else f"Entry{len(placeholders)}"
	block = ARROW_SIMPLE_RE.sub(lambda m: f"{m.group(1)}: '{class_name}.{m.group(1)}'", block)
	idx = 0
	result = ""
	while idx < len(block):
		m_arrow = ARROW_BLOCK_RE.search(block, idx)
		m_func = FUNC_RE.search(block, idx)
		# Choose earliest match
		m = None
		arrow = False
		if m_arrow and (not m_func or m_arrow.start() < m_func.start()):
			m = m_arrow
			arrow = True
		elif m_func:
			m = m_func
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
			if block[j] == "{":
				brace += 1
			elif block[j] == "}":
				brace -= 1
			j += 1
		if j < len(block) and block[j] == ",":
			result += ","
			j += 1
		placeholders[class_name].add(fn)
		idx = j
	# json5 doesn't accept numeric keys, so quote them
	result = re.sub(r"(\{|,)\s*(\d+)\s*:", lambda m: f'{m.group(1)} "{m.group(2)}":', result)
	data = json5.loads(result)
	return class_name, data


def convert_ts(dict_type: str) -> None:
	ts_path = TS_DIR / f"{dict_type}.ts"
	if not ts_path.exists():
		print(f"Missing {ts_path}")
		return
	text = load_ts(ts_path, dict_type)
	entries = extract_entries(text)
	placeholders: defaultdict[str, set[str]] = defaultdict(set)
	py_dict: dict[str, dict] = {}
	for name, block in entries.items():
		cls, data = process_block(name, block, placeholders)
		py_dict[cls] = data

	# Write JSON file
	JSON_DIR.mkdir(parents=True, exist_ok=True)
	with (JSON_DIR / f"{dict_type}.json").open("w") as f:
		json.dump(py_dict, f, indent=4)

	# Write Python dictionary
	PY_DIR.mkdir(parents=True, exist_ok=True)
	out_name = PY_NAMES.get(dict_type, dict_type)
	with (PY_DIR / f"{out_name}.py").open("w") as f:
		f.write(f"from .functions.{dict_type}_funcs import *\n\n")
		pretty = pprint.pformat(py_dict, indent=4, width=120, sort_dicts=False)
		f.write("py_dict = " + pretty)

	# Write functions file
	FUNC_DIR.mkdir(parents=True, exist_ok=True)
	with (FUNC_DIR / f"{dict_type}_funcs.py").open("w") as f:
		for cls in sorted(placeholders):
			f.write(f"class {cls}:\n")
			for fn in sorted(placeholders[cls]):
				f.write(f"    def {fn}(self, *args, **kwargs):\n        pass\n")
			f.write("\n")

	print(f"Processed {dict_type}")


def main() -> None:
	for dict_type in ["pokedex", "items", "abilities", "moves"]:
		convert_ts(dict_type)


if __name__ == "__main__":
	main()
